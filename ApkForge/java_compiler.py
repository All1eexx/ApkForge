# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : java_compiler.py
# Purpose : Compiles Java source files to class files.
# =============================================================================

import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any

from platform_utils import setup_utf8_environment, run_compiler_with_args


class JavaCompiler:
    def __init__(self, logger=None):
        self.logger = logger
        setup_utf8_environment()

    @staticmethod
    def find_javac() -> Optional[str]:
        javac_path = shutil.which("javac")
        if not javac_path:
            raise RuntimeError("javac not found. Please install JDK")
        return javac_path

    def compile(
            self, java_files: List[Path], classpath: str, output_dir: Path
    ) -> Dict[str, Any]:
        if not java_files:
            return {"compiled": 0, "output_dir": output_dir}

        if self.logger:
            self.logger.info("  Compiling Java files...")

        javac_path = self.find_javac()

        args = ["-cp", classpath, "-d", str(output_dir), "-Xlint:unchecked"]
        for java_file in java_files:
            args.append(str(java_file))

        run_compiler_with_args(javac_path, args, len(java_files), "Java", self.logger)

        class_files = list(output_dir.rglob("*.class"))

        if self.logger:
            self.logger.info(f"    Compiled {len(java_files)} Java files successfully")
            self.logger.info(f"    Generated {len(class_files)} class files")

        return {
            "compiled": len(java_files),
            "class_files": len(class_files),
            "output_dir": output_dir,
        }
