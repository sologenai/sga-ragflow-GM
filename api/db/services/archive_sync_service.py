"""
档案同步服务 - Archive Sync Service
用于从档案系统同步文档到RAGFlow知识库
"""
import json
import logging
import os
import re
import threading
import time
import requests
import hashlib
from datetime import datetime, timedelta
from api.db.db_models import SystemSetting, Knowledgebase, Document
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.document_service import DocumentService, queue_raptor_o_graphrag_tasks
from api.db.services.file_service import FileService
from api.db.services.task_service import GRAPH_RAPTOR_FAKE_DOC_ID


class MemoryFile:
    """内存文件类，用于上传下载的文件到RAGFlow"""
    def __init__(self, content, filename, content_type="application/octet-stream"):
        self.content = content if isinstance(content, bytes) else content.encode('utf-8')
        self.filename = filename
        self.size = len(self.content)
        self.content_type = content_type

    def read(self):
        return self.content


class ArchiveSyncService:
    """档案同步服务"""
    CONFIG_KEY = "archive_sync_config"

    # Default API 配置 (can be overridden via config)
    DEFAULT_API_BASE_URL = os.getenv("ARCHIVE_API_BASE_URL", "http://das-dev.itg.cn")
    TOKEN_URL = "/report/getApiToken"
    DOCTYPE_URL = "/report/queryDocType"
    QUERY_URL = "/report/queryDataDetail"
    FILE_URL = "/report/queryViewData"

    # 鉴权信息
    SYSTEM_ID = os.getenv("ARCHIVE_SYSTEM_ID", "OA")
    PASSWORD = os.getenv("ARCHIVE_PASSWORD", "")
    DEFAULT_ARCHIVE_USERID = os.getenv("ARCHIVE_USER_ID", "308569")
    FIXED_CATEGORY_NAMES = [
        "党建工作",
        "党务工作",
        "纪律监察",
        "工会",
        "行政管理",
        "综合行政事务",
        "人力资源管理",
        "品牌管理",
        "风控合规法务管理",
        "信息技术管理",
        "安全管理",
        "经营管理",
        "财务管理",
        "资金管理",
        "审计工作",
        "战略投资管理",
        "证券管理",
        "研发管理",
        "供应链管理",
    ]

    # Token缓存
    _token_cache = None
    _token_expire_time = None
    _token_lock = threading.Lock()

    @classmethod
    def get_api_base_url(cls):
        """Get API base URL from config or use default"""
        config = cls.get_config()
        return config.get("api_base_url") or cls.DEFAULT_API_BASE_URL

    @classmethod
    def get_archive_userid(cls):
        """Get archive API userid from config or use the validated default."""
        config = cls.get_config()
        return str(config.get("archive_userid") or cls.DEFAULT_ARCHIVE_USERID)

    @classmethod
    def get_fixed_categories(cls):
        """Return the fixed category set required by the business."""
        return [{"code": name, "name": name, "desc": ""} for name in cls.FIXED_CATEGORY_NAMES]

    @staticmethod
    def _normalize_text(value):
        return (value or "").strip()

    @staticmethod
    def _has_duplicate_suffix(name):
        return bool(name and re.search(r"_0(?:\.[^.]+)?$", name))

    @classmethod
    def _should_skip_sync_item(cls, doctitle="", filename=""):
        title = cls._normalize_text(doctitle)
        file_name = cls._normalize_text(filename)

        for value in (title, file_name):
            if value and "存证" in value:
                return True, "contains 存证"
            if cls._has_duplicate_suffix(value):
                return True, "ends with _0"

        return False, ""

    @classmethod
    def test_connection(cls, api_base_url=None):
        """
        Test connection to Archive API
        :param api_base_url: Optional URL to test, uses configured URL if not provided
        :return: dict with success status and message
        """
        test_url = api_base_url or cls.get_api_base_url()
        try:
            # Test by getting token
            url = f"{test_url}{cls.TOKEN_URL}"
            params = {"systemid": cls.SYSTEM_ID, "password": cls.PASSWORD}
            resp = requests.get(url, params=params, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                if data.get("result") == "success":
                    return {
                        "success": True,
                        "message": "连接成功，Token获取正常",
                        "status_code": resp.status_code
                    }
                else:
                    return {
                        "success": False,
                        "message": f"认证失败: {data.get('message', '未知错误')}",
                        "status_code": resp.status_code
                    }
            else:
                return {
                    "success": False,
                    "message": f"HTTP错误: {resp.status_code}",
                    "status_code": resp.status_code
                }
        except requests.exceptions.Timeout:
            return {"success": False, "message": "连接超时"}
        except requests.exceptions.ConnectionError as e:
            return {"success": False, "message": f"连接失败: {str(e)[:100]}"}
        except Exception as e:
            return {"success": False, "message": f"测试失败: {str(e)[:100]}"}

    @classmethod
    def get_token(cls, force_refresh=False):
        """获取API Token，有效期24小时，带缓存"""
        with cls._token_lock:
            now = datetime.now()
            # 检查缓存是否有效（提前1小时刷新）
            if not force_refresh and cls._token_cache and cls._token_expire_time:
                if now < cls._token_expire_time - timedelta(hours=1):
                    return cls._token_cache

            # 获取新Token
            try:
                api_base_url = cls.get_api_base_url()
                url = f"{api_base_url}{cls.TOKEN_URL}"
                params = {"systemid": cls.SYSTEM_ID, "password": cls.PASSWORD}
                resp = requests.get(url, params=params, timeout=30)
                data = resp.json()

                if data.get("result") == "success":
                    cls._token_cache = data.get("Token")
                    cls._token_expire_time = now + timedelta(hours=24)
                    logging.info(f"[ArchiveSync] Token refreshed successfully")
                    return cls._token_cache
                else:
                    logging.error(f"[ArchiveSync] Token fetch failed: {data.get('message')}")
                    return None
            except Exception as e:
                logging.error(f"[ArchiveSync] Token fetch error: {e}")
                return None
    
    @classmethod
    def get_auth_headers(cls):
        """获取API请求头"""
        token = cls.get_token()
        if not token:
            raise Exception("Failed to get archive API token")
        return {
            "systemid": cls.SYSTEM_ID,
            "token": token,
            "Content-Type": "application/json"
        }
    
    @classmethod
    def fetch_doctypes(cls):
        """
        从档案系统获取所有文档分类名称 (docclassfyname)
        通过查询档案数据，提取唯一的分类名称
        返回格式: [{"code": "党群", "name": "党群"}, ...]
        """
        try:
            logging.info("[ArchiveSync] Fetching docclassfyname from archive data...")
            fixed_categories = cls.get_fixed_categories()
            logging.info(f"[ArchiveSync] Using {len(fixed_categories)} fixed categories for archive sync")
            return fixed_categories

            all_categories = set()

            # 尝试查询多个常见的 doctype 来获取更多分类
            doctypes_to_try = ["ZD", "SFD", "FP", "HT", ""]  # 制度、收发文、发票、合同、全部

            for doctype in doctypes_to_try:
                try:
                    archives = cls.query_archives(doctype=doctype if doctype else None)
                    logging.info(f"[ArchiveSync] Got {len(archives)} archive records for doctype='{doctype}'")

                    for archive in archives:
                        docinfo = archive.get("docinfo", {})
                        classfy_name = docinfo.get("docclassfyname", "")
                        if classfy_name and classfy_name.strip():
                            all_categories.add(classfy_name.strip())

                    # 如果获取到数据就继续尝试其他类型以获取更多分类
                except Exception as e:
                    logging.warning(f"[ArchiveSync] Error querying doctype '{doctype}': {e}")
                    continue

            if not all_categories:
                logging.warning("[ArchiveSync] No categories extracted, trying DOCTYPE_URL fallback...")
                return cls._fetch_doctypes_fallback()

            # 转换为前端期望的格式: [{code: "党群", name: "党群"}, ...]
            category_list = [{"code": name, "name": name, "desc": ""} for name in sorted(all_categories)]
            logging.info(f"[ArchiveSync] Extracted {len(category_list)} unique docclassfyname: {[c['name'] for c in category_list]}")
            return category_list

        except Exception as e:
            logging.error(f"[ArchiveSync] Fetch doctypes error: {e}", exc_info=True)
            return cls.get_fixed_categories()

    @classmethod
    def _fetch_doctypes_fallback(cls):
        """旧的 doctype 获取方法作为回退"""
        try:
            headers = cls.get_auth_headers()
            api_base_url = cls.get_api_base_url()
            url = f"{api_base_url}{cls.DOCTYPE_URL}"
            resp = requests.post(url, headers=headers, timeout=30)
            data = resp.json()

            if "doctypelist" in data:
                logging.info(f"[ArchiveSync] Fallback got doctypelist: {data['doctypelist']}")
                return data["doctypelist"]
            else:
                logging.warning(f"[ArchiveSync] Unexpected doctype response: {data}")
                return []
        except Exception as e:
            logging.error(f"[ArchiveSync] Fallback fetch doctypes error: {e}")
            return []
    
    @classmethod
    def get_config(cls):
        """获取档案同步配置"""
        setting = SystemSetting.get_or_none(SystemSetting.key == cls.CONFIG_KEY)
        default_config = {
            "enabled": False,
            "sync_time": "03:00",
            "graph_regen_time": "05:00",
            "last_sync_time": None,
            "sync_user_id": "",
            "archive_userid": cls.DEFAULT_ARCHIVE_USERID,
            # API URL 配置
            "api_base_url": cls.DEFAULT_API_BASE_URL,
            # 同步频率设置
            "sync_frequency": "weekly",  # daily, weekly, monthly
            "incremental_days": 7,
            "weekly_days": [1],  # 0=Sunday, 1=Monday, etc.
            "monthly_days": [1],  # 1-31
            # 图谱重建频率
            "graph_regen_frequency": "monthly",
            "graph_regen_weekly_days": [0],
            "graph_regen_monthly_days": [1],
            # 分类映射: doctype_code -> kb_id
            "category_mapping": {},
            # 分类信息缓存
            "categories": cls.get_fixed_categories(),
            # 同步统计
            "total_synced": 0
        }
        if not setting:
            return default_config
        try:
            config = {**default_config, **json.loads(setting.value)}
            return config
        except:
            return default_config
    
    @classmethod
    def update_config(cls, config):
        """更新档案同步配置"""
        setting = SystemSetting.get_or_none(SystemSetting.key == cls.CONFIG_KEY)
        if setting:
            try:
                current = json.loads(setting.value)
            except:
                current = {}
        else:
            current = {}
        
        current.update(config)
        SystemSetting.replace(key=cls.CONFIG_KEY, value=json.dumps(current)).execute()
        return cls.get_config()

    @classmethod
    def refresh_categories(cls):
        """从档案系统刷新分类列表并更新配置，清空旧的分类列表"""
        categories = cls.fetch_doctypes()
        # 无论是否获取到新分类，都清空旧的分类列表，用新的替换
        # 这样每次刷新都是最新的分类
        cls.update_config({"categories": categories if categories else []})
        logging.info(f"[ArchiveSync] Refreshed categories, count: {len(categories) if categories else 0}")
        return categories if categories else []

    @classmethod
    def get_kb_id_for_category(cls, category_code, category_name, tenant_id):
        """
        获取或创建分类对应的知识库
        :param category_code: 分类代码 (如 'ZD', 'SFD')
        :param category_name: 分类名称 (如 '党群', '文书档案')
        :param tenant_id: 租户ID
        :return: 知识库ID
        """
        config = cls.get_config()
        category_mapping = config.get("category_mapping", {})  # code -> kb_id
        category_name_mapping = config.get("category_name_mapping", {})  # code -> kb_name

        # 1. Check if mapping exists and KB still valid
        if category_code in category_mapping:
            existing_kb = Knowledgebase.get_or_none(Knowledgebase.id == category_mapping[category_code])
            if existing_kb:
                return category_mapping[category_code]

        # 2. Get KB name for this category
        kb_name = category_name_mapping.get(category_code, f"ITG_Archive_{category_name or category_code}")

        # 3. Try to find existing KB by name first
        exists, existing_kb = KnowledgebaseService.get_by_name(kb_name, tenant_id)
        if exists and existing_kb:
            kb_id = existing_kb.id
            category_mapping[category_code] = kb_id
            category_name_mapping[category_code] = kb_name
            cls.update_config({"category_mapping": category_mapping, "category_name_mapping": category_name_mapping})
            logging.info(f"[ArchiveSync] Found existing KB '{kb_name}' for category {category_code}: {kb_id}")
            return kb_id

        # 4. Create new KB if not exists - use presentation parser for PDF
        logging.info(f"[ArchiveSync] Creating new KB '{kb_name}' for category {category_code}")
        try:
            ok, payload = KnowledgebaseService.create_with_name(
                name=kb_name,
                tenant_id=tenant_id,
                parser_id="naive"  # archive PDFs should use the general parser
            )
            if ok and payload and "id" in payload:
                # Actually save to database
                if KnowledgebaseService.save(**payload):
                    kb_id = payload["id"]
                    category_mapping[category_code] = kb_id
                    category_name_mapping[category_code] = kb_name
                    cls.update_config({"category_mapping": category_mapping, "category_name_mapping": category_name_mapping})
                    logging.info(f"[ArchiveSync] Created KB '{kb_name}' for category {category_code}: {kb_id}")
                    return kb_id
                else:
                    logging.error(f"[ArchiveSync] Failed to save KB for {category_code}")
            else:
                logging.error(f"[ArchiveSync] Failed to create KB payload for {category_code}: {payload}")
        except Exception as e:
            logging.error(f"[ArchiveSync] Failed to create KB for {category_code}: {e}")
            return None
        return None

    @classmethod
    def query_archives(cls, doctype=None, start_date=None, end_date=None, page=1, page_size=100, userid=None):
        """
        查询档案元数据
        :param doctype: 文档类型代码 (如 'SFD', 'FP')
        :param start_date: 开始日期 YYYYMMDD
        :param end_date: 结束日期 YYYYMMDD
        :param userid: 用户ID（必填字段）
        :return: 档案列表
        """
        try:
            headers = cls.get_auth_headers()
            api_base_url = cls.get_api_base_url()
            url = f"{api_base_url}{cls.QUERY_URL}"
            userid = userid or cls.get_archive_userid()

            # userid 是必填字段
            payload = {
                "sysno": "",
                "userid": userid,
                "docclassfy": "",
                "docbarcode": "",
                "docno": "",
                "doctitle": "",
                "doccomptaxno": "913502001550054395",
                "archivetypename": "文书档案",
                "isfilepool": "false"
            }
            if doctype:
                payload["doctype"] = doctype
            if start_date:
                payload["StartDate"] = start_date
            if end_date:
                payload["EndDate"] = end_date

            logging.info(f"[ArchiveSync] Query archives with payload: {payload}")
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            data = resp.json()

            if "result" in data and isinstance(data["result"], list):
                logging.info(f"[ArchiveSync] Query returned {len(data['result'])} records")
                return data["result"]
            elif data.get("result") == "false":
                logging.warning(f"[ArchiveSync] Query returned no data: {data.get('message')}")
                return []
            else:
                logging.warning(f"[ArchiveSync] Unexpected response: {data}")
                return []
        except Exception as e:
            logging.error(f"[ArchiveSync] Query archives error: {e}")
            return []

    @classmethod
    def get_file_url(cls, docid, tablename, tableid, userid=None):
        """
        获取档案附件下载地址
        :return: 文件URL列表
        """
        try:
            headers = cls.get_auth_headers()
            api_base_url = cls.get_api_base_url()
            url = f"{api_base_url}{cls.FILE_URL}"
            userid = userid or cls.get_archive_userid()

            # 存储所有文件列表
            all_files = []

            # 首先查询 fileclass: "ORG" (原始文件)
            payload = {
                "docid": docid,
                "tablename": tablename,
                "tableid": tableid,
                "userid": userid,
                "fileclass": "ORG"  # 原始文件
            }

            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            data = resp.json()

            if "fileList" in data and data["fileList"]:
                all_files.extend(data["fileList"])
            
            # 然后查询 fileclass: "--"
            payload["fileclass"] = "--"
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            data = resp.json()

            if "fileList" in data and data["fileList"]:
                all_files.extend(data["fileList"])
            elif data.get("result") == "false":
                logging.warning(f"[ArchiveSync] File with payload: {payload}")
                logging.warning(f"[ArchiveSync] File access denied: {data.get('message')}")

            return all_files
        except Exception as e:
            logging.error(f"[ArchiveSync] Get file URL error: {e}")
            return []

    @classmethod
    def download_file(cls, file_url):
        """下载文件内容"""
        try:
            resp = requests.get(file_url, timeout=120)
            if resp.status_code == 200:
                return resp.content
            else:
                logging.error(f"[ArchiveSync] Download failed: {resp.status_code}")
                return None
        except Exception as e:
            logging.error(f"[ArchiveSync] Download error: {e}")
            return None

    @classmethod
    def get_sync_user_id(cls):
        """获取用于同步的用户ID"""
        from api.db.services.user_service import UserService
        config = cls.get_config()
        user_id = config.get("sync_user_id")

        if user_id:
            user = UserService.get_by_id(user_id)
            if user:
                return user_id

        # 查找任意管理员用户
        from api.db.db_models import User
        admin = User.select().where(User.is_superuser == True).first()
        if admin:
            cls.update_config({"sync_user_id": admin.id})
            return admin.id

        # 查找任意用户
        user = User.select().first()
        if user:
            cls.update_config({"sync_user_id": user.id})
            return user.id

        return None

    @classmethod
    def _normalize_incremental_days(cls, days_back=None):
        if days_back is None:
            days_back = cls.get_config().get("incremental_days", 7)

        try:
            normalized_days = int(days_back)
        except (TypeError, ValueError):
            normalized_days = 7

        return max(normalized_days, 1)

    @classmethod
    def sync_category(cls, doctype_code, category_name=None, target_date_start=None, target_date_end=None):
        """
        同步单个分类的档案
        按每条档案的 docclassfyname 字段匹配对应的知识库
        :param doctype_code: 文档类型代码 (用于查询 API)
        :param category_name: 分类名称 (未使用，保留兼容性)
        :param target_date_start: 开始日期 (datetime或YYYYMMDD字符串)
        :param target_date_end: 结束日期
        :return: 同步的文档数量
        """
        user_id = cls.get_sync_user_id()
        if not user_id:
            logging.error("[ArchiveSync] No user available for sync")
            return 0

        # 获取用户的 tenant_id
        from api.db.services.user_service import UserService
        user = UserService.get_by_id(user_id)
        if not user:
            logging.error("[ArchiveSync] User not found")
            return 0
        tenant_id = user.get("tenant_id") if isinstance(user, dict) else getattr(user, "tenant_id", None)

        # 获取映射配置 - key 是 docclassfyname (如 '党群')，value 是 kb_id
        config = cls.get_config()
        category_mapping = config.get("category_mapping", {})  # docclassfyname -> kb_id

        if not category_mapping:
            logging.warning("[ArchiveSync] No category mappings configured")
            return 0

        # 格式化日期
        if isinstance(target_date_start, datetime):
            start_str = target_date_start.strftime("%Y%m%d")
        else:
            start_str = target_date_start

        if isinstance(target_date_end, datetime):
            end_str = target_date_end.strftime("%Y%m%d")
        else:
            end_str = target_date_end or datetime.now().strftime("%Y%m%d")

        # 查询档案
        archives = cls.query_archives(doctype=doctype_code, start_date=start_str, end_date=end_str)
        logging.info(f"[ArchiveSync] Found {len(archives)} archives for {doctype_code}")

        synced_count = 0
        for archive in archives:
            try:
                docinfo = archive.get("docinfo", {})
                docid = docinfo.get("docid")
                doctitle = docinfo.get("doctitle", f"Archive_{docid}")
                tablename = docinfo.get("tablename")
                tableid = docinfo.get("tableid")
                # 获取分类名称字段 - 用于匹配知识库
                doc_classfy_name = docinfo.get("docclassfyname", "")

                if not all([docid, tablename, tableid]):
                    logging.debug(f"[ArchiveSync] Skip incomplete record: docid={docid}")
                    continue

                # 根据 docclassfyname 查找对应的知识库
                if not doc_classfy_name:
                    logging.debug(f"[ArchiveSync] No docclassfyname for {docid}, skipping")
                    continue

                kb_id = category_mapping.get(doc_classfy_name)
                if not kb_id:
                    logging.debug(f"[ArchiveSync] No KB mapped for '{doc_classfy_name}', skipping {docid}")
                    continue

                kb = Knowledgebase.get_or_none(Knowledgebase.id == kb_id)
                if not kb:
                    logging.error(f"[ArchiveSync] KB not found: {kb_id} for '{doc_classfy_name}'")
                    continue

                # 检查是否已存在
                existing = Document.select().where(
                    Document.kb_id == kb_id,
                    Document.name.contains(docid)
                ).first()
                if existing:
                    logging.debug(f"[ArchiveSync] Skip existing: {docid}")
                    continue

                # 获取文件URL
                file_list = cls.get_file_url(docid, tablename, tableid)
                if not file_list:
                    logging.warning(f"[ArchiveSync] No files for {docid}")
                    continue

                # 下载并上传文件
                for file_info in file_list:
                    file_url = file_info.get("downloadPath") or file_info.get("filePath")
                    if not file_url:
                        continue

                    content = cls.download_file(file_url)
                    if not content:
                        continue

                    # 使用 API 返回的原始文件名，或构造文件名
                    original_filename = file_info.get("fileName", "")
                    if original_filename:
                        # 在原始文件名前加上 docid 防止重复
                        filename = f"{docid}_{original_filename}"
                    else:
                        filename = f"{doctitle}_{docid}.pdf"

                    # 确定 content_type
                    if filename.lower().endswith(".pdf"):
                        content_type = "application/pdf"
                    else:
                        content_type = "application/octet-stream"

                    # 创建内存文件并上传
                    mem_file = MemoryFile(content, filename, content_type)

                    try:
                        err, files = FileService.upload_document(kb, [mem_file], user_id)
                        if not err and files:
                            synced_count += 1
                            logging.info(f"[ArchiveSync] Uploaded: {filename} (classfy: {doc_classfy_name})")
                    except Exception as upload_err:
                        logging.error(f"[ArchiveSync] Upload failed: {upload_err}")

            except Exception as e:
                logging.error(f"[ArchiveSync] Sync archive error: {e}")
                continue

        return synced_count

    @classmethod
    def sync_all_categories(cls, days_back=7):
        """
        同步所有已配置映射的分类
        :param days_back: 回溯天数（增量同步）
        """
        config = cls.get_config()
        category_name_mapping = config.get("category_name_mapping", {})

        # 过滤出已配置名称的分类
        configured_codes = [code for code, name in category_name_mapping.items() if name]
        if not configured_codes:
            logging.warning("[ArchiveSync] No category name mappings configured")
            return 0

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        total_synced = 0
        for doctype_code in configured_codes:
            category_name = category_name_mapping.get(doctype_code)
            count = cls.sync_category(
                doctype_code,
                category_name=category_name,
                target_date_start=start_date,
                target_date_end=end_date
            )
            total_synced += count

        # 更新同步时间和统计
        cls.update_config({
            "last_sync_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_synced": config.get("total_synced", 0) + total_synced
        })

        logging.info(f"[ArchiveSync] Total synced: {total_synced} documents")
        return total_synced

    @classmethod
    def sync_category(
        cls,
        category_name,
        target_date_start=None,
        target_date_end=None,
        days_back=None,
        full_sync=False,
    ):
        """Sync one archive category by matching docclassfyname instead of misusing doctype."""
        category_name = cls._normalize_text(category_name)
        if not category_name:
            logging.warning("[ArchiveSync] Empty category name, skipping")
            return 0

        user_id = cls.get_sync_user_id()
        if not user_id:
            logging.error("[ArchiveSync] No user available for sync")
            return 0

        config = cls.get_config()
        category_mapping = config.get("category_mapping", {})
        kb_id = category_mapping.get(category_name)
        if not kb_id:
            logging.warning(f"[ArchiveSync] No KB mapped for category '{category_name}'")
            return 0

        kb = Knowledgebase.get_or_none(Knowledgebase.id == kb_id)
        if not kb:
            logging.error(f"[ArchiveSync] KB not found: {kb_id} for '{category_name}'")
            return 0

        archive_userid = cls.get_archive_userid()

        if isinstance(target_date_start, datetime):
            start_str = target_date_start.strftime("%Y%m%d")
        else:
            start_str = target_date_start

        if isinstance(target_date_end, datetime):
            end_str = target_date_end.strftime("%Y%m%d")
        else:
            end_str = target_date_end or datetime.now().strftime("%Y%m%d")

        if not full_sync and not start_str:
            incremental_days = cls._normalize_incremental_days(days_back)
            start_str = (datetime.now() - timedelta(days=incremental_days)).strftime("%Y%m%d")

        logging.info(
            f"[ArchiveSync] Start {'full' if full_sync else 'incremental'} sync for category "
            f"'{category_name}' (start={start_str or 'ALL'}, end={end_str})"
        )

        archives = cls.query_archives(start_date=start_str, end_date=end_str, userid=archive_userid)
        logging.info(
            f"[ArchiveSync] Loaded {len(archives)} candidate archives for category '{category_name}'"
        )

        synced_count = 0
        for archive in archives:
            try:
                docinfo = archive.get("docinfo", {})
                docid = docinfo.get("docid")
                doctitle = docinfo.get("doctitle", f"Archive_{docid}")
                tablename = docinfo.get("tablename")
                tableid = docinfo.get("tableid")
                doc_classfy_name = cls._normalize_text(docinfo.get("docclassfyname", ""))

                if not all([docid, tablename, tableid]):
                    logging.debug(f"[ArchiveSync] Skip incomplete record: docid={docid}")
                    continue

                if doc_classfy_name != category_name:
                    continue

                should_skip, skip_reason = cls._should_skip_sync_item(doctitle=doctitle)
                if should_skip:
                    logging.info(
                        f"[ArchiveSync] Skip archive {docid} ({doctitle}) for category '{category_name}': {skip_reason}"
                    )
                    continue

                existing = Document.select().where(
                    Document.kb_id == kb_id,
                    Document.name.contains(docid)
                ).first()
                if existing:
                    logging.debug(f"[ArchiveSync] Skip existing: {docid}")
                    continue

                file_list = cls.get_file_url(docid, tablename, tableid, userid=archive_userid)
                if not file_list:
                    logging.warning(f"[ArchiveSync] No files for {docid}")
                    continue

                processed_filenames = set()
                for file_info in file_list:
                    file_url = file_info.get("downloadPath") or file_info.get("filePath")
                    if not file_url:
                        continue

                    original_filename = file_info.get("fileName", "")
                    if original_filename:
                        filename = f"{docid}_{original_filename}"
                    else:
                        filename = f"{docid}_{doctitle}.pdf"

                    if filename in processed_filenames:
                        logging.info(f"[ArchiveSync] Skip duplicate filename: {filename}")
                        continue
                    processed_filenames.add(filename)

                    should_skip, skip_reason = cls._should_skip_sync_item(
                        doctitle=doctitle,
                        filename=original_filename or filename,
                    )
                    if should_skip:
                        logging.info(
                            f"[ArchiveSync] Skip file for archive {docid} ({filename}) in category '{category_name}': {skip_reason}"
                        )
                        continue

                    content = cls.download_file(file_url)
                    if not content:
                        continue

                    content_type = "application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream"
                    mem_file = MemoryFile(content, filename, content_type)

                    try:
                        err, files = FileService.upload_document(kb, [mem_file], user_id)
                        if not err and files:
                            doc = files[0][0]
                            doc_id = doc.get("id") if isinstance(doc, dict) else doc.id
                            try:
                                DocumentService.update_by_id(doc_id, {"parser_id": "naive"})
                                doc_for_run = dict(doc) if isinstance(doc, dict) else {"id": doc_id}
                                doc_for_run["id"] = doc_id
                                doc_for_run["kb_id"] = kb_id
                                doc_for_run["parser_id"] = "naive"
                                DocumentService.run(kb.tenant_id, doc_for_run, {})
                            except Exception as parse_err:
                                logging.error(
                                    f"[ArchiveSync] Failed to queue parsing for {doc_id}: {parse_err}",
                                    exc_info=True,
                                )
                            synced_count += 1
                            logging.info(f"[ArchiveSync] Uploaded: {filename} (classfy: {doc_classfy_name})")
                    except Exception as upload_err:
                        logging.error(f"[ArchiveSync] Upload failed: {upload_err}")

            except Exception as e:
                logging.error(f"[ArchiveSync] Sync archive error: {e}")
                continue

        return synced_count

    @classmethod
    def sync_all_categories(cls, days_back=None, full_sync=False):
        """Sync all configured archive categories in the requested date window."""
        config = cls.get_config()
        category_mapping = config.get("category_mapping", {})
        configured_categories = [name for name, kb_id in category_mapping.items() if kb_id]
        if not configured_categories:
            logging.warning("[ArchiveSync] No category mappings configured")
            return 0

        end_date = datetime.now()
        normalized_days = None if full_sync else cls._normalize_incremental_days(days_back)
        start_date = None if full_sync else end_date - timedelta(days=normalized_days)

        logging.info(
            f"[ArchiveSync] Start {'full' if full_sync else 'incremental'} sync for "
            f"{len(configured_categories)} categories"
            + (
                ""
                if full_sync
                else f" (days_back={normalized_days}, start={start_date.strftime('%Y%m%d')}, end={end_date.strftime('%Y%m%d')})"
            )
        )

        total_synced = 0
        for category_name in configured_categories:
            total_synced += cls.sync_category(
                category_name,
                target_date_start=start_date,
                target_date_end=end_date,
                days_back=normalized_days,
                full_sync=full_sync,
            )

        cls.update_config({
            "last_sync_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_synced": config.get("total_synced", 0) + total_synced
        })

        logging.info(f"[ArchiveSync] Total synced: {total_synced} documents")
        return total_synced

    @classmethod
    def _should_sync_today(cls, config):
        """Check if archive sync should run today based on frequency settings."""
        frequency = config.get("sync_frequency", "weekly")
        now = datetime.now()

        if frequency == "daily":
            return True
        if frequency == "weekly":
            current_weekday = (now.weekday() + 1) % 7  # JS convention: Sunday=0
            weekly_days = config.get("weekly_days", [1])
            return current_weekday in weekly_days
        if frequency == "monthly":
            current_day = now.day
            monthly_days = config.get("monthly_days", [1])
            return current_day in monthly_days
        return True

    @classmethod
    def _should_regen_graph_today(cls, config):
        """Check if archive graph rebuild should run today based on frequency settings."""
        frequency = config.get("graph_regen_frequency", "monthly")
        now = datetime.now()

        if frequency == "daily":
            return True
        if frequency == "weekly":
            current_weekday = (now.weekday() + 1) % 7
            weekly_days = config.get("graph_regen_weekly_days", [0])
            return current_weekday in weekly_days
        if frequency == "monthly":
            current_day = now.day
            monthly_days = config.get("graph_regen_monthly_days", [1])
            return current_day in monthly_days
        return True

    @classmethod
    def start_scheduler(cls):
        """Start archive sync scheduler."""

        def run():
            logging.info("Archive Sync Scheduler started.")
            while True:
                try:
                    config = cls.get_config()
                    if not config.get("enabled", False):
                        time.sleep(60)
                        continue

                    now = datetime.now()
                    current_time = now.strftime("%H:%M")

                    if current_time == config.get("sync_time", "03:00"):
                        if cls._should_sync_today(config):
                            incremental_days = cls._normalize_incremental_days(
                                config.get("incremental_days", 7)
                            )
                            logging.info(
                                f"Running scheduled archive incremental sync "
                                f"(frequency: {config.get('sync_frequency', 'weekly')}, "
                                f"days_back={incremental_days})"
                            )
                            cls.sync_all_categories(days_back=incremental_days, full_sync=False)
                        else:
                            logging.debug("Skipping archive sync - not scheduled for today")
                        time.sleep(61)
                        continue

                    if current_time == config.get("graph_regen_time", "05:00"):
                        if cls._should_regen_graph_today(config):
                            logging.info(
                                f"Running scheduled archive graph rebuild (frequency: {config.get('graph_regen_frequency', 'monthly')})"
                            )
                            cls.trigger_graph_regen()
                        else:
                            logging.debug("Skipping archive graph rebuild - not scheduled for today")
                        time.sleep(61)
                        continue

                    time.sleep(30)
                except Exception as e:
                    logging.error(f"Archive scheduler error: {e}")
                    time.sleep(60)

        t = threading.Thread(target=run, daemon=True)
        t.start()

    @classmethod
    def trigger_graph_regen(cls, doctype_codes=None):
        """
        触发指定分类的图谱重建
        :param doctype_codes: 分类代码列表，为空则重建所有已映射的分类
        """
        config = cls.get_config()
        category_mapping = config.get("category_mapping", {})

        if doctype_codes is None:
            doctype_codes = list(category_mapping.keys())

        for code in doctype_codes:
            if code not in category_mapping:
                continue

            kb_id = category_mapping[code]
            kb = Knowledgebase.get_or_none(Knowledgebase.id == kb_id)
            if not kb:
                continue

            try:
                # 触发GraphRAG重建
                logging.info(f"[ArchiveSync] Triggering graph regen for {code} -> {kb.name}")
                queue_raptor_o_graphrag_tasks(kb.tenant_id, [GRAPH_RAPTOR_FAKE_DOC_ID], kb_id)
            except Exception as e:
                logging.error(f"[ArchiveSync] Graph regen error for {code}: {e}")
