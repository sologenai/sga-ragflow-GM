#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import json

from api.db import AuditActionType
from api.db.db_models import AuditLog, DB
from api.db.services.common_service import CommonService
from common.misc_utils import get_uuid
from common.time_utils import current_timestamp


class AuditLogService(CommonService):
    model = AuditLog

    @staticmethod
    def _serialize_json_field(value):
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    @classmethod
    @DB.connection_context()
    def log(cls, action_type, user_id=None, user_email=None,
            resource_type=None, resource_id=None,
            detail=None, ip_address=None,
            user_agent=None, client_info=None):
        action = action_type.value if isinstance(action_type, AuditActionType) else str(action_type)
        return cls.model.create(
            id=get_uuid(),
            user_id=user_id,
            user_email=user_email,
            action_type=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=cls._serialize_json_field(detail),
            ip_address=ip_address,
            user_agent=user_agent,
            client_info=cls._serialize_json_field(client_info),
        )

    @classmethod
    @DB.connection_context()
    def query_logs(cls, page=1, page_size=20, action_type=None,
                   user_email=None, date_from=None, date_to=None,
                   order_by="create_time", desc=True):
        page = max(int(page), 1)
        page_size = max(int(page_size), 1)
        query = cls.model.select()
        if action_type:
            query = query.where(cls.model.action_type == action_type)
        if user_email:
            query = query.where(cls.model.user_email.contains(user_email))
        if date_from:
            query = query.where(cls.model.create_time >= date_from)
        if date_to:
            query = query.where(cls.model.create_time <= date_to)

        total = query.count()
        order_field = getattr(cls.model, order_by, cls.model.create_time)
        if desc:
            order_field = order_field.desc()
        else:
            order_field = order_field.asc()
        items = list(query.order_by(order_field).paginate(page, page_size).dicts())
        return items, total

    @classmethod
    @DB.connection_context()
    def cleanup_old_logs(cls, retention_days=180):
        cutoff_ms = current_timestamp() - (retention_days * 24 * 60 * 60 * 1000)
        count = cls.model.select().where(cls.model.create_time < cutoff_ms).count()

        # Record the cleanup action before deleting old logs.
        cls.log(
            action_type=AuditActionType.LOG_CLEARED,
            detail={
                "retention_days": retention_days,
                "deleted_count": count,
            },
        )

        if count > 0:
            cls.model.delete().where(cls.model.create_time < cutoff_ms).execute()
        return count
