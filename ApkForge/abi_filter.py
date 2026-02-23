# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : abi_filter.py
# Purpose : Filters ABI (Application Binary Interface) directories in the
#           decompiled APK, keeping only specified architectures and removing
#           others to reduce APK size.
# ============================================================================

import logging
import shutil
from pathlib import Path
from typing import List, Optional


class ABIFilter:
    ALL_ABIS = {
        "armeabi",
        "armeabi-v7a",
        "arm64-v8a",
        "x86",
        "x86_64",
        "mips",
        "mips64",
    }

    def __init__(
            self,
            modded_dir: Path,
            config: Optional[dict] = None,
            logger: Optional[logging.Logger] = None,
    ):
        self.modded_dir = modded_dir
        self.lib_dir = modded_dir / "lib"
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)

        abi_config = self.config.get("abi", {})
        self.keep_abis = set(abi_config.get("keep_only", []))
        self.remove_others = abi_config.get("remove_others", True)
        self.warn_if_missing = abi_config.get("warn_if_missing", True)

    def filter(self) -> List[Path]:
        if not self.lib_dir.exists():
            self.logger.info("  No lib directory found, skipping ABI filter")
            return []

        if not self.keep_abis:
            self.logger.info("  No ABI filter specified, keeping all")
            return []

        self.logger.info("\n  Filtering ABI directories...")
        self.logger.info(f"    Keeping ABIs: {', '.join(self.keep_abis)}")

        all_abi_dirs = self._find_abi_directories()

        if not all_abi_dirs:
            self.logger.info("    No ABI directories found")
            return []

        self.logger.info(f"    Found ABIs: {', '.join(d.name for d in all_abi_dirs)}")
        self._check_missing_abis(all_abi_dirs)

        kept_dirs = []
        removed_dirs = []

        for abi_dir in all_abi_dirs:
            if abi_dir.name in self.keep_abis:
                kept_dirs.append(abi_dir)
                self.logger.info(f"    [OK] Keeping: {abi_dir.name}")
            elif self.remove_others:
                self._remove_abi_directory(abi_dir)
                removed_dirs.append(abi_dir)
            else:
                kept_dirs.append(abi_dir)
                self.logger.info(
                    f"    Keeping (configured to keep all): {abi_dir.name}"
                )

        if removed_dirs:
            self.logger.info(
                f"    [ERROR] Removed: {', '.join(d.name for d in removed_dirs)}"
            )

        return kept_dirs

    def _find_abi_directories(self) -> List[Path]:
        if not self.lib_dir.exists():
            return []

        abi_dirs = []
        for item in self.lib_dir.iterdir():
            if item.is_dir() and item.name in self.ALL_ABIS:
                abi_dirs.append(item)

        return abi_dirs

    def _check_missing_abis(self, existing_dirs: List[Path]):
        if not self.warn_if_missing:
            return

        existing_names = {d.name for d in existing_dirs}
        missing_abis = self.keep_abis - existing_names

        if missing_abis:
            self.logger.warning(
                f"    Warning: Requested ABIs not found: {', '.join(missing_abis)}"
            )

    def _remove_abi_directory(self, abi_dir: Path):
        try:
            file_count = len(list(abi_dir.rglob("*")))
            size = sum(f.stat().st_size for f in abi_dir.rglob("*") if f.is_file())

            shutil.rmtree(abi_dir, ignore_errors=True)

            if not abi_dir.exists():
                self.logger.info(
                    f"    [ERROR] Removed: {abi_dir.name} ({file_count} files, {size / 1024:.1f} KB)"
                )
            else:
                self.logger.error(f"    Failed to remove: {abi_dir.name}")

        except Exception as e:
            self.logger.error(f"    Error removing {abi_dir.name}: {e}")

    def get_library_files(self, abi: str) -> List[Path]:
        abi_dir = self.lib_dir / abi
        if not abi_dir.exists():
            return []
        return list(abi_dir.glob("*.so"))

    def get_all_library_files(self) -> List[Path]:
        lib_files = []
        kept_dirs = self.filter()

        for abi_dir in kept_dirs:
            lib_files.extend(abi_dir.glob("*.so"))

        return lib_files

    def print_summary(self):
        if not self.lib_dir.exists():
            return

        all_dirs = self._find_abi_directories()
        if not all_dirs:
            return

        print("\n  ABI Directories Summary:")
        print("-" * 40)

        for abi_dir in all_dirs:
            so_files = list(abi_dir.glob("*.so"))
            total_size = sum(f.stat().st_size for f in so_files) / 1024

            status = "[OK]" if abi_dir.name in self.keep_abis else "[ERROR]"
            print(
                f"  {status} {abi_dir.name}: {len(so_files)} files, {total_size:.1f} KB"
            )

        print("-" * 40)
