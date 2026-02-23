# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : strings_updater.py
# Purpose : Updates app_name in strings.xml with the new application name.
# =============================================================================

import re
from pathlib import Path


class StringsUpdater:
    APP_NAME_KEYS = [
        "app_name",
        "game_name",
        "godot_project_name_string",
        "project_name_string",
        "application_name",
        "app_title",
        "app_display_name",
    ]

    def __init__(self, strings_path: Path):
        self.strings_path = strings_path
        self.old_app_name = None
        self.used_key = "app_name"

    def _find_app_name_tag(self, content: str):
        for key in self.APP_NAME_KEYS:
            patterns = [
                rf'<string\s+name\s*=\s*"{key}"\s*>(.*?)</string>',
                rf'<string\s+name="{key}">(.*?)</string>',
            ]

            for pattern in patterns:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    self.used_key = key
                    return match, key

        return None, None

    @staticmethod
    def _add_app_name_tag(content: str, new_app_name: str) -> str:
        if "</resources>" in content:
            new_content = content.replace(
                "</resources>",
                f'    <string name="app_name">{new_app_name}</string>\n</resources>',
            )
            print(f"    Added app_name tag with value: '{new_app_name}'")
            return new_content

        return content + f'\n    <string name="app_name">{new_app_name}</string>\n'

    def update_app_name(self, new_app_name):
        if not self.strings_path.exists():
            return False, f"File not found at {self.strings_path}"

        try:
            with open(self.strings_path, "r", encoding="utf-8", newline="") as f:
                content = f.read()

            match, found_key = self._find_app_name_tag(content)

            if not match:
                print("  No app name tag found, adding with key 'app_name'")
                new_content = self._add_app_name_tag(content, new_app_name)

                with open(self.strings_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(new_content)

                return True, f"Added app_name tag with value: '{new_app_name}'"

            self.old_app_name = match.group(1).strip()
            old_app_name_clean = re.sub(r"\s+", " ", self.old_app_name).strip()

            if old_app_name_clean == new_app_name:
                return (
                    True,
                    f"app_name already set to '{new_app_name}' (using key: {found_key})",
                )

            pattern = rf'<string\s+name\s*=\s*"{found_key}"\s*>(.*?)</string>'

            new_content = re.sub(
                pattern,
                f'<string name="{found_key}">{new_app_name}</string>',
                content,
                flags=re.DOTALL,
            )

            with open(self.strings_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(new_content)

            verify_match = re.search(pattern, new_content, re.DOTALL)
            if verify_match and verify_match.group(1).strip() == new_app_name:
                return (
                    True,
                    f"Updated app_name from '{old_app_name_clean}' to '{new_app_name}' (key: {found_key})",
                )
            else:
                return False, "Update verification failed"

        except Exception as e:
            return False, f"Error updating strings.xml: {e}"

    def get_old_app_name(self):
        return self.old_app_name

    def get_used_key(self):
        return self.used_key