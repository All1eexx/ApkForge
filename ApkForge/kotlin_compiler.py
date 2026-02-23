# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : kotlin_compiler.py
# Purpose : Compiles Kotlin source files to class files.
# =============================================================================

import os
import shutil
from pathlib import Path
from typing import List, Optional

from platform_utils import run_command, setup_utf8_environment, run_compiler_with_args


class KotlinCompiler:
    def __init__(self, logger=None):
        self.logger = logger
        setup_utf8_environment()

    def find_kotlinc(self) -> Optional[str]:
        system = os.name
        names = self._get_kotlinc_names(system)

        for name in names:
            kotlinc_path = shutil.which(name)
            if kotlinc_path:
                return kotlinc_path

        return self._search_kotlinc_in_standard_paths(names)

    @staticmethod
    def _get_kotlinc_names(system):
        if system == "nt":
            return ["kotlinc.bat", "kotlinc.cmd", "kotlinc"]
        else:
            return ["kotlinc", "kotlinc-jvm"]

    def _search_kotlinc_in_standard_paths(self, names):
        standard_paths = self._get_kotlinc_standard_paths()

        for search_path in standard_paths:
            for name in names:
                exe_path = search_path / name
                if exe_path.exists():
                    return str(exe_path)

        return None

    @staticmethod
    def _get_kotlinc_standard_paths():
        system = os.name
        if system == "nt":
            return [
                Path(os.environ.get("ProgramFiles", "")) / "Kotlin" / "bin",
                Path(os.environ.get("LOCALAPPDATA", ""))
                / "Programs"
                / "Kotlin"
                / "bin",
                Path("C:\\Kotlin\\bin"),
            ]
        else:
            return [
                Path("/usr/bin"),
                Path("/usr/local/bin"),
                Path.home() / ".sdkman" / "candidates" / "kotlin" / "current" / "bin",
                Path.home() / ".konan" / "bin",
            ]

    def _print_kotlin_version(self, kotlinc_path):
        if not self.logger:
            return

        try:
            result = run_command([kotlinc_path, "-version"])
            version_info = (
                result.stdout.strip() if result.stdout else result.stderr.strip()
            )
            self.logger.info(f"    Kotlin version: {version_info}")
        except RuntimeError:
            self.logger.info("    Could not determine Kotlin version")

    def compile(
            self,
            kotlin_files: List[Path],
            classpath: str,
            output_dir: Path,
            java_output_dir: Optional[Path] = None,
    ) -> None:
        if not kotlin_files:
            return

        if self.logger:
            self.logger.info("  Compiling Kotlin files...")

        kotlinc_path = self.find_kotlinc()
        if not kotlinc_path:
            raise RuntimeError(
                "Kotlin compiler (kotlinc) not found. Please install Kotlin"
            )

        self._print_kotlin_version(kotlinc_path)

        classpath_items = classpath.split(os.pathsep)
        if java_output_dir and java_output_dir.exists():
            classpath_items.append(str(java_output_dir))

        args = [
            "-cp",
            os.pathsep.join(classpath_items),
            "-d",
            str(output_dir),
            "-jvm-target",
            "1.8",
            "-Xlint:all",
            "-Xlint:unused",
            "-Xlint:deprecation",
            "-Xlint:unchecked",
            "-Xlint:infer",
            "-Xjsr305=strict",
            "-Xjvm-default=all",
            "-progressive",
            "-Xlint",
            "-Xlint:nullability",
            "-Xlint:constant",
            "-Xlint:divergence",
            "-Xlint:scope",
            "-Xopt-in=kotlin.RequiresOptIn",
            "-Xopt-in=kotlin.Experimental",
            "-Xopt-in=kotlin.time.ExperimentalTime",
            "-Xopt-in=kotlin.ExperimentalStdlibApi",
            "-Xopt-in=kotlin.ExperimentalUnsignedTypes",
            "-Xopt-in=kotlin.contracts.ExperimentalContracts",
        ]

        for kt_file in kotlin_files:
            args.append(str(kt_file))

        run_compiler_with_args(
            kotlinc_path, args, len(kotlin_files), "Kotlin", self.logger
        )

        if self.logger:
            self.logger.info(
                f"    [OK] Successfully compiled {len(kotlin_files)} Kotlin files"
            )
