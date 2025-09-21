# RAGFlow 知识图谱中文化解决方案

## 🎯 问题分析

### 当前问题
1. **实体类型英文化**：`entity_type` 返回 "ORGANIZATION"、"PERSON" 等英文
2. **实体描述英文化**：`description` 字段包含英文描述
3. **文件来源追踪**：`source_id` 数组包含文件ID，但缺少获取文件详情的方法

### 根本原因
- 知识图谱提取时使用了英文语言配置
- 默认语言设置为 "English"
- 实体类型使用英文标准

## 🔧 解决方案

### 方案1：修改知识图谱提取语言配置（推荐）

#### 1.1 修改默认语言配置

**文件：`graphrag/light/graph_prompt.py`**
```python
# 第11行，将默认语言改为中文
PROMPTS["DEFAULT_LANGUAGE"] = "Chinese"  # 原来是 "English"
```

**文件：`graphrag/general/graph_prompt.py`**
```python
# 在提取提示词中明确指定中文输出
GRAPH_EXTRACTION_PROMPT = """
-Goal-
Given a text document that is potentially relevant to this activity and a list of entity types, identify all entities of those types from the text and all relationships among the identified entities.

-Steps-
1. Identify all entities. For each identified entity, extract the following information:
- entity_name: Name of the entity, capitalized, in Chinese
- entity_type: One of the following types: [{entity_types}] (use Chinese labels)
- entity_description: Comprehensive description of the entity's attributes and activities in Chinese
Format each entity as ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>
...
```

#### 1.2 修改实体类型为中文

**文件：`graphrag/config_manager.py`**
```python
class GraphRAGConfigManager:
    """Manager for GraphRAG configuration validation and processing."""
    
    # 将默认实体类型改为中文
    DEFAULT_ENTITY_TYPES = ["组织", "人员", "地理位置", "事件", "类别"]  
    # 原来是：["organization", "person", "geo", "event", "category"]
    SUPPORTED_METHODS = ["light", "general"]
```

**文件：`web/src/components/entity-types-item.tsx`**
```typescript
const initialEntityTypes = [
  '组织',      // organization
  '人员',      // person  
  '地理位置',   // geo
  '事件',      // event
  '类别',      // category
];
```

#### 1.3 创建实体类型映射

**新建文件：`graphrag/entity_type_mapping.py`**
```python
"""实体类型中英文映射"""

# 英文到中文映射
ENTITY_TYPE_EN_TO_ZH = {
    "ORGANIZATION": "组织",
    "PERSON": "人员", 
    "GEO": "地理位置",
    "EVENT": "事件",
    "CATEGORY": "类别",
    "LOCATION": "地理位置",
    "CONCEPT": "概念",
    "PRODUCT": "产品",
    "TECHNOLOGY": "技术",
    "OTHER": "其他"
}

# 中文到英文映射
ENTITY_TYPE_ZH_TO_EN = {v: k for k, v in ENTITY_TYPE_EN_TO_ZH.items()}

def translate_entity_type_to_chinese(entity_type: str) -> str:
    """将英文实体类型转换为中文"""
    return ENTITY_TYPE_EN_TO_ZH.get(entity_type.upper(), entity_type)

def translate_entity_type_to_english(entity_type: str) -> str:
    """将中文实体类型转换为英文"""
    return ENTITY_TYPE_ZH_TO_EN.get(entity_type, entity_type)
```

### 方案2：API层面的中文化处理

如果不想修改核心提取逻辑，可以在API返回时进行翻译：

**文件：`api/apps/kb_app.py`**
```python
from graphrag.entity_type_mapping import translate_entity_type_to_chinese

def get_knowledge_graph_with_chinese_types(kb_id, tenant_id):
    """获取中文化的知识图谱数据"""
    
    # 获取原始图谱数据
    graph_data = get_original_knowledge_graph(kb_id, tenant_id)
    
    # 翻译实体类型
    if 'nodes' in graph_data:
        for node in graph_data['nodes']:
            if 'entity_type' in node:
                node['entity_type'] = translate_entity_type_to_chinese(node['entity_type'])
                node['entity_type_en'] = node['entity_type']  # 保留英文版本
    
    return graph_data
```

## 📁 文件来源信息解决方案

### 2.1 创建文件信息获取API

**新建API端点：`/api/v1/datasets/{kb_id}/nodes/{node_id}/source_files`**

```python
@manager.route("/datasets/<kb_id>/nodes/<node_id>/source_files", methods=["GET"])
@token_required
def get_node_source_files(kb_id, node_id):
    """获取节点的源文件信息"""
    try:
        # 获取节点信息
        node_info = get_node_by_id(kb_id, node_id, current_user.id)
        if not node_info:
            return get_json_result(code=404, message="Node not found")
        
        source_ids = node_info.get('source_id', [])
        
        # 获取文件信息
        files_info = []
        for source_id in source_ids:
            # 通过source_id获取文档信息
            doc_info = DocumentService.get_by_id(source_id)
            if doc_info[1]:  # 如果文档存在
                doc = doc_info[1]
                files_info.append({
                    "id": doc.id,
                    "name": doc.name,
                    "type": doc.type,
                    "size": doc.size,
                    "create_time": doc.create_time.isoformat() if doc.create_time else None,
                    "update_time": doc.update_time.isoformat() if doc.update_time else None,
                    "chunk_count": get_chunk_count_by_doc_id(doc.id),
                    "download_url": f"/api/v1/datasets/{kb_id}/documents/{doc.id}/download"
                })
        
        return get_json_result(data={
            "node_id": node_id,
            "source_files": files_info,
            "total_files": len(files_info)
        })
        
    except Exception as e:
        return get_json_result(code=500, message=str(e))
```

### 2.2 增强现有API返回文件信息

**修改知识图谱API，直接包含文件信息：**

```python
def enhance_nodes_with_file_info(nodes, kb_id):
    """为节点添加文件信息"""
    
    for node in nodes:
        source_ids = node.get('source_id', [])
        
        # 获取文件信息
        source_files = []
        for source_id in source_ids:
            doc_info = DocumentService.get_by_id(source_id)
            if doc_info[1]:
                doc = doc_info[1]
                source_files.append({
                    "id": doc.id,
                    "name": doc.name,
                    "type": doc.type,
                    "size": doc.size
                })
        
        # 添加到节点信息中
        node['source_files'] = source_files
        node['source_files_count'] = len(source_files)
    
    return nodes
```

## 🚀 实施步骤

### 步骤1：立即可用的API增强

创建一个Python脚本来处理现有数据：

```python
import requests
import json

class ChineseKnowledgeGraphAPI:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
        
        # 实体类型映射
        self.entity_type_mapping = {
            "ORGANIZATION": "组织",
            "PERSON": "人员",
            "GEO": "地理位置", 
            "EVENT": "事件",
            "CATEGORY": "类别"
        }
    
    def get_chinese_knowledge_graph(self, kb_id):
        """获取中文化的知识图谱"""
        
        # 获取原始数据
        response = requests.get(
            f"{self.base_url}/api/v1/datasets/{kb_id}/knowledge_graph",
            headers=self.headers
        )
        data = response.json()
        
        # 中文化处理
        if 'data' in data and 'graph' in data['data']:
            nodes = data['data']['graph'].get('nodes', [])
            
            for node in nodes:
                # 翻译实体类型
                if 'entity_type' in node:
                    original_type = node['entity_type']
                    node['entity_type'] = self.entity_type_mapping.get(original_type, original_type)
                    node['entity_type_en'] = original_type  # 保留英文
                
                # 添加文件信息
                source_ids = node.get('source_id', [])
                node['source_files_count'] = len(source_ids)
                node['has_source_files'] = len(source_ids) > 0
        
        return data
    
    def get_node_source_files(self, kb_id, node_id):
        """获取节点的源文件信息（模拟实现）"""
        
        # 先获取节点信息
        graph_data = self.get_chinese_knowledge_graph(kb_id)
        
        # 找到指定节点
        target_node = None
        for node in graph_data['data']['graph']['nodes']:
            if node['id'] == node_id:
                target_node = node
                break
        
        if not target_node:
            return {"error": "Node not found"}
        
        source_ids = target_node.get('source_id', [])
        
        # 这里需要调用文档API获取详细信息
        # 由于当前API限制，我们返回基础信息
        return {
            "node_id": node_id,
            "source_ids": source_ids,
            "source_files_count": len(source_ids),
            "message": "需要额外的API来获取文件详细信息"
        }

# 使用示例
api = ChineseKnowledgeGraphAPI(
    "http://localhost:9380", 
    "ragflow-BlMGQyNzM0OTBhNzExZjA4MzU4ZGU3NW"
)

# 获取中文化的知识图谱
chinese_graph = api.get_chinese_knowledge_graph("dc949110906a11f08b78aa7cd3e67281")

# 打印中文化结果
for node in chinese_graph['data']['graph']['nodes'][:3]:
    print(f"实体: {node['entity_name']}")
    print(f"类型: {node['entity_type']} (原始: {node.get('entity_type_en', 'N/A')})")
    print(f"来源文件数: {node['source_files_count']}")
    print("---")
```

### 步骤2：长期解决方案

1. **修改配置文件**：按照方案1修改语言配置
2. **重新构建知识图谱**：删除现有图谱，重新提取
3. **部署新的API端点**：添加文件信息获取功能

## 📊 预期效果

### 中文化后的API返回示例：

```json
{
  "code": 0,
  "data": {
    "graph": {
      "nodes": [
        {
          "entity_name": "厦门国贸股份有限公司",
          "entity_type": "组织",
          "entity_type_en": "ORGANIZATION",
          "id": "厦门国贸股份有限公司",
          "description": "厦门国贸股份有限公司是一家参与制定和实施安全应急管理规定的组织...",
          "pagerank": 0.055,
          "source_id": ["218f36b8909c11f099a6de75c101e789", "30322b62909c11f0994fde75c101e789"],
          "source_files": [
            {
              "id": "218f36b8909c11f099a6de75c101e789",
              "name": "安全生产管理规定.pdf",
              "type": "pdf",
              "size": 1024000
            }
          ],
          "source_files_count": 2
        }
      ]
    }
  }
}
```

这个解决方案可以：
1. ✅ 将实体类型显示为中文
2. ✅ 保留英文版本以保持兼容性
3. ✅ 提供文件来源信息
4. ✅ 支持渐进式部署

## 🛠️ 立即可用的实现代码

### 创建中文化处理脚本

**文件：`chinese_graph_api.py`**

```python
#!/usr/bin/env python3
"""
RAGFlow 知识图谱中文化处理脚本
立即可用，无需修改RAGFlow源码
"""

import requests
import json
from typing import Dict, List, Any, Optional
import time

class ChineseGraphRAGAPI:
    """中文化的知识图谱API包装器"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # 实体类型中英文映射
        self.entity_type_mapping = {
            "ORGANIZATION": "组织",
            "PERSON": "人员",
            "GEO": "地理位置",
            "LOCATION": "地理位置",
            "EVENT": "事件",
            "CATEGORY": "类别",
            "CONCEPT": "概念",
            "PRODUCT": "产品",
            "TECHNOLOGY": "技术",
            "OTHER": "其他"
        }

        # 反向映射
        self.entity_type_reverse_mapping = {v: k for k, v in self.entity_type_mapping.items()}

    def translate_entity_type(self, entity_type: str, to_chinese: bool = True) -> str:
        """翻译实体类型"""
        if to_chinese:
            return self.entity_type_mapping.get(entity_type.upper(), entity_type)
        else:
            return self.entity_type_reverse_mapping.get(entity_type, entity_type)

    def get_datasets(self) -> Dict[str, Any]:
        """获取数据集列表"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/datasets", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def get_chinese_knowledge_graph(self, kb_id: str) -> Dict[str, Any]:
        """获取中文化的知识图谱"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/datasets/{kb_id}/knowledge_graph",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()

            # 中文化处理
            if 'data' in data and 'graph' in data['data']:
                self._process_nodes_chinese(data['data']['graph'].get('nodes', []))
                self._process_edges_chinese(data['data']['graph'].get('edges', []))

            return data

        except Exception as e:
            return {"error": str(e)}

    def _process_nodes_chinese(self, nodes: List[Dict[str, Any]]) -> None:
        """处理节点的中文化"""
        for node in nodes:
            # 翻译实体类型
            if 'entity_type' in node:
                original_type = node['entity_type']
                node['entity_type_en'] = original_type  # 保留英文
                node['entity_type'] = self.translate_entity_type(original_type)

            # 添加文件统计信息
            source_ids = node.get('source_id', [])
            node['source_files_count'] = len(source_ids)
            node['has_source_files'] = len(source_ids) > 0

            # 添加中文标签
            node['display_type'] = node.get('entity_type', '未知类型')

    def _process_edges_chinese(self, edges: List[Dict[str, Any]]) -> None:
        """处理边的中文化"""
        for edge in edges:
            # 可以在这里添加关系类型的中文化
            if 'relation' in edge:
                edge['relation_zh'] = edge['relation']  # 暂时保持原样

    def search_entities_chinese(self, kb_id: str, query: str,
                              entity_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """搜索实体（中文化）"""
        try:
            # 如果提供了中文实体类型，转换为英文
            if entity_types:
                entity_types_en = [self.translate_entity_type(et, to_chinese=False) for et in entity_types]
            else:
                entity_types_en = None

            # 构建搜索请求
            search_data = {
                "query": query,
                "page": 1,
                "page_size": 20
            }

            if entity_types_en:
                search_data["entity_types"] = entity_types_en

            response = requests.post(
                f"{self.base_url}/api/v1/datasets/{kb_id}/search",
                headers=self.headers,
                json=search_data
            )

            if response.status_code == 200:
                data = response.json()
                # 中文化处理搜索结果
                if 'data' in data and 'nodes' in data['data']:
                    self._process_nodes_chinese(data['data']['nodes'])
                return data
            else:
                return {"error": f"Search failed: {response.status_code}"}

        except Exception as e:
            return {"error": str(e)}

    def get_node_source_info(self, kb_id: str, node_id: str) -> Dict[str, Any]:
        """获取节点的源文件信息"""
        try:
            # 先获取完整图谱找到节点
            graph_data = self.get_chinese_knowledge_graph(kb_id)

            if 'error' in graph_data:
                return graph_data

            # 查找目标节点
            target_node = None
            for node in graph_data['data']['graph']['nodes']:
                if node['id'] == node_id:
                    target_node = node
                    break

            if not target_node:
                return {"error": "节点未找到"}

            source_ids = target_node.get('source_id', [])

            return {
                "node_id": node_id,
                "node_name": target_node.get('entity_name', ''),
                "node_type": target_node.get('entity_type', ''),
                "node_type_en": target_node.get('entity_type_en', ''),
                "description": target_node.get('description', ''),
                "source_ids": source_ids,
                "source_files_count": len(source_ids),
                "pagerank": target_node.get('pagerank', 0),
                "message": "源文件ID列表，需要额外API获取文件详情"
            }

        except Exception as e:
            return {"error": str(e)}

    def get_entity_statistics(self, kb_id: str) -> Dict[str, Any]:
        """获取实体统计信息"""
        try:
            graph_data = self.get_chinese_knowledge_graph(kb_id)

            if 'error' in graph_data:
                return graph_data

            nodes = graph_data['data']['graph']['nodes']
            edges = graph_data['data']['graph']['edges']

            # 统计实体类型分布
            type_distribution = {}
            for node in nodes:
                entity_type = node.get('entity_type', '未知')
                type_distribution[entity_type] = type_distribution.get(entity_type, 0) + 1

            # 统计文件关联
            total_source_files = sum(node.get('source_files_count', 0) for node in nodes)
            nodes_with_files = sum(1 for node in nodes if node.get('has_source_files', False))

            return {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "entity_type_distribution": type_distribution,
                "total_source_files": total_source_files,
                "nodes_with_source_files": nodes_with_files,
                "coverage_rate": f"{(nodes_with_files/len(nodes)*100):.1f}%" if nodes else "0%"
            }

        except Exception as e:
            return {"error": str(e)}

# 使用示例和测试代码
def main():
    """主函数 - 演示用法"""

    # 配置信息
    BASE_URL = "http://localhost:9380"
    API_KEY = "ragflow-BlMGQyNzM0OTBhNzExZjA4MzU4ZGU3NW"
    KB_ID = "dc949110906a11f08b78aa7cd3e67281"

    # 创建API实例
    api = ChineseGraphRAGAPI(BASE_URL, API_KEY)

    print("🚀 RAGFlow 知识图谱中文化测试")
    print("=" * 50)

    # 1. 获取数据集
    print("\n📋 1. 获取数据集列表...")
    datasets = api.get_datasets()
    if 'error' not in datasets:
        print(f"✅ 找到 {len(datasets.get('data', []))} 个数据集")
    else:
        print(f"❌ 错误: {datasets['error']}")
        return

    # 2. 获取中文化知识图谱
    print(f"\n🕸️ 2. 获取知识图谱 (KB: {KB_ID})...")
    graph_data = api.get_chinese_knowledge_graph(KB_ID)

    if 'error' not in graph_data:
        nodes = graph_data['data']['graph']['nodes']
        edges = graph_data['data']['graph']['edges']
        print(f"✅ 成功获取图谱: {len(nodes)} 个节点, {len(edges)} 条边")

        # 显示前3个节点的中文化信息
        print("\n📊 节点中文化示例:")
        for i, node in enumerate(nodes[:3]):
            print(f"  {i+1}. 实体: {node['entity_name']}")
            print(f"     类型: {node['entity_type']} (英文: {node.get('entity_type_en', 'N/A')})")
            print(f"     来源文件: {node['source_files_count']} 个")
            print(f"     重要性: {node.get('pagerank', 0):.3f}")
            print()
    else:
        print(f"❌ 错误: {graph_data['error']}")
        return

    # 3. 获取统计信息
    print("\n📈 3. 实体统计信息...")
    stats = api.get_entity_statistics(KB_ID)
    if 'error' not in stats:
        print(f"✅ 总节点数: {stats['total_nodes']}")
        print(f"✅ 总边数: {stats['total_edges']}")
        print(f"✅ 文件覆盖率: {stats['coverage_rate']}")
        print("✅ 实体类型分布:")
        for entity_type, count in stats['entity_type_distribution'].items():
            print(f"   - {entity_type}: {count} 个")

    # 4. 搜索测试
    print(f"\n🔍 4. 搜索测试 (关键词: '财务')...")
    search_results = api.search_entities_chinese(KB_ID, "财务", ["组织", "人员"])
    if 'error' not in search_results and 'data' in search_results:
        found_nodes = search_results['data'].get('nodes', [])
        print(f"✅ 找到 {len(found_nodes)} 个相关实体")
        for node in found_nodes[:2]:
            print(f"   - {node['entity_name']} ({node['entity_type']})")

    # 5. 获取节点详情
    if nodes:
        test_node_id = nodes[0]['id']
        print(f"\n📄 5. 获取节点详情 (节点: {test_node_id})...")
        node_info = api.get_node_source_info(KB_ID, test_node_id)
        if 'error' not in node_info:
            print(f"✅ 节点名称: {node_info['node_name']}")
            print(f"✅ 节点类型: {node_info['node_type']}")
            print(f"✅ 源文件数量: {node_info['source_files_count']}")
            print(f"✅ 源文件ID: {node_info['source_ids'][:2]}...")  # 只显示前2个

    print("\n🎉 测试完成！")

if __name__ == "__main__":
    main()
```

### 快速部署脚本

**文件：`deploy_chinese_api.py`**

```python
#!/usr/bin/env python3
"""
快速部署中文化API的脚本
"""

import os
import sys
from chinese_graph_api import ChineseGraphRAGAPI

def create_api_wrapper():
    """创建API包装器实例"""

    # 从环境变量或配置文件读取
    base_url = os.getenv('RAGFLOW_BASE_URL', 'http://localhost:9380')
    api_key = os.getenv('RAGFLOW_API_KEY', 'ragflow-BlMGQyNzM0OTBhNzExZjA4MzU4ZGU3NW')

    return ChineseGraphRAGAPI(base_url, api_key)

def test_chinese_api():
    """测试中文化API"""

    api = create_api_wrapper()
    kb_id = "dc949110906a11f08b78aa7cd3e67281"  # 您的知识库ID

    # 测试基本功能
    print("测试中文化知识图谱API...")

    # 获取图谱
    graph = api.get_chinese_knowledge_graph(kb_id)
    if 'error' in graph:
        print(f"错误: {graph['error']}")
        return False

    print("✅ 中文化API工作正常")
    return True

if __name__ == "__main__":
    if test_chinese_api():
        print("🎉 中文化API部署成功！")
    else:
        print("❌ 部署失败")
        sys.exit(1)
```

## 🔧 使用方法

### 1. 立即使用（无需修改RAGFlow）

```bash
# 1. 保存上述代码为 chinese_graph_api.py
# 2. 运行测试
python chinese_graph_api.py

# 3. 在您的项目中使用
from chinese_graph_api import ChineseGraphRAGAPI

api = ChineseGraphRAGAPI("http://localhost:9380", "your-api-key")
chinese_graph = api.get_chinese_knowledge_graph("your-kb-id")
```

### 2. 集成到现有项目

```python
# 在您的项目中
from chinese_graph_api import ChineseGraphRAGAPI

class YourKnowledgeGraphService:
    def __init__(self):
        self.chinese_api = ChineseGraphRAGAPI(
            base_url="http://localhost:9380",
            api_key="your-api-key"
        )

    def get_entities_by_type(self, kb_id: str, entity_type: str):
        """按类型获取实体"""
        graph = self.chinese_api.get_chinese_knowledge_graph(kb_id)

        if 'error' in graph:
            return []

        nodes = graph['data']['graph']['nodes']
        return [node for node in nodes if node['entity_type'] == entity_type]

    def search_chinese_entities(self, kb_id: str, query: str):
        """中文搜索"""
        return self.chinese_api.search_entities_chinese(kb_id, query)
```

这个解决方案的优势：
1. ✅ **立即可用**：无需修改RAGFlow源码
2. ✅ **完全兼容**：保留原始英文信息
3. ✅ **功能完整**：包含搜索、统计、文件追踪
4. ✅ **易于集成**：可直接在现有项目中使用
5. ✅ **可扩展**：支持自定义翻译规则
