# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : jar_builder.py
# Purpose : Creates and combines JAR files from compiled classes.
# =============================================================================

import os
import shutil
from pathlib import Path
from typing import List, Optional

from platform_utils import (
    find_executable,
    run_command,
    setup_utf8_environment,
    normalize_path,
    to_posix_path,
    get_platform_info,
)


class JarBuilder:
    def __init__(self, logger=None):
        self.logger = logger
        self.platform_info = get_platform_info()
        setup_utf8_environment()

    def find_jar_tool(self, tool: str = "jar") -> Optional[str]:
        jar_path = find_executable(tool)
        if not jar_path:
            raise RuntimeError(f"{tool} not found. Please install JDK")

        if self.logger:
            self.logger.debug(f"Found {tool}: {jar_path}")

        return jar_path

    def create_jar(self, classes_dir: Path, output_jar: Path) -> Path:
        if self.logger:
            self.logger.info("  Creating JAR from compiled classes...")

        classes_dir = normalize_path(classes_dir)
        output_jar = normalize_path(output_jar)

        if not classes_dir.exists():
            raise FileNotFoundError(f"Classes directory not found: {classes_dir}")

        jar_path = self.find_jar_tool()

        cmd = [
            jar_path,
            "cf",
            to_posix_path(output_jar),
            "-C",
            to_posix_path(classes_dir),
            ".",
        ]

        result = run_command(cmd)

        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout
            raise RuntimeError(f"JAR creation failed: {error_msg}")

        if output_jar.exists():
            jar_size = output_jar.stat().st_size / 1024
            if self.logger:
                self.logger.info(f"    JAR created ({jar_size:.2f} KB)")

        return output_jar

    def _extract_jars(
        self, jar_path: str, main_jar: Path, library_jars: List[Path], extract_dir: Path
    ):
        if main_jar.exists():
            if self.logger:
                self.logger.info(f"    Extracting main JAR: {main_jar.name}")
            self._extract_single_jar(jar_path, main_jar, extract_dir)

        if library_jars and self.logger:
            self.logger.info(f"    Extracting {len(library_jars)} library JARs...")

        for lib_jar in library_jars:
            lib_jar = normalize_path(lib_jar)
            if lib_jar.exists():
                if self.logger:
                    self.logger.debug(f"      Extracting: {lib_jar.name}")
                self._extract_single_jar(jar_path, lib_jar, extract_dir)

    def _extract_single_jar(self, jar_path: str, jar_file: Path, extract_dir: Path):
        original_cwd = Path.cwd()
        try:
            os.chdir(extract_dir)
            cmd = [jar_path, "xf", to_posix_path(jar_file)]
            result = run_command(cmd)
            if result.returncode != 0 and self.logger:
                self.logger.warning(f"    Warning: Failed to extract {jar_file.name}")
        finally:
            os.chdir(original_cwd)

    @staticmethod
    def _create_combined_jar_windows(
        jar_path: str, extract_dir: Path, output_jar: Path
    ):
        filelist = extract_dir / "filelist.txt"
        with open(filelist, "w", encoding="utf-8") as f:
            for root, _, files in os.walk("."):
                for file in files:
                    rel_path = Path(root) / file
                    f.write(f"{rel_path}\n")

        cmd = [jar_path, "cf", to_posix_path(output_jar), f"@{filelist}"]
        return run_command(cmd)

    @staticmethod
    def _create_combined_jar_unix(jar_path: str, extract_dir: Path, output_jar: Path):
        _ = extract_dir
        cmd = [jar_path, "cf", to_posix_path(output_jar), "."]
        return run_command(cmd)

    def _create_combined_jar(self, jar_path: str, extract_dir: Path, output_jar: Path):
        original_cwd = Path.cwd()
        try:
            os.chdir(extract_dir)

            if self.platform_info["is_windows"]:
                result = self._create_combined_jar_windows(
                    jar_path, extract_dir, output_jar
                )
            else:
                result = self._create_combined_jar_unix(
                    jar_path, extract_dir, output_jar
                )

            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                raise RuntimeError(f"Combined JAR creation failed: {error_msg}")

        finally:
            os.chdir(original_cwd)

    def combine_jars(
        self, main_jar: Path, library_jars: List[Path], output_jar: Path, work_dir: Path
    ) -> Path:
        if self.logger:
            self.logger.info("  Combining all JAR files into one...")

        main_jar = normalize_path(main_jar)
        output_jar = normalize_path(output_jar)
        work_dir = normalize_path(work_dir)

        extract_dir = work_dir / "jar_combine"
        extract_dir.mkdir(parents=True, exist_ok=True)

        jar_path = self.find_jar_tool()

        try:
            self._extract_jars(jar_path, main_jar, library_jars, extract_dir)

            self._cleanup_meta_inf(extract_dir)

            if self.logger:
                self.logger.info("    Creating combined JAR...")

            self._create_combined_jar(jar_path, extract_dir, output_jar)

            if output_jar.exists():
                combined_size = output_jar.stat().st_size / 1024
                if self.logger:
                    self.logger.info(
                        f"    Combined JAR created ({combined_size:.2f} KB)"
                    )

            return output_jar

        finally:
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)

    def _cleanup_meta_inf(self, extract_dir: Path):
        meta_inf_dirs = list(extract_dir.glob("META-INF"))

        if len(meta_inf_dirs) <= 1:
            return

        for meta_dir in meta_inf_dirs[1:]:
            shutil.rmtree(meta_dir, ignore_errors=True)

        if self.logger:
            self.logger.debug("    Cleaned up duplicate META-INF directories")

    def list_jar_contents(self, jar_file: Path) -> List[str]:
        jar_file = normalize_path(jar_file)

        if not jar_file.exists():
            return []

        jar_path = self.find_jar_tool()

        cmd = [jar_path, "tf", to_posix_path(jar_file)]

        result = run_command(cmd)

        if result.returncode != 0:
            return []

        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
