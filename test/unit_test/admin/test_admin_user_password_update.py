#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
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

import base64
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT_DIR = Path(__file__).resolve().parents[3]
ADMIN_SERVER_DIR = ROOT_DIR / "admin" / "server"
ADMIN_SERVICES_FILE = ADMIN_SERVER_DIR / "services.py"
ADMIN_AUTH_FILE = ADMIN_SERVER_DIR / "auth.py"
SERVICES_MODULE_NAME = "admin_server_services_under_test"
AUTH_MODULE_NAME = "admin_server_auth_under_test"


def _load_admin_services_module():
    if SERVICES_MODULE_NAME in sys.modules:
        return sys.modules[SERVICES_MODULE_NAME]

    if str(ADMIN_SERVER_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_SERVER_DIR))

    spec = importlib.util.spec_from_file_location(SERVICES_MODULE_NAME, ADMIN_SERVICES_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec from {ADMIN_SERVICES_FILE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[SERVICES_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def _load_admin_auth_module():
    if AUTH_MODULE_NAME in sys.modules:
        return sys.modules[AUTH_MODULE_NAME]

    if str(ADMIN_SERVER_DIR) not in sys.path:
        sys.path.insert(0, str(ADMIN_SERVER_DIR))

    spec = importlib.util.spec_from_file_location(AUTH_MODULE_NAME, ADMIN_AUTH_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec from {ADMIN_AUTH_FILE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[AUTH_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def test_create_user_uses_plain_password_for_storage(monkeypatch):
    services = _load_admin_services_module()

    username = "alice@example.com"
    plain_password = "AdminCreate#2026"
    password_base64 = base64.b64encode(plain_password.encode("utf-8")).decode("utf-8")
    calls: dict[str, str] = {}

    monkeypatch.setattr(services.UserService, "query", lambda **kwargs: [])
    monkeypatch.setattr(services, "decrypt", lambda _: password_base64)

    def fake_validate_password(password_plain: str, email: str):
        calls["validated_plain"] = password_plain
        calls["validated_email"] = email
        return None

    def fake_create_new_user(user_info: dict):
        calls["stored_password"] = user_info["password"]
        return {"success": True, "user_info": user_info}

    monkeypatch.setattr(services, "validate_password", fake_validate_password)
    monkeypatch.setattr(services, "create_new_user", fake_create_new_user)

    result = services.UserMgr.create_user(username, "encrypted-input")

    assert result["success"] is True
    assert calls["validated_plain"] == plain_password
    assert calls["validated_email"] == username
    assert calls["stored_password"] == plain_password


def test_update_user_password_uses_plain_for_hash_check_and_storage(monkeypatch):
    services = _load_admin_services_module()

    username = "alice@example.com"
    new_plain_password = "AdminReset#2026"
    new_password_base64 = base64.b64encode(new_plain_password.encode("utf-8")).decode("utf-8")
    user = SimpleNamespace(id="user-1", password="hashed-old-password")
    calls: dict[str, str | tuple[str, str]] = {}

    monkeypatch.setattr(services.UserService, "query_user_by_email", lambda email: [user])
    monkeypatch.setattr(services, "decrypt", lambda _: new_password_base64)

    def fake_validate_password(password_plain: str, email: str):
        calls["validated_plain"] = password_plain
        calls["validated_email"] = email
        return None

    def fake_check_password_hash(_stored_hash: str, candidate: str):
        calls["checked_candidate"] = candidate
        return False

    def fake_update_user_password(user_id: str, password_value: str):
        calls["updated"] = (user_id, password_value)

    monkeypatch.setattr(services, "validate_password", fake_validate_password)
    monkeypatch.setattr(services, "check_password_hash", fake_check_password_hash)
    monkeypatch.setattr(services.UserService, "update_user_password", fake_update_user_password)

    message = services.UserMgr.update_user_password(username, "encrypted-input")

    assert message == "Password updated successfully!"
    assert calls["validated_plain"] == new_plain_password
    assert calls["validated_email"] == username
    assert calls["checked_candidate"] == new_plain_password
    assert calls["updated"] == (user.id, new_plain_password)


def test_update_user_password_noop_when_plain_password_unchanged(monkeypatch):
    services = _load_admin_services_module()

    username = "alice@example.com"
    new_plain_password = "AdminReset#2026"
    new_password_base64 = base64.b64encode(new_plain_password.encode("utf-8")).decode("utf-8")
    user = SimpleNamespace(id="user-1", password="hashed-old-password")
    calls: dict[str, str | tuple[str, str]] = {}

    monkeypatch.setattr(services.UserService, "query_user_by_email", lambda email: [user])
    monkeypatch.setattr(services, "decrypt", lambda _: new_password_base64)
    monkeypatch.setattr(services, "validate_password", lambda _password_plain, _email: None)

    def fake_check_password_hash(_stored_hash: str, candidate: str):
        calls["checked_candidate"] = candidate
        return candidate == new_plain_password

    monkeypatch.setattr(services, "check_password_hash", fake_check_password_hash)

    def fake_update_user_password(user_id: str, password_value: str):
        calls["updated"] = (user_id, password_value)

    monkeypatch.setattr(services.UserService, "update_user_password", fake_update_user_password)

    message = services.UserMgr.update_user_password(username, "encrypted-input")

    assert message == "Same password, no need to update!"
    assert calls["checked_candidate"] == new_plain_password
    assert "updated" not in calls


def test_get_all_users_exposes_login_lock_state(monkeypatch):
    services = _load_admin_services_module()

    users = [
        SimpleNamespace(
            email="locked@example.com",
            nickname="locked",
            create_date="2026-04-05",
            is_active="1",
            is_superuser=False,
        ),
        SimpleNamespace(
            email="ok@example.com",
            nickname="ok",
            create_date="2026-04-05",
            is_active="1",
            is_superuser=False,
        ),
    ]

    class FakeRedis:
        @staticmethod
        def exist(key: str):
            return key == "login_lock:locked@example.com"

    monkeypatch.setattr(services.UserService, "get_all_users", lambda: users)
    monkeypatch.setattr(services, "REDIS_CONN", FakeRedis())

    result = services.UserMgr.get_all_users()

    assert result[0]["email"] == "locked@example.com"
    assert result[0]["is_locked"] is True
    assert result[1]["email"] == "ok@example.com"
    assert result[1]["is_locked"] is False


def test_unlock_user_clears_both_login_lock_keys(monkeypatch):
    services = _load_admin_services_module()

    deleted_keys: list[str] = []
    user = SimpleNamespace(id="user-1", email="locked@example.com")

    class FakeRedis:
        @staticmethod
        def delete(key: str):
            deleted_keys.append(key)

    monkeypatch.setattr(services.UserService, "query_user_by_email", lambda _username: [user])
    monkeypatch.setattr(services, "REDIS_CONN", FakeRedis())
    monkeypatch.setattr(
        services,
        "login_security_keys",
        lambda _email: {
            "attempts": "login_attempts:locked@example.com",
            "lock": "login_lock:locked@example.com",
        },
    )

    message = services.UserMgr.unlock_user("locked@example.com")

    assert message == "User unlocked successfully!"
    assert deleted_keys == [
        "login_attempts:locked@example.com",
        "login_lock:locked@example.com",
    ]


def test_login_lock_message_guides_contact_admin(monkeypatch):
    auth = _load_admin_auth_module()

    class FakeRedis:
        def __init__(self):
            self.store = {"login_lock:alice@example.com": "1"}

        def exist(self, key: str):
            return key in self.store

        def get(self, key: str):
            return self.store.get(key)

        def set(self, key: str, value, _ttl: int):
            self.store[key] = str(value)

        def delete(self, key: str):
            self.store.pop(key, None)

    fake_redis = FakeRedis()

    monkeypatch.setattr(auth, "REDIS_CONN", fake_redis)
    monkeypatch.setattr(
        auth,
        "request",
        SimpleNamespace(headers={}, remote_addr="127.0.0.1", path="/api/v1/admin/login"),
    )
    monkeypatch.setattr(auth.AuditLogService, "log", lambda **_kwargs: None)
    monkeypatch.setattr(auth.UserService, "query", lambda **_kwargs: [SimpleNamespace(id="u1", email="alice@example.com")])

    with pytest.raises(auth.AdminException) as locked_error:
        auth.login_admin("alice@example.com", "encrypted")

    assert "contact an administrator to unlock it" in str(locked_error.value)
