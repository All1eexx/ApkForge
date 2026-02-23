# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : apk_builder.py
# Purpose : Builds APK using apktool.
# =============================================================================

import re
from pathlib import Path

from platform_utils import run_command, setup_utf8_environment


class ApkBuilder:
    def __init__(self, apktool_jar: Path, logger=None):
        self.apktool_jar = apktool_jar
        self.logger = logger
        setup_utf8_environment()

    def build(self, modded_dir: Path, output_apk: Path) -> bool:
        if self.logger:
            self.logger.info("  Building APK with apktool...")

        build_cmd = [
            "java",
            "-jar",
            str(self.apktool_jar),
            "b",
            str(modded_dir),
            "-o",
            str(output_apk),
        ]

        result = run_command(build_cmd)

        if result.returncode != 0 and "android:multiDexEnabled" in result.stderr:
            return self._retry_without_multidex(modded_dir, build_cmd)

        self._check_result(result, "apktool build")
        return True

    def _retry_without_multidex(self, modded_dir: Path, original_cmd: list) -> bool:
        if self.logger:
            self.logger.info(
                "  [WARNING] Detected multiDexEnabled error, trying alternative approach..."
            )

        manifest_path = modded_dir / "AndroidManifest.xml"
        if manifest_path.exists():
            self._remove_multidex_from_manifest(manifest_path)

            if self.logger:
                self.logger.info(
                    "  Removed multiDexEnabled attribute, retrying build..."
                )

            result = run_command(original_cmd)
            self._check_result(result, "apktool build (after removing multidex)")
            return True

        return False

    @staticmethod
    def _remove_multidex_from_manifest(manifest_path: Path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            content = f.read()

        content = re.sub(r'\s+android:multiDexEnabled="true"', "", content)
        content = re.sub(r'\s+multiDexEnabled="true"', "", content)

        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def _check_result(result, step_name):
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout
            if error_msg and len(error_msg) > 500:
                error_msg = error_msg[:500] + "..."
            raise RuntimeError(f"{step_name} failed: {error_msg}")
