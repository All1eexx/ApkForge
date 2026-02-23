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

import shutil
from pathlib import Path
from typing import List, Optional

from platform_utils import run_command, setup_utf8_environment


class JarBuilder:
    def __init__(self, logger=None):
        self.logger = logger
        setup_utf8_environment()

    @staticmethod
    def find_jar() -> Optional[str]:
        jar_path = shutil.which("jar")
        if not jar_path:
            raise RuntimeError("jar not found. Please install JDK")
        return jar_path

    def create_jar(self, classes_dir: Path, output_jar: Path) -> Path:
        if self.logger:
            self.logger.info("  Creating JAR from compiled classes...")

        jar_path = self.find_jar()

        cmd = [jar_path, "cf", str(output_jar), "-C", str(classes_dir), "."]

        result = run_command(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"JAR creation failed: {result.stderr}")

        if output_jar.exists():
            jar_size = output_jar.stat().st_size / 1024
            if self.logger:
                self.logger.info(f"    JAR created ({jar_size:.2f} KB)")

        return output_jar

    def combine_jars(self, main_jar: Path, library_jars: List[Path], output_jar: Path, work_dir: Path) -> Path:
        if self.logger:
            self.logger.info("  Combining all JAR files into one...")

        combine_dir = work_dir / "temp_combine"
        combine_dir.mkdir(exist_ok=True, parents=True)

        jar_path = self.find_jar()

        self._extract_jars(jar_path, main_jar, library_jars, combine_dir)
        self._create_combined_jar(jar_path, output_jar, combine_dir)

        shutil.rmtree(combine_dir, ignore_errors=True)

        if output_jar.exists():
            combined_size = output_jar.stat().st_size / 1024
            if self.logger:
                self.logger.info(f"    Combined JAR created ({combined_size:.2f} KB)")

        return output_jar

    def _extract_jars(self, jar_path: str, main_jar: Path, library_jars: List[Path], combine_dir: Path):
        if main_jar.exists():
            if self.logger:
                self.logger.info("    Extracting compiled JAR...")
            extract_cmd = [jar_path, "xf", str(main_jar)]
            run_command(extract_cmd, cwd=combine_dir)

        if library_jars:
            if self.logger:
                self.logger.info("    Extracting library JARs...")
            for lib_jar in library_jars:
                if self.logger:
                    self.logger.info(f"      - {lib_jar.name}")
                extract_cmd = [jar_path, "xf", str(lib_jar)]
                run_command(extract_cmd, cwd=combine_dir)

    def _create_combined_jar(self, jar_path: str, output_jar: Path, combine_dir: Path):
        if self.logger:
            self.logger.info("    Creating combined JAR...")

        create_jar_cmd = [jar_path, "cf", str(output_jar), "."]

        result = run_command(create_jar_cmd, cwd=combine_dir)
        if result.returncode != 0:
            raise RuntimeError(f"Combined JAR creation failed: {result.stderr}")