# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : resource_manager.py
# Purpose : Manages copying and merging of Android resources.
# =============================================================================

import os
import shutil
import filecmp
from pathlib import Path
from typing import Dict, Tuple, List, Optional


class ResourceManager:
    def __init__(
            self, paths: Dict[str, Path], config: Optional[dict] = None, logger=None
    ):
        self.paths = paths
        self.config = config or {}
        self.logger = logger

        src_structure = self.config.get("source_structure", {})
        self.main_dir = src_structure.get("main", "main")
        self.res_dir = src_structure.get("res", "res")

    def merge_resources(self) -> Tuple[int, int]:
        source_res = self.paths["src_dir"] / self.main_dir / self.res_dir
        target_res = self.paths["modded_dir"] / "res"

        if not source_res.exists() or not source_res.is_dir():
            if self.logger:
                self.logger.info(
                    f"  Source resources directory not found: {source_res}"
                )
            return 0, self._count_files(target_res) if target_res.exists() else 0

        self._log_merge_start(source_res, target_res)

        target_res.mkdir(parents=True, exist_ok=True)

        merged_dirs, merged_files = self._merge_all_items(source_res, target_res)

        total_files = self._count_files(target_res)

        self._log_merge_complete(merged_dirs, merged_files, total_files)

        return merged_dirs, total_files

    def _log_merge_start(self, source_res: Path, target_res: Path) -> None:
        if not self.logger:
            return

        self.logger.info("\n  Merging resources...")
        self.logger.info(f"    Source: {source_res}")
        self.logger.info(f"    Target: {target_res}")

        existing_files = self._count_files(target_res) if target_res.exists() else 0
        self.logger.info(f"    Existing resources: {existing_files} files")

    def _log_merge_complete(
            self, merged_dirs: int, merged_files: int, total_files: int
    ) -> None:
        if not self.logger:
            return

        self.logger.info("\n    [OK] Resources merged successfully:")
        self.logger.info(f"        - {merged_dirs} directories processed")
        self.logger.info(f"        - {merged_files} new/updated files added")
        self.logger.info(f"        - {total_files} total files in target")

    def _merge_all_items(self, source_res: Path, target_res: Path) -> Tuple[int, int]:
        merged_dirs = 0
        merged_files = 0

        for item in source_res.iterdir():
            dest_path = target_res / item.name

            if item.is_dir():
                dir_merged = self._merge_directory(item, dest_path)
                if dir_merged:
                    merged_dirs += 1
            else:
                if self._merge_file(item, dest_path):
                    merged_files += 1

        return merged_dirs, merged_files

    def _merge_directory(self, source_dir: Path, target_dir: Path) -> bool:
        target_dir.mkdir(parents=True, exist_ok=True)

        files_updated = 0

        for item in source_dir.iterdir():
            dest_path = target_dir / item.name

            if item.is_dir():
                self._merge_directory(item, dest_path)
            else:
                if self._merge_file(item, dest_path):
                    files_updated += 1

        if self.logger and files_updated > 0:
            rel_path = source_dir.relative_to(
                self.paths["src_dir"] / self.main_dir / self.res_dir
            )
            self.logger.info(
                f"    Updated directory: {rel_path} ({files_updated} files)"
            )

        return True

    def _merge_file(self, source_file: Path, target_file: Path) -> bool:
        if not target_file.exists():
            shutil.copy2(source_file, target_file)
            if self.logger:
                rel_path = source_file.relative_to(
                    self.paths["src_dir"] / self.main_dir / self.res_dir
                )
                self.logger.info(f"    Added file: {rel_path}")
            return True

        if not filecmp.cmp(source_file, target_file, shallow=False):
            shutil.copy2(source_file, target_file)
            if self.logger:
                rel_path = source_file.relative_to(
                    self.paths["src_dir"] / self.main_dir / self.res_dir
                )
                self.logger.info(f"    Updated file: {rel_path}")
            return True

        return False

    @staticmethod
    def _count_files(directory: Path) -> int:
        if not directory.exists():
            return 0

        total = 0
        for _, _, files in os.walk(directory):
            total += len(files)
        return total

    def list_resource_differences(self) -> Dict[str, List[str]]:
        source_res = self.paths["src_dir"] / self.main_dir / self.res_dir
        target_res = self.paths["modded_dir"] / "res"

        if not source_res.exists():
            return {}

        differences = {"new": [], "updated": [], "missing": []}

        self._find_source_differences(source_res, target_res, differences)

        if target_res.exists():
            self._find_missing_in_target(source_res, target_res, differences)

        return differences

    def _find_source_differences(
            self, source_res: Path, target_res: Path, differences: Dict
    ) -> None:
        for root, _, files in os.walk(source_res):
            for file in files:
                self._check_source_file(root, file, source_res, target_res, differences)

    @staticmethod
    def _check_source_file(
            root: str, file: str, source_res: Path, target_res: Path, differences: Dict
    ) -> None:
        source_file = Path(root) / file
        rel_path = source_file.relative_to(source_res)
        target_file = target_res / rel_path

        if not target_file.exists():
            differences["new"].append(str(rel_path))
        elif not filecmp.cmp(source_file, target_file, shallow=False):
            differences["updated"].append(str(rel_path))

    def _find_missing_in_target(
            self, source_res: Path, target_res: Path, differences: Dict
    ) -> None:
        for root, _, files in os.walk(target_res):
            for file in files:
                self._check_target_file(root, file, source_res, target_res, differences)

    @staticmethod
    def _check_target_file(
            root: str, file: str, source_res: Path, target_res: Path, differences: Dict
    ) -> None:
        target_file = Path(root) / file
        rel_path = target_file.relative_to(target_res)
        source_file = source_res / rel_path

        if not source_file.exists():
            differences["missing"].append(str(rel_path))
