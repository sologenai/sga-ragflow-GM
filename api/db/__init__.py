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

from enum import IntEnum
from strenum import StrEnum


class UserTenantRole(StrEnum):
    OWNER = 'owner'
    ADMIN = 'admin'
    NORMAL = 'normal'
    INVITE = 'invite'


class TenantPermission(StrEnum):
    ME = 'me'
    TEAM = 'team'


class SerializedType(IntEnum):
    PICKLE = 1
    JSON = 2


class FileType(StrEnum):
    PDF = 'pdf'
    DOC = 'doc'
    VISUAL = 'visual'
    AURAL = 'aural'
    VIRTUAL = 'virtual'
    FOLDER = 'folder'
    OTHER = "other"

VALID_FILE_TYPES = {FileType.PDF, FileType.DOC, FileType.VISUAL, FileType.AURAL, FileType.VIRTUAL, FileType.FOLDER, FileType.OTHER}


class InputType(StrEnum):
    LOAD_STATE = "load_state"  # e.g. loading a current full state or a save state, such as from a file
    POLL = "poll"  # e.g. calling an API to get all documents in the last hour
    EVENT = "event"  # e.g. registered an endpoint as a listener, and processing connector events
    SLIM_RETRIEVAL = "slim_retrieval"


class CanvasCategory(StrEnum):
    Agent = "agent_canvas"
    DataFlow = "dataflow_canvas"


class PipelineTaskType(StrEnum):
    PARSE = "Parse"
    DOWNLOAD = "Download"
    RAPTOR = "RAPTOR"
    GRAPH_RAG = "GraphRAG"
    MINDMAP = "Mindmap"


VALID_PIPELINE_TASK_TYPES = {PipelineTaskType.PARSE, PipelineTaskType.DOWNLOAD, PipelineTaskType.RAPTOR, PipelineTaskType.GRAPH_RAG, PipelineTaskType.MINDMAP}


PIPELINE_SPECIAL_PROGRESS_FREEZE_TASK_TYPES = {PipelineTaskType.RAPTOR.lower(), PipelineTaskType.GRAPH_RAG.lower(), PipelineTaskType.MINDMAP.lower()}


KNOWLEDGEBASE_FOLDER_NAME=".knowledgebase"


# Security audit action types for audit_log.action_type.
class AuditActionType(StrEnum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    ACCOUNT_LOCKED = "account_locked"
    SESSION_EXPIRED = "session_expired"
    SESSION_KICKED = "session_kicked"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    USER_ACTIVATED = "user_activated"
    USER_DEACTIVATED = "user_deactivated"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"
    ADMIN_GRANTED = "admin_granted"
    ADMIN_REVOKED = "admin_revoked"
    SETTINGS_UPDATED = "settings_updated"
    KB_CREATED = "kb_created"
    KB_DELETED = "kb_deleted"
    KB_UPDATED = "kb_updated"
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_DELETED = "document_deleted"
    LOG_CLEARED = "log_cleared"
