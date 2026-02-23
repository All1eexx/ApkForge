# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : apk_analyzer.py
# Purpose : Analyzes decompiled APK structure, detects DEX files, package name,
#           main activity and manifest information.
# =============================================================================

import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from manifest_manager import ManifestManager


class ApkAnalyzer:
    ANDROID_NS = "http://schemas.android.com/apk/res/android"
    SMALI_EXT = "*.smali"
    MANIFEST_FILE = "AndroidManifest.xml"
    BUILD_CONFIG_FILE = "BuildConfig.smali"

    DEX_DIR_PATTERN = r"^smali(_classes\d+)?$"
    SMALI_CLASSES_PATTERN = r"smali_classes(\d+)"

    def __init__(self, modded_dir: Path, config: Optional[dict] = None):
        self.modded_dir = modded_dir
        self.config = config or {}
        self.space_threshold = self.config.get("dex_placement", {}).get(
            "space_threshold", 10000
        )

        self.dex_directories: List[Path] = []
        self.package_name: Optional[str] = None
        self.has_multidex: bool = False
        self.dex_count: int = 0
        self.manifest_info: Dict[str, str] = {}
        self.application_class: Optional[str] = None
        self.main_activity: Optional[str] = None

        self._manifest_manager = ManifestManager(modded_dir / self.MANIFEST_FILE)

    def analyze(self) -> "ApkAnalyzer":
        print("\n  Analyzing APK structure...")
        self._find_dex_directories()
        self._extract_package_name()
        self._analyze_manifest()
        self._find_main_activity()
        self._count_original_dex_files()
        return self

    def _find_dex_directories(self):
        pattern = re.compile(self.DEX_DIR_PATTERN)

        for item in self.modded_dir.iterdir():
            if item.is_dir() and pattern.match(item.name):
                self.dex_directories.append(item)

        self.dex_directories.sort(key=self._get_dex_index)
        self.has_multidex = len(self.dex_directories) > 1
        self.dex_count = len(self.dex_directories)

        print(f"    Found {len(self.dex_directories)} DEX directories:")
        for dex_dir in self.dex_directories:
            files_count = len(list(dex_dir.rglob(self.SMALI_EXT)))
            print(f"      - {dex_dir.name}: {files_count} smali files")

    def _get_dex_index(self, dex_dir: Path) -> int:
        name = dex_dir.name
        if name == "smali":
            return 1
        match = re.search(self.SMALI_CLASSES_PATTERN, name)
        return int(match.group(1)) if match else 999

    def _extract_package_name(self):
        self.package_name = self._manifest_manager.get_package_name()
        if self.package_name:
            print(f"    Detected package: {self.package_name}")
        else:
            print("    Warning: Could not extract package name")

    def _analyze_manifest(self):
        manifest_path = self.modded_dir / self.MANIFEST_FILE
        if not manifest_path.exists():
            return

        try:
            ET.register_namespace("android", self.ANDROID_NS)
            tree = ET.parse(manifest_path)
            root = tree.getroot()

            self._extract_sdk_versions()
            self._extract_application_info(root)

        except Exception as e:
            print(f"    Warning: Could not analyze manifest: {e}")

    def _extract_sdk_versions(self):
        min_sdk_str, target_sdk_str = self._manifest_manager.get_sdk_versions()

        if min_sdk_str:
            self.manifest_info["min_sdk"] = min_sdk_str
        if target_sdk_str:
            self.manifest_info["target_sdk"] = target_sdk_str

        print(f"    minSdk: {min_sdk_str}, targetSdk: {target_sdk_str}")

    def _extract_application_info(self, root):
        application = root.find(".//application")
        if application is not None:
            app_class = application.get(f"{{{self.ANDROID_NS}}}name")
            if app_class:
                self.application_class = app_class
                print(f"    Application class: {app_class}")

            multidex = application.get(f"{{{self.ANDROID_NS}}}multiDexEnabled")
            if multidex:
                print(f"    multiDexEnabled: {multidex}")

    def _find_main_activity(self):
        try:
            self.main_activity = self._manifest_manager.get_main_activity()
            if self.main_activity:
                print(f"    Main activity: {self.main_activity}")
        except Exception as e:
            print(f"    Warning: Could not find main activity: {e}")

    def _count_original_dex_files(self):
        original_dex_dir = self.modded_dir / "original" / "dex"
        if original_dex_dir.exists():
            dex_files = list(original_dex_dir.glob("*.dex"))
            if dex_files:
                print(f"    Original APK had {len(dex_files)} DEX files")

    def suggest_dex_placement(
            self, target_dex_index: Optional[int] = None
    ) -> Tuple[Path, str]:
        if not self.dex_directories:
            return self._create_new_dex_directory("smali")

        if target_dex_index is not None:
            return self._find_or_create_target_dex(target_dex_index)

        return self._find_least_loaded_dex()

    def _create_new_dex_directory(self, dir_name: str) -> Tuple[Path, str]:
        new_dir = self.modded_dir / dir_name
        new_dir.mkdir(exist_ok=True)
        return new_dir, dir_name

    def _find_or_create_target_dex(self, target_dex_index: int) -> Tuple[Path, str]:
        target_name = (
            "smali" if target_dex_index == 1 else f"smali_classes{target_dex_index}"
        )

        for dex_dir in self.dex_directories:
            if dex_dir.name == target_name:
                return dex_dir, dex_dir.name

        return self._create_new_dex_directory(target_name)

    def _has_space_in_dex(self, dex_dir: Path) -> bool:
        file_count = len(list(dex_dir.rglob(self.SMALI_EXT)))
        return file_count < self.space_threshold

    def _find_least_loaded_dex(self) -> Tuple[Path, str]:
        if not self.dex_directories:
            return self._create_new_dex_directory("smali")

        dex_loads = []
        for dex_dir in self.dex_directories:
            file_count = len(list(dex_dir.rglob(self.SMALI_EXT)))
            dex_loads.append((dex_dir, file_count))

        dex_loads.sort(key=lambda x: x[1])

        loads_str = ", ".join([f"{d.name}({c})" for d, c in dex_loads])
        print(f"    DEX loads: {loads_str}")
        best_dir = dex_loads[0][0]
        print(f"    Selected: {best_dir.name}")

        return best_dir, best_dir.name

    def update_manifest_for_multidex(self) -> bool:
        if self.dex_count <= 1:
            return False

        manifest_path = self.modded_dir / self.MANIFEST_FILE
        if not manifest_path.exists():
            return False

        try:
            return self._add_multidex_to_manifest(manifest_path)
        except Exception as e:
            print(f"    Warning: Could not update manifest for multidex: {e}")
            return False

    def _add_multidex_to_manifest(self, manifest_path: Path) -> bool:
        with open(manifest_path, "r", encoding="utf-8") as f:
            content = f.read()

        if (
                'android:multiDexEnabled="true"' in content
                or 'multiDexEnabled="true"' in content
        ):
            return False

        self._check_min_sdk_for_multidex()

        return self._insert_multidex_attribute(content, manifest_path)

    def _check_min_sdk_for_multidex(self):
        min_sdk = self.manifest_info.get("min_sdk", "14")
        try:
            if int(min_sdk) < 21:
                print(
                    f"    Warning: minSdkVersion ({min_sdk}) < 21, multiDexEnabled might not be supported"
                )
                print("    Will still add it, but verify if your app supports multidex")
        except ValueError:
            pass

    @staticmethod
    def _insert_multidex_attribute(content: str, manifest_path: Path) -> bool:
        app_pattern = r"(<application\s+[^>]*?)(/?>)"

        def add_multidex(match):
            attrs = match.group(1)
            closing = match.group(2)

            if "android:" in attrs:
                return f'{attrs} android:multiDexEnabled="true"{closing}'
            else:
                if (
                        'xmlns:android="http://schemas.android.com/apk/res/android"'
                        in content
                ):
                    return f'{attrs} android:multiDexEnabled="true"{closing}'
                else:
                    return f'{attrs} multiDexEnabled="true"{closing}'

        new_content, count = re.subn(app_pattern, add_multidex, content, count=1)

        if count > 0:
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print("    Added multiDexEnabled=true to manifest")
            return True
        else:
            print("    Warning: Could not find application tag in manifest")
            return False

    def find_build_config(self) -> Optional[Path]:
        if not self.package_name:
            return self._find_build_config_recursive()

        return self._find_build_config_in_dexes()

    def _find_build_config_recursive(self) -> Optional[Path]:
        smali_files = list(self.modded_dir.rglob(self.BUILD_CONFIG_FILE))
        if smali_files:
            return smali_files[0]
        return None

    def _find_build_config_in_dexes(self) -> Optional[Path]:
        package_path = self.package_name.replace(".", "/")

        for dex_dir in self.dex_directories:
            expected_path = dex_dir / package_path / self.BUILD_CONFIG_FILE
            if expected_path.exists():
                print(f"    Found BuildConfig.smali in {dex_dir.name}/{package_path}/")
                return expected_path

        return self._find_build_config_recursive()

    def merge_smali_files(
            self, source_dir: Path, target_dex_index: Optional[int] = None
    ) -> int:
        print("\n  Merging smali files...")

        if not source_dir.exists():
            print(f"    Source directory not found: {source_dir}")
            return 0

        smali_files = list(source_dir.rglob(self.SMALI_EXT))
        if not smali_files:
            print("    No smali files to merge")
            return 0

        print(f"    Found {len(smali_files)} smali files to merge")

        target_dir, target_name = self.suggest_dex_placement(target_dex_index)
        print(f"    Target DEX directory: {target_name}")

        return self._copy_smali_files(smali_files, source_dir, target_dir)

    @staticmethod
    def _copy_smali_files(
            smali_files: List[Path], source_dir: Path, target_dir: Path
    ) -> int:
        merged_count = 0
        for smali_file in smali_files:
            try:
                rel_path = smali_file.relative_to(source_dir)
                dest_path = target_dir / rel_path

                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(smali_file, dest_path)
                merged_count += 1

                if merged_count <= 5:
                    print(f"      Added: {rel_path}")

            except Exception as e:
                print(f"      Error copying {smali_file.name}: {e}")

        if merged_count > 5:
            print(f"      ... and {merged_count - 5} more files")

        print(f"    [OK] Merged {merged_count} smali files into {target_dir.name}")
        return merged_count

    def get_dex_info(self) -> Dict[str, any]:
        return {
            "dex_count": self.dex_count,
            "dex_directories": [d.name for d in self.dex_directories],
            "has_multidex": self.has_multidex,
            "package_name": self.package_name,
            "application_class": self.application_class,
            "main_activity": self.main_activity,
            "manifest_info": self.manifest_info,
        }
