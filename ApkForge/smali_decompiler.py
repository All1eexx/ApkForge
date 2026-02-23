# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : smali_decompiler.py
# Purpose : Decompiles DEX files to smali using baksmali.
# =============================================================================

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

from platform_utils import run_command_checked, setup_utf8_environment


class SmaliDecompiler:
    ANDROID_NS = "http://schemas.android.com/apk/res/android"

    def __init__(self, baksmali_jar: Path, modded_dir: Path, logger=None):
        self.baksmali_jar = baksmali_jar
        self.modded_dir = modded_dir
        self.logger = logger
        setup_utf8_environment()

    def decompile(
            self, dex_files: List[Path], target_dex_index: Optional[int] = None
    ) -> List[str]:
        if self.logger:
            self.logger.info("  Decompiling DEX to smali...")

        existing_smali, smali_dirs = self._get_existing_smali_dirs()
        created_dirs = set()

        use_auto_detection = target_dex_index is None or target_dex_index == 0

        for i, dex_file in enumerate(dex_files):
            if not use_auto_detection:
                target_dir = self._get_target_directory(
                    target_dex_index, existing_smali
                )
            else:
                target_dir = self._get_auto_detected_directory(smali_dirs, i)
                target_dir.mkdir(exist_ok=True, parents=True)

            created_dirs.add(target_dir.name)

            self._decompile_single_dex(dex_file, target_dir)

        self._print_summary(dex_files, created_dirs)

        return list(created_dirs)

    def _get_existing_smali_dirs(self):
        existing_smali = []
        smali_dirs = []

        for item in self.modded_dir.iterdir():
            if item.is_dir() and item.name.startswith("smali"):
                existing_smali.append(item.name)

                if item.name == "smali":
                    smali_dirs.append(1)
                else:
                    try:
                        index = int(item.name.replace("smali_classes", ""))
                        smali_dirs.append(index)
                    except ValueError:
                        continue

        smali_dirs.sort()

        if self.logger:
            dirs_str = ", ".join(existing_smali) if existing_smali else "none"
            self.logger.info(f"    Existing smali directories: {dirs_str}")

        return existing_smali, smali_dirs

    def _get_target_directory(self, target_dex_index, existing_smali):
        if target_dex_index == 1:
            target_dir = self.modded_dir / "smali"
        else:
            target_dir = self.modded_dir / f"smali_classes{target_dex_index}"

        target_dir.mkdir(exist_ok=True, parents=True)

        if target_dir.name in existing_smali and self.logger:
            self.logger.info(f"    NOTE: Adding files to existing {target_dir.name}")

        return target_dir

    def _get_auto_detected_directory(self, smali_dirs, file_index):
        if file_index == 0:
            if not smali_dirs:
                return self.modded_dir / "smali"

            max_index = max(smali_dirs)
            next_index = max_index + 1

            if next_index == 1:
                return self.modded_dir / "smali"
            else:
                return self.modded_dir / f"smali_classes{next_index}"
        else:
            base_index = max(smali_dirs) if smali_dirs else 0
            target_index = base_index + file_index + 1

            if target_index == 1:
                return self.modded_dir / "smali"
            else:
                return self.modded_dir / f"smali_classes{target_index}"

    def _decompile_single_dex(self, dex_file: Path, target_dir: Path):
        if self.logger:
            self.logger.info(f"    Decompiling {dex_file.name} to {target_dir.name}...")

        api_level = self._get_api_level_for_dex(dex_file)

        cmd = [
            "java",
            "-jar",
            str(self.baksmali_jar),
            "d",
            str(dex_file),
            "-o",
            str(target_dir),
            "--api",
            str(api_level),
        ]

        run_command_checked(cmd, f"baksmali failed for {dex_file.name}")

        smali_files = list(target_dir.rglob("*.smali"))
        if self.logger:
            self.logger.info(
                f"      Created {len(smali_files)} smali files in {target_dir.name}"
            )

    def _get_api_level_for_dex(self, dex_file: Path) -> int:
        try:
            if "classes2.dex" in str(dex_file) or "classes3.dex" in str(dex_file):
                return 21

            manifest_path = self.modded_dir / "AndroidManifest.xml"
            if manifest_path.exists():
                tree = ET.parse(manifest_path)
                root = tree.getroot()
                uses_sdk = root.find(".//uses-sdk")
                if uses_sdk is not None:
                    min_sdk = uses_sdk.get(f"{{{self.ANDROID_NS}}}minSdkVersion")
                    if min_sdk and min_sdk.isdigit():
                        return int(min_sdk)
        except (OSError, ValueError, ET.ParseError):
            pass

        return 21

    def _print_summary(self, dex_files, created_dirs):
        if not self.logger:
            return

        dir_count = len(created_dirs)
        dir_text = "directories" if dir_count != 1 else "directory"

        self.logger.info(
            f"    [OK] Successfully decompiled {len(dex_files)} DEX file(s) "
            f"into {dir_count} smali {dir_text}"
        )
