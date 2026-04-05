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

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
USER_APP_FILE = ROOT_DIR / "api" / "apps" / "user_app.py"


def test_user_setting_password_verification_uses_plain_password_contract():
    source = USER_APP_FILE.read_text(encoding="utf-8")

    assert "old_pwd_plain = base64.b64decode(old_pwd_base64).decode('utf-8')" in source
    assert "check_password_hash(current_user.password, old_pwd_plain)" in source
    assert "update_dict[\"password\"] = generate_password_hash(new_pwd_plain)" in source


def test_user_password_paths_store_plain_password_contract():
    source = USER_APP_FILE.read_text(encoding="utf-8")

    assert "\"password\": password_decoded" in source
    assert "UserService.update_user_password(user.id, new_pwd_string)" in source


def test_login_lock_message_guides_contact_admin_contract():
    source = USER_APP_FILE.read_text(encoding="utf-8")

    assert "Please contact an administrator to unlock it." in source
