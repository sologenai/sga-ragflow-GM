#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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


import logging
import time
import uuid
from functools import wraps
from datetime import datetime

from flask import jsonify, request
from flask_login import current_user, login_user
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer

from api.common.exceptions import AdminException, UserNotFoundError
from api.db.services import UserService
from api.db import AuditActionType, UserTenantRole
from api.db.services.audit_log_service import AuditLogService
from api.db.services.user_service import TenantService, UserTenantService
from common.constants import ActiveEnum, StatusEnum
from api.utils.crypt import decrypt
from api.utils.web_utils import (
    LOGIN_ATTEMPT_LIMIT,
    LOGIN_ATTEMPT_TTL,
    LOGIN_LOCK_SECONDS,
    SESSION_IDLE_TIMEOUT,
    login_security_keys,
    session_keys,
)
from rag.utils.redis_conn import REDIS_CONN
import base64
from common.misc_utils import get_uuid
from common.time_utils import current_timestamp, datetime_format, get_format_time
from common.connection_utils import sync_construct_response
from common import settings


def setup_auth(login_manager):
    @login_manager.request_loader
    def load_user(web_request):
        jwt = Serializer(secret_key=settings.SECRET_KEY)
        authorization = web_request.headers.get("Authorization")
        if authorization:
            try:
                access_token = str(jwt.loads(authorization))

                if not access_token or not access_token.strip():
                    logging.warning("Authentication attempt with empty access token")
                    return None

                # Access tokens should be UUIDs (32 hex characters)
                if len(access_token.strip()) < 32:
                    logging.warning(f"Authentication attempt with invalid token format: {len(access_token)} chars")
                    return None

                user = UserService.query(
                    access_token=access_token, status=StatusEnum.VALID.value
                )
                if user:
                    if not user[0].access_token or not user[0].access_token.strip():
                        logging.warning(f"User {user[0].email} has empty access_token in database")
                        return None
                    return user[0]
                else:
                    return None
            except Exception as e:
                logging.warning(f"load_user got exception {e}")
                return None
        else:
            return None


def init_default_admin():
    """
    Initialize the default superuser account.
    - Creates zhengys1@xindeco.com.cn as the primary superuser if not exists
    - Demotes admin@ragflow.io to non-superuser if it exists
    """
    # Define the primary superuser
    PRIMARY_SUPERUSER_EMAIL = "zhengys1@xindeco.com.cn"
    PRIMARY_SUPERUSER_PASSWORD = "admin"
    PRIMARY_SUPERUSER_NICKNAME = "超级管理员"

    # Check if primary superuser exists
    primary_users = UserService.query(email=PRIMARY_SUPERUSER_EMAIL)
    if not primary_users:
        # Create the primary superuser
        from api.db.joint_services.user_account_service import create_new_user
        user_info = {
            "email": PRIMARY_SUPERUSER_EMAIL,
            "password": PRIMARY_SUPERUSER_PASSWORD,
            "nickname": PRIMARY_SUPERUSER_NICKNAME,
            "login_channel": "password",
            "is_superuser": True,
        }
        result = create_new_user(user_info)
        if not result.get("success"):
            raise AdminException(f"Can't create superuser {PRIMARY_SUPERUSER_EMAIL}.", 500)
        logging.info(f"Created superuser: {PRIMARY_SUPERUSER_EMAIL}")
    else:
        # Ensure the primary superuser has superuser privileges
        primary_user = primary_users[0]
        if not primary_user.is_superuser:
            UserService.update_user(primary_user.id, {"is_superuser": True})
            logging.info(f"Updated {PRIMARY_SUPERUSER_EMAIL} to superuser")

    # Demote the old admin@ragflow.io account if it exists
    OLD_ADMIN_EMAIL = "admin@ragflow.io"
    old_admin_users = UserService.query(email=OLD_ADMIN_EMAIL)
    if old_admin_users:
        old_admin = old_admin_users[0]
        if old_admin.is_superuser:
            UserService.update_user(old_admin.id, {"is_superuser": False})
            logging.info(f"Demoted {OLD_ADMIN_EMAIL} from superuser to normal user")

    # Verify that at least one active superuser exists
    superusers = UserService.query(is_superuser=True)
    if not superusers:
        raise AdminException("No superuser found after initialization.", 500)
    if not any([u.is_active == ActiveEnum.ACTIVE.value for u in superusers]):
        raise AdminException("No active admin. Please update 'is_active' in db manually.", 500)
    else:
        default_admin_rows = [u for u in superusers if u.email == "admin@ragflow.io"]
        if default_admin_rows:
            default_admin = default_admin_rows[0].to_dict()
            exist, default_admin_tenant = TenantService.get_by_id(default_admin["id"])
            if not exist:
                add_tenant_for_admin(default_admin, UserTenantRole.OWNER)


def add_tenant_for_admin(user_info: dict, role: str):
    from api.db.services.tenant_llm_service import TenantLLMService
    from api.db.services.llm_service import get_init_tenant_llm

    tenant = {
        "id": user_info["id"],
        "name": user_info["nickname"] + "'s Kingdom",
        "llm_id": settings.CHAT_MDL,
        "embd_id": settings.EMBEDDING_MDL,
        "asr_id": settings.ASR_MDL,
        "parser_ids": settings.PARSERS,
        "img2txt_id": settings.IMAGE2TEXT_MDL
    }
    usr_tenant = {
        "tenant_id": user_info["id"],
        "user_id": user_info["id"],
        "invited_by": user_info["id"],
        "role": role
    }

    tenant_llm = get_init_tenant_llm(user_info["id"])
    TenantService.insert(**tenant)
    UserTenantService.insert(**usr_tenant)
    TenantLLMService.insert_many(tenant_llm)
    logging.info(
        f"Added tenant for email: {user_info['email']}, A default tenant has been set; changing the default models after login is strongly recommended.")


def check_admin_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = UserService.filter_by_id(current_user.id)
        if not user:
            raise UserNotFoundError(current_user.email)
        if not user.is_superuser:
            raise AdminException("Not admin", 403)
        if user.is_active == ActiveEnum.INACTIVE.value:
            raise AdminException(f"User {current_user.email} inactive", 403)

        return func(*args, **kwargs)

    return wrapper


def login_admin(email: str, password: str):
    """
    :param email: admin email
    :param password: string before decrypt (RSA encrypted, then base64 encoded)
    """
    ip_address = request.headers.get("X-Forwarded-For", request.headers.get("X-Real-Ip", request.remote_addr))
    if ip_address and "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()
    user_agent = request.headers.get("User-Agent", "")
    client_info = {"path": request.path}
    login_keys = login_security_keys(email)
    lock_message = "Account is locked due to too many failed login attempts. Please contact an administrator to unlock it."

    def handle_login_failure(reason: str, user_id: str | None = None):
        try:
            attempts = int(REDIS_CONN.get(login_keys["attempts"]) or 0) + 1
        except Exception:
            attempts = 1
        REDIS_CONN.set(login_keys["attempts"], attempts, LOGIN_ATTEMPT_TTL)

        AuditLogService.log(
            action_type=AuditActionType.LOGIN_FAILED,
            user_id=user_id,
            user_email=email,
            resource_type="admin_user",
            resource_id=user_id or email,
            detail={"reason": reason, "attempts": attempts, "limit": LOGIN_ATTEMPT_LIMIT},
            ip_address=ip_address,
            user_agent=user_agent,
            client_info=client_info,
        )

        if attempts >= LOGIN_ATTEMPT_LIMIT:
            REDIS_CONN.set(login_keys["lock"], "1", LOGIN_LOCK_SECONDS)
            AuditLogService.log(
                action_type=AuditActionType.ACCOUNT_LOCKED,
                user_id=user_id,
                user_email=email,
                resource_type="admin_user",
                resource_id=user_id or email,
                detail={
                    "reason": "too many failed login attempts",
                    "attempts": attempts,
                    "lock_seconds": LOGIN_LOCK_SECONDS,
                },
                ip_address=ip_address,
                user_agent=user_agent,
                client_info=client_info,
            )
            return True
        return False

    if REDIS_CONN.exist(login_keys["lock"]):
        AuditLogService.log(
            action_type=AuditActionType.ACCOUNT_LOCKED,
            user_email=email,
            resource_type="admin_user",
            resource_id=email,
            detail={"reason": "login denied while account is locked"},
            ip_address=ip_address,
            user_agent=user_agent,
            client_info=client_info,
        )
        raise AdminException(lock_message, 403)

    users = UserService.query(email=email)
    if not users:
        AuditLogService.log(
            action_type=AuditActionType.LOGIN_FAILED,
            user_email=email,
            resource_type="admin_user",
            resource_id=email,
            detail={"reason": "email is not registered"},
            ip_address=ip_address,
            user_agent=user_agent,
            client_info=client_info,
        )
        raise UserNotFoundError(email)

    try:
        # decrypt() returns base64-encoded password, need to decode it
        psw_base64 = decrypt(password)
        psw = base64.b64decode(psw_base64).decode('utf-8')
    except BaseException:
        locked = handle_login_failure("password decrypt failed")
        if locked:
            raise AdminException(lock_message, 403)
        raise AdminException("Fail to crypt password")

    user = UserService.query_user(email, psw)
    if not user:
        locked = handle_login_failure("email and password do not match")
        if locked:
            raise AdminException(lock_message, 403)
        raise AdminException("Email and password do not match!")
    if not user.is_superuser:
        locked = handle_login_failure("not admin", user.id)
        if locked:
            raise AdminException(lock_message, 403)
        raise AdminException("Not admin", 403)
    if user.is_active == ActiveEnum.INACTIVE.value:
        handle_login_failure("user inactive", user.id)
        raise AdminException(f"User {email} inactive", 403)

    REDIS_CONN.delete(login_keys["attempts"])
    REDIS_CONN.delete(login_keys["lock"])

    sk = session_keys(user.id)
    old_active_token = REDIS_CONN.get(sk["active_token"])
    resp = user.to_json()
    new_access_token = get_uuid()
    user.access_token = new_access_token
    login_user(user)
    user.update_time = (current_timestamp(),)
    user.update_date = (datetime_format(datetime.now()),)
    user.last_login_time = get_format_time()
    user.save()
    REDIS_CONN.set(sk["active_token"], new_access_token, SESSION_IDLE_TIMEOUT)
    REDIS_CONN.set(sk["last_activity"], str(int(time.time())), SESSION_IDLE_TIMEOUT)

    if old_active_token and old_active_token != new_access_token:
        AuditLogService.log(
            action_type=AuditActionType.SESSION_KICKED,
            user_id=user.id,
            user_email=email,
            resource_type="session",
            resource_id=user.id,
            detail={"reason": "new admin login invalidated previous session"},
            ip_address=ip_address,
            user_agent=user_agent,
            client_info=client_info,
        )

    AuditLogService.log(
        action_type=AuditActionType.LOGIN_SUCCESS,
        user_id=user.id,
        user_email=email,
        resource_type="admin_user",
        resource_id=user.id,
        detail={"message": "admin login success"},
        ip_address=ip_address,
        user_agent=user_agent,
        client_info=client_info,
    )
    msg = "Welcome back!"
    return sync_construct_response(data=resp, auth=user.get_id(), message=msg)


def check_admin(username: str, password: str):
    users = UserService.query(email=username)
    if not users:
        logging.info(f"Username: {username} is not registered!")
        user_info = {
            "id": uuid.uuid1().hex,
            "password": "admin",
            "nickname": "admin",
            "is_superuser": True,
            "email": "admin@ragflow.io",
            "creator": "system",
            "status": "1",
        }
        if not UserService.save(**user_info):
            raise AdminException("Can't init admin.", 500)

    user = UserService.query_user(username, password)
    if user:
        return True
    else:
        return False


def login_verify(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or 'username' not in auth.parameters or 'password' not in auth.parameters:
            return jsonify({
                "code": 401,
                "message": "Authentication required",
                "data": None
            }), 200

        username = auth.parameters['username']
        password = auth.parameters['password']
        try:
            if not check_admin(username, password):
                return jsonify({
                    "code": 500,
                    "message": "Access denied",
                    "data": None
                }), 200
        except Exception:
            logging.exception("An error occurred during admin login verification.")
            return jsonify({
                "code": 500,
                "message": "An internal server error occurred."
            }), 200

        return f(*args, **kwargs)

    return decorated
