# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : smali_updater.py
# Purpose : Updates BuildConfig.smali with new version code, version name,
#           application ID and build type.
# =============================================================================

import re
from pathlib import Path


class SmaliUpdater:
    PATTERNS = {
        "VERSION_CODE": r"VERSION_CODE:I\s*=\s*(0x[0-9a-fA-F]+)",
        "VERSION_NAME": r'VERSION_NAME:Ljava/lang/String;\s*=\s*"([^"]*)"',
        "APPLICATION_ID": r'APPLICATION_ID:Ljava/lang/String;\s*=\s*"([^"]*)"',
        "BUILD_TYPE": r'BUILD_TYPE:Ljava/lang/String;\s*=\s*"([^"]*)"',
    }

    FIELD_VERSION_CODE = "VERSION_CODE:I = "
    FIELD_VERSION_NAME = 'VERSION_NAME:Ljava/lang/String; = "'
    FIELD_APPLICATION_ID = 'APPLICATION_ID:Ljava/lang/String; = "'
    FIELD_BUILD_TYPE = 'BUILD_TYPE:Ljava/lang/String; = "'

    def __init__(self, smali_path: Path):
        self.smali_path = smali_path
        self.lines = []
        self.old_values = {}

    def load(self):
        if not self.smali_path.exists():
            raise FileNotFoundError(f"BuildConfig.smali not found at {self.smali_path}")

        with open(self.smali_path, "r", encoding="utf-8") as f:
            self.lines = f.readlines()

        self._extract_old_values()

    def _extract_old_values(self):
        content = "".join(self.lines)
        self._extract_with_regex(content)
        self._extract_from_lines()

    def _extract_with_regex(self, content):
        for name, pattern in self.PATTERNS.items():
            match = re.search(pattern, content)
            if match:
                self.old_values[name] = match.group(1)

    def _extract_from_lines(self):
        for line in self.lines:
            self._extract_version_code(line)
            self._extract_string_field(line, "VERSION_NAME", self.FIELD_VERSION_NAME)
            self._extract_string_field(
                line, "APPLICATION_ID", self.FIELD_APPLICATION_ID
            )
            self._extract_string_field(line, "BUILD_TYPE", self.FIELD_BUILD_TYPE)

    def _extract_version_code(self, line):
        if self.FIELD_VERSION_CODE in line and "0x" in line:
            parts = line.split("0x")
            if len(parts) == 2:
                hex_str = parts[1].strip().rstrip("\n")
                self.old_values["VERSION_CODE"] = f"0x{hex_str}"

    def _extract_string_field(self, line, field_name, field_identifier):
        if field_identifier in line:
            value = self._parse_string_value(line)
            if value is not None:
                self.old_values[field_name] = value

    @staticmethod
    def _parse_string_value(line):
        start_idx = line.find('= "')
        if start_idx == -1:
            return None

        start_idx += 3
        end_idx = line.find('"', start_idx)

        if end_idx != -1:
            return line[start_idx:end_idx]

        return None

    def update_build_config(
            self, version_code, version_name, application_id, build_type
    ):
        version_hex = f"0x{version_code:x}".lower()

        config = {
            self.FIELD_VERSION_CODE: (
                "VERSION_CODE",
                version_hex,
                self._update_version_code,
            ),
            self.FIELD_VERSION_NAME: (
                "VERSION_NAME",
                version_name,
                self._update_string_value,
            ),
            self.FIELD_APPLICATION_ID: (
                "APPLICATION_ID",
                application_id,
                self._update_string_value,
            ),
            self.FIELD_BUILD_TYPE: (
                "BUILD_TYPE",
                build_type,
                self._update_string_value,
            ),
        }

        updated_lines = []
        changes = []

        for line in self.lines:
            updated_line, change = self._process_line(line, config)
            updated_lines.append(updated_line)
            if change:
                changes.append(change)

        if changes:
            self._write_file(updated_lines)

        return changes

    def _process_line(self, line, config):
        for field_identifier, (field_name, new_value, update_func) in config.items():
            if field_identifier in line:
                if field_identifier == self.FIELD_VERSION_CODE and "0x" not in line:
                    continue

                updated_line = update_func(line, new_value)

                if updated_line != line:
                    return updated_line, (field_name, new_value)

                return updated_line, None

        return line, None

    @staticmethod
    def _update_version_code(line, version_hex):
        parts = line.split("0x")
        if len(parts) == 2:
            return parts[0] + version_hex + "\n"
        return line

    @staticmethod
    def _update_string_value(line, new_value):
        start_idx = line.find('= "')
        if start_idx == -1:
            return line

        start_idx += 3
        end_idx = line.find('"', start_idx)

        if end_idx != -1:
            return line[:start_idx] + new_value + line[end_idx:]

        return line

    def _write_file(self, lines):
        with open(self.smali_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def get_old_values(self):
        return self.old_values
