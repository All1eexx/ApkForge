# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : library_deployer.py
# Purpose : Finds and deploys built native libraries to the correct ABI
#           directories in the decompiled APK.
# =============================================================================

import logging
import shutil
from pathlib import Path
from typing import List, Optional

from abi_filter import ABIFilter


class LibraryDeployer:
    IGNORE_PATTERNS = ["CMakeFiles", "_deps", "Testing", ".cmake"]
    TARGET_ABI = "arm64-v8a"

    def __init__(self, target_dir: Path, logger: Optional[logging.Logger] = None):
        self.target_dir = target_dir
        self.logger = logger or logging.getLogger(__name__)

    def find_built_libraries(
            self, build_dir: Path, target_name: Optional[str] = None
    ) -> List[Path]:
        self.logger.info("\nSearching for built libraries...")

        if target_name:
            self.logger.info(f"  Looking for: {target_name}")

        lib_files = []

        lib_files.extend(self._search_in_target_dir(target_name))

        if not lib_files:
            lib_files.extend(self._search_in_build_dir(build_dir, target_name))

        self._log_search_results(lib_files, build_dir)

        return lib_files

    def _search_in_target_dir(self, target_name: Optional[str]) -> List[Path]:
        lib_files = []
        target_lib_dir = self.target_dir / "lib" / self.TARGET_ABI

        if not target_lib_dir.exists():
            return lib_files

        self.logger.info(f"  Searching in target directory: {target_lib_dir}")

        for lib_path in target_lib_dir.glob("*.so"):
            if self._should_include_library(lib_path, target_name):
                lib_files.append(lib_path)
                self.logger.info(f"  [OK] Found in target: {lib_path.name}")

        return lib_files

    def _search_in_build_dir(
            self, build_dir: Path, target_name: Optional[str]
    ) -> List[Path]:
        lib_files = []
        self.logger.info(f"  Searching in build directory: {build_dir}")

        for lib_path in build_dir.rglob("*.so"):
            if self._should_ignore(lib_path):
                continue

            if self._should_include_library(lib_path, target_name):
                lib_files.append(lib_path)
                self.logger.info(
                    f"  [OK] Found in build: {lib_path.relative_to(build_dir)}"
                )

        return lib_files

    def _should_include_library(
            self, lib_path: Path, target_name: Optional[str]
    ) -> bool:
        if target_name is None:
            return True
        return self._matches_target(lib_path.name, target_name)

    def _log_search_results(self, lib_files: List[Path], build_dir: Path):
        if lib_files:
            self._print_library_summary(lib_files)
        else:
            self._log_no_libraries_found(build_dir)

    def _log_no_libraries_found(self, build_dir: Path):
        target_lib_dir = self.target_dir / "lib" / self.TARGET_ABI
        self.logger.warning("  [ERROR] No libraries found!")
        self.logger.warning("  Checked:")
        self.logger.warning(f"    - {target_lib_dir}")
        self.logger.warning(f"    - {build_dir}")

    def deploy_libraries(self, lib_files: List[Path]):
        if not lib_files:
            self.logger.warning("No libraries to deploy")
            return

        self.logger.info("\nDeploying libraries...")

        existing_abis = []
        for item in self.target_dir.iterdir():
            if item.is_dir() and item.name in ABIFilter.ALL_ABIS:
                existing_abis.append(item.name)

        if existing_abis:
            self.logger.info(
                f"  Existing ABIs after filtering: {', '.join(existing_abis)}"
            )

        for lib_file in lib_files:
            self._deploy_single_library(lib_file)

    def _deploy_single_library(self, lib_file: Path):
        ext = lib_file.suffix.lower()

        if ext == ".so":
            self._deploy_android_library(lib_file)
        elif ext in (".dll", ".dylib", ".a"):
            self._deploy_generic_library(lib_file)
        else:
            self.logger.warning(f"  Unknown library type: {lib_file.name}")

    def _deploy_android_library(self, lib_file: Path):
        if not self._validate_library_file(lib_file):
            return

        abi = self._detect_abi(lib_file)
        target_dir = self.target_dir / "lib" / abi
        target_dir.mkdir(parents=True, exist_ok=True)

        dest = target_dir / lib_file.name

        if self._is_already_deployed(lib_file, dest, abi):
            return

        self._copy_library_file(lib_file, dest, f"lib/{abi}")

    def _validate_library_file(self, lib_file: Path) -> bool:
        if not lib_file.exists():
            self.logger.error(f"  Library not found: {lib_file.name}")
            return False
        return True

    def _is_already_deployed(self, lib_file: Path, dest: Path, abi: str) -> bool:
        try:
            if lib_file.resolve() == dest.resolve():
                size_kb = lib_file.stat().st_size / 1024
                self.logger.info(
                    f"  [OK] {lib_file.name} already in lib/{abi}/ ({size_kb:.1f} KB)"
                )
                return True
        except (OSError, ValueError) as e:
            self.logger.debug(f"Could not compare paths: {e}")
        return False

    def _deploy_generic_library(self, lib_file: Path):
        target_dir = self.target_dir / "libs"
        target_dir.mkdir(parents=True, exist_ok=True)

        dest = target_dir / lib_file.name
        self._copy_library_file(lib_file, dest, "libs")

    def _copy_library_file(self, src: Path, dest: Path, location: str):
        try:
            if dest.exists():
                dest.unlink()

            shutil.copy2(src, dest)

            if dest.exists():
                size_kb = dest.stat().st_size / 1024
                self.logger.info(f"  [OK] {src.name} → {location}/ ({size_kb:.1f} KB)")
            else:
                self.logger.error(f"  [ERROR] Failed to copy {src.name}")

        except Exception as e:
            self.logger.error(f"  Error deploying {src.name}: {e}")

    def _should_ignore(self, lib_path: Path) -> bool:
        path_str = str(lib_path)

        if any(pattern in path_str for pattern in self.IGNORE_PATTERNS):
            return True

        if "test" in lib_path.name.lower():
            return True

        return False

    @staticmethod
    def _matches_target(lib_name: str, target_name: str) -> bool:
        lib_lower = lib_name.lower()
        target_lower = target_name.lower()

        return (
                target_lower in lib_lower
                or f"lib{target_lower}" in lib_lower
                or lib_lower.startswith(target_lower)
        )

    @staticmethod
    def _detect_abi(lib_path: Path) -> str:
        path_str = str(lib_path).lower()

        abi_map = {
            "arm64-v8a": "arm64-v8a",
            "arm64": "arm64-v8a",
            "aarch64": "arm64-v8a",
            "armeabi-v7a": "armeabi-v7a",
            "armeabi": "armeabi",
            "x86_64": "x86_64",
            "x64": "x86_64",
            "x86": "x86",
        }

        for key, abi in abi_map.items():
            if key in path_str:
                return abi

        return "arm64-v8a"

    def _print_library_summary(self, lib_files: List[Path]):
        total_size = sum(f.stat().st_size for f in lib_files) / 1024

        self.logger.info(f"\n[OK] Found {len(lib_files)} library/libraries:")
        for lib in lib_files:
            size_kb = lib.stat().st_size / 1024
            self.logger.info(f"  - {lib.name} ({size_kb:.1f} KB)")

        self.logger.info(f"Total size: {total_size:.1f} KB")
