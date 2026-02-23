# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : yaml_updater.py
# Purpose : Updates apktool.yml with new version information and APK filename.
# =============================================================================

from pathlib import Path


class YamlUpdater:
    def __init__(self, yml_path: Path):
        self.yml_path = yml_path
        self.lines = []

    def load(self):
        if not self.yml_path.exists():
            raise FileNotFoundError(f"apktool.yml not found at {self.yml_path}")

        with open(self.yml_path, "r", encoding="utf-8") as f:
            self.lines = f.readlines()

    def extract_values(self):
        values = {}

        for line in self.lines:
            stripped = line.strip()

            if stripped.startswith("versionCode:"):
                values["version_code"] = self._extract_value(stripped)
            elif stripped.startswith("versionName:"):
                values["version_name"] = self._extract_value(stripped)
            elif stripped.startswith("apkFileName:"):
                values["apk_file_name"] = self._extract_value(stripped)

        return values

    def update(self, version_code, version_name, app_name):
        new_apk_name = f"{app_name} ({version_name}).apk"
        updated = False

        for i, line in enumerate(self.lines):
            if line.lstrip().startswith("versionCode:"):
                self.lines[i] = f"  versionCode: {version_code}\n"
                updated = True
            elif line.lstrip().startswith("versionName:"):
                self.lines[i] = f"  versionName: {version_name}\n"
                updated = True
            elif line.lstrip().startswith("apkFileName:"):
                self.lines[i] = f"  apkFileName: {new_apk_name}\n"
                updated = True

        if updated:
            with open(self.yml_path, "w", encoding="utf-8") as f:
                f.writelines(self.lines)

        return new_apk_name, updated

    @staticmethod
    def _extract_value(line):
        return line.split(":", 1)[1].strip().strip("\"'")