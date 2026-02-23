# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : file_cleaner.py
# Purpose : Cleans up temporary files and directories created during build.
# =============================================================================

import shutil
from pathlib import Path
from typing import List


class FileCleaner:
    def __init__(self, logger=None):
        self.logger = logger

    def cleanup_temp_dirs(self, temp_dirs: List[Path], description: str = "temporary"):
        if not temp_dirs:
            return

        if self.logger:
            self.logger.info(f"\n  Cleaning up {description} files...")

        for temp_dir in temp_dirs:
            self._remove_path(temp_dir)

    def cleanup_temp_files(
            self, temp_files: List[Path], description: str = "temporary"
    ):
        if not temp_files:
            return

        if self.logger:
            self.logger.info(f"\n  Cleaning up {description} files...")

        for temp_file in temp_files:
            self._remove_path(temp_file)

    def _remove_path(self, path: Path):
        try:
            if path.is_file() or path.is_symlink():
                path.unlink(missing_ok=True)
                if self.logger:
                    self.logger.debug(f"    Removed file: {path.name}")
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                if self.logger:
                    self.logger.debug(f"    Removed directory: {path.name}")
        except OSError as e:
            if self.logger:
                self.logger.warning(
                    f"    [WARNING] Could not clean up {path.name}: {e}"
                )

    def cleanup_by_pattern(self, directory: Path, pattern: str):
        if not directory.exists():
            return

        for item in directory.glob(pattern):
            self._remove_path(item)
