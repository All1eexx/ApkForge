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


from pathlib import Path
from typing import List, Optional, Dict, Any

from platform_utils import (
    find_executable,
    setup_utf8_environment,
    run_compiler_with_args,
    normalize_path,
    to_posix_path,
    get_platform_info,
    create_arg_file,
    cleanup_arg_file,
)


class JavaCompiler:
    def __init__(self, logger=None):
        self.logger = logger
        self.platform_info = get_platform_info()
        setup_utf8_environment()

    @staticmethod
    def find_javac() -> Optional[str]:
        javac_path = find_executable("javac")
        if not javac_path:
            raise RuntimeError(
                "javac not found. Please install JDK.\n"
                "  • Windows: https://adoptium.net/\n"
                "  • macOS: brew install openjdk\n"
                "  • Linux: sudo apt-get install openjdk-17-jdk"
            )
        return javac_path

    @staticmethod
    def get_boot_classpath(android_jar: Path) -> str:
        android_jar = normalize_path(android_jar)

        if not android_jar.exists():
            raise FileNotFoundError(f"android.jar not found: {android_jar}")

        return to_posix_path(android_jar)

    def compile(
            self,
            java_files: List[Path],
            classpath: str,
            output_dir: Path,
            android_jar: Optional[Path] = None,
            source_version: str = "1.8",
            target_version: str = "1.8",
    ) -> Dict[str, Any]:
        if not java_files:
            return {"compiled": 0, "output_dir": output_dir}

        if self.logger:
            self.logger.info(f"  Compiling {len(java_files)} Java files...")

        output_dir = normalize_path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        javac_path = self.find_javac()

        args = ["-cp", classpath, "-d", to_posix_path(output_dir)]

        if android_jar:
            bootcp = self.get_boot_classpath(android_jar)
            args.extend(["-bootclasspath", bootcp])

        args.extend(
            [
                "-encoding",
                "UTF-8",
                "-Xlint:unchecked",
                "-Xlint:deprecation",
                "-source",
                source_version,
                "-target",
                target_version,
            ]
        )

        for java_file in java_files:
            args.append(to_posix_path(normalize_path(java_file)))

        if self.platform_info["is_windows"] and len(args) > 100:
            self._compile_with_argfile(javac_path, args, len(java_files))
        else:
            run_compiler_with_args(
                javac_path, args, len(java_files), "Java", self.logger
            )

        class_files = list(output_dir.rglob("*.class"))

        if self.logger:
            self.logger.info(f"    Compiled {len(java_files)} Java files successfully")
            self.logger.info(f"    Generated {len(class_files)} class files")

        return {
            "compiled": len(java_files),
            "class_files": len(class_files),
            "output_dir": output_dir,
        }

    def _compile_with_argfile(self, javac_path: str, args: List[str], file_count: int):
        if self.logger:
            self.logger.info("    Using argument file for long command line...")

        argfile = create_arg_file(args, prefix="javac_args")

        try:
            run_compiler_with_args(
                javac_path, [f"@{argfile}"], file_count, "Java", self.logger
            )
        finally:
            cleanup_arg_file(argfile)

    def compile_directory(
            self,
            source_dir: Path,
            classpath: str,
            output_dir: Path,
            android_jar: Optional[Path] = None,
    ) -> Dict[str, Any]:
        source_dir = normalize_path(source_dir)

        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

        java_files = list(source_dir.rglob("*.java"))

        if not java_files:
            return {"compiled": 0, "output_dir": output_dir}

        return self.compile(java_files, classpath, output_dir, android_jar)

    def get_classpath_separator(self) -> str:
        return ";" if self.platform_info["is_windows"] else ":"
