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
PROFILE_PAGE_FILE = ROOT_DIR / "web" / "src" / "pages" / "user-setting" / "profile" / "index.tsx"
PROFILE_HOOK_FILE = ROOT_DIR / "web" / "src" / "pages" / "user-setting" / "profile" / "hooks" / "use-profile.ts"
SETTING_REQUEST_HOOK_FILE = ROOT_DIR / "web" / "src" / "hooks" / "use-user-setting-request.tsx"


def test_password_schema_isolated_from_unrelated_fields():
    source = PROFILE_PAGE_FILE.read_text(encoding="utf-8")

    assert "const passwordSchema = z" in source
    assert "currPasswd" in source
    assert "newPasswd" in source
    assert "confirmPasswd" in source
    assert "getSchemaByEditType" in source
    assert "if (editType === EditType.editPassword)" in source


def test_password_submit_has_visible_validation_failure_feedback():
    source = PROFILE_PAGE_FILE.read_text(encoding="utf-8")

    assert "form.handleSubmit(" in source
    assert "(errors) => {" in source
    assert "message.error(errorMessage);" in source


def test_profile_hook_closes_modal_only_after_successful_save():
    source = PROFILE_HOOK_FILE.read_text(encoding="utf-8")

    assert "const code = await onSubmit(newProfile);" in source
    assert "if (code === 0) {" in source
    assert "setIsEditing(false);" in source
    assert "setEditForm({});" in source


def test_save_setting_has_explicit_error_feedback():
    source = SETTING_REQUEST_HOOK_FILE.read_text(encoding="utf-8")

    assert "onError: () => {" in source
    assert "message.error(t('message.requestError'));" in source
