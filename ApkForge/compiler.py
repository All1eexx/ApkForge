# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : compiler.py
# Purpose : Orchestrates compilation of Java/Kotlin sources to smali.
# =============================================================================

import os
import shutil
from pathlib import Path

from dex_converter import DexConverter
from jar_builder import JarBuilder
from java_compiler import JavaCompiler
from kotlin_compiler import KotlinCompiler
from platform_utils import setup_utf8_environment
from smali_decompiler import SmaliDecompiler


class ConfigError(Exception):
    pass


class SourceCompiler:
    def __init__(self, paths: dict, found_files: dict, config=None, logger=None):
        required_keys = ["modded_dir", "android_sdk", "src_dir"]
        missing = [key for key in required_keys if key not in paths]
        if missing:
            raise ConfigError(f"Missing required paths: {missing}")

        self.paths = paths
        self.found_files = found_files
        self.modded_dir = paths["modded_dir"]
        self.config = config
        self.logger = logger

        self.path_separator: str = os.pathsep

        self.java_compiler = JavaCompiler(logger)
        self.kotlin_compiler = KotlinCompiler(logger)
        self.jar_builder = JarBuilder(logger)
        self.dex_converter = DexConverter(paths["android_sdk"], logger)
        self.smali_decompiler = SmaliDecompiler(
            found_files["baksmali_jar"], self.modded_dir, logger
        )

        setup_utf8_environment()

    def compile_and_merge(self):
        if self.logger:
            self.logger.info("\nCompiling and merging source files...")

        temp_dirs = self._create_temp_directories()

        try:
            android_jar = self._find_android_jar()

            java_files = list(self.paths["src_dir"].rglob("*.java"))
            kotlin_files = list(self.paths["src_dir"].rglob("*.kt"))

            if not (java_files or kotlin_files):
                if self.logger:
                    self.logger.info(
                        "  No Java or Kotlin source files found to compile."
                    )
                return None

            self._print_source_files_info(java_files, kotlin_files)
            self._copy_source_files(java_files, kotlin_files, temp_dirs["src"])

            library_jars = self._find_library_jars()
            classpath = self._prepare_classpath(android_jar, library_jars)

            if java_files:
                self.java_compiler.compile(java_files, classpath, temp_dirs["classes"])

            if kotlin_files:
                self.kotlin_compiler.compile(
                    kotlin_files, classpath, temp_dirs["classes"], temp_dirs["classes"]
                )

            if not any(temp_dirs["classes"].iterdir()):
                raise RuntimeError("No compiled classes found. Compilation failed.")

            temp_jar = self.jar_builder.create_jar(
                temp_dirs["classes"], temp_dirs["jar"]
            )
            combined_jar = self.jar_builder.combine_jars(
                temp_jar, library_jars, temp_dirs["combined"], self.modded_dir
            )

            dex_files = self.dex_converter.convert_to_dex(
                combined_jar, android_jar, temp_dirs["dex"]
            )

            target_dex_index = self.config.target_dex_index if self.config else None
            self.smali_decompiler.decompile(dex_files, target_dex_index)

            self._print_summary(
                java_files,
                kotlin_files,
                library_jars,
                temp_jar,
                combined_jar,
                dex_files,
            )

            if self.logger:
                self.logger.info("[OK] SUCCESS: Source files compiled and merged")

            return {
                "temp_classes": temp_dirs["classes"],
                "temp_dex": temp_dirs["dex"],
                "temp_jar": temp_dirs["jar"],
                "temp_combined_jar": temp_dirs["combined"],
                "temp_src": temp_dirs["src"],
            }

        finally:
            self._cleanup_temp_dirs(temp_dirs)

    def _create_temp_directories(self):
        if self.logger:
            self.logger.info("  Creating temporary directories...")

        dirs = {
            "classes": self.modded_dir / "temp_classes",
            "jar": self.modded_dir / "temp.jar",
            "dex": self.modded_dir / "temp_dex",
            "combined": self.modded_dir / "temp_combined.jar",
            "src": self.modded_dir / "temp_src",
        }

        for name, dir_path in dirs.items():
            if name not in ["jar", "combined"]:
                dir_path.mkdir(exist_ok=True, parents=True)
            if self.logger:
                self.logger.info(f"    Created: {dir_path.name}")

        return dirs

    def _find_android_jar(self):
        if self.logger:
            self.logger.info("  Searching for Android SDK...")

        platforms_dir = self._get_platforms_directory()
        android_platform = self._select_android_platform(platforms_dir)
        android_jar = self._validate_android_jar(android_platform)

        if self.logger:
            self.logger.info(f"    Using Android platform: {android_platform.name}")
            self.logger.info(f"    Found at: {android_jar.parent}")

        return android_jar

    def _get_platforms_directory(self) -> Path:
        platforms_dir = self.paths["android_sdk"] / "platforms"

        if platforms_dir.exists():
            return platforms_dir

        if self.logger:
            self.logger.info(
                "    Android SDK not found in project path, searching system..."
            )

        detected = self._find_android_sdk_component("platforms")
        if detected:
            return detected

        raise FileNotFoundError(self._build_sdk_error_message())

    @staticmethod
    def _select_android_platform(platforms_dir: Path) -> Path:
        android_platforms = list(platforms_dir.glob("android-*"))
        if not android_platforms:
            raise FileNotFoundError(f"No Android platforms found in {platforms_dir}")

        def get_version(platform_path):
            try:
                return int(platform_path.name.split("-")[1])
            except (IndexError, ValueError):
                return 0

        android_platforms.sort(key=get_version, reverse=True)
        return android_platforms[0]

    @staticmethod
    def _validate_android_jar(android_platform: Path) -> Path:
        android_jar = android_platform / "android.jar"
        if not android_jar.exists():
            raise FileNotFoundError(f"android.jar not found at {android_jar}")
        return android_jar

    def _find_android_sdk_component(self, component: str):
        sdk_path = self.paths["android_sdk"]

        if sdk_path and sdk_path.exists():
            component_path = sdk_path / component
            if component_path.exists():
                return component_path

        env_paths = [
            os.environ.get("ANDROID_HOME"),
            os.environ.get("ANDROID_SDK_ROOT"),
        ]

        for env_path in env_paths:
            if env_path:
                test_path = Path(env_path) / component
                if test_path.exists():
                    return test_path

        return None

    def _build_sdk_error_message(self):
        error_msg = "Android SDK not found.\n\n"
        error_msg += "Please install Android SDK:\n"
        error_msg += "Current search paths checked:\n"

        checked_paths = [str(self.paths["android_sdk"] / "platforms")]

        for env_var in ["ANDROID_HOME", "ANDROID_SDK_ROOT"]:
            env_val = os.environ.get(env_var)
            if env_val:
                checked_paths.append(f"{env_val}/platforms")

        for checked_path in checked_paths:
            error_msg += f"  - {checked_path}\n"

        return error_msg

    @staticmethod
    def _select_latest_platform(android_platforms):
        def get_version(platform_path):
            try:
                return int(platform_path.name.split("-")[1])
            except (IndexError, ValueError):
                return 0

        android_platforms.sort(key=get_version, reverse=True)
        return android_platforms[0]

    @staticmethod
    def _print_source_files_info(java_files, kotlin_files, logger=None):
        if not logger:
            return

        logger.info("  Found source files:")
        if java_files:
            logger.info(f"    Java: {len(java_files)} files")
        if kotlin_files:
            logger.info(f"    Kotlin: {len(kotlin_files)} files")

    @staticmethod
    def _copy_source_files(java_files, kotlin_files, temp_src_dir):
        for java_file in java_files:
            shutil.copy2(java_file, temp_src_dir)

        for kt_file in kotlin_files:
            shutil.copy2(kt_file, temp_src_dir)

    def _find_library_jars(self):
        libs_dir = self.paths.get("libs_dir")
        if not libs_dir:
            if self.logger:
                self.logger.info(
                    "  No library directory configured (libs_dir not in paths)"
                )
            return []

        if self.logger:
            self.logger.info(f"  Looking for libraries in: {libs_dir}")

        if not libs_dir.exists():
            if self.logger:
                self.logger.info("  No library JARs configured")
            return []

        library_jars = list(libs_dir.rglob("*.jar"))
        self._log_library_jars(library_jars, libs_dir)
        return library_jars

    def _log_library_jars(self, library_jars, libs_dir):
        if not self.logger:
            return
        if not library_jars:
            self.logger.info(f"  No JAR files found in {libs_dir}")
            return
        self.logger.info(
            f"  Found {len(library_jars)} library JAR files in {libs_dir}:"
        )
        for lib_jar in library_jars[:5]:
            self.logger.info(
                f"    - {lib_jar.name} ({lib_jar.stat().st_size / 1024:.1f} KB)"
            )
        if len(library_jars) > 5:
            self.logger.info(f"    ... and {len(library_jars) - 5} more")

    def _prepare_classpath(self, android_jar, library_jars):
        classpath_items = [str(android_jar)]

        if library_jars:
            classpath_items.extend([str(jar) for jar in library_jars])

        if self.logger:
            self.logger.info(
                f"  Compilation classpath prepared ({len(classpath_items)} items)"
            )

        return self.path_separator.join(classpath_items)

    @staticmethod
    def _print_summary(
            java_files,
            kotlin_files,
            library_jars,
            temp_jar,
            combined_jar,
            dex_files,
            logger=None,
    ):
        if not logger:
            return

        logger.info("\n" + "=" * 50)
        logger.info("COMPILATION AND MERGING SUMMARY")
        logger.info("=" * 50)

        if java_files:
            logger.info(f"Java files compiled       : {len(java_files)}")
        if kotlin_files:
            logger.info(f"Kotlin files compiled     : {len(kotlin_files)}")

        logger.info(f"Library JARs merged      : {len(library_jars)}")
        logger.info(f"Total source files       : {len(java_files) + len(kotlin_files)}")

        if temp_jar.exists():
            jar_size = temp_jar.stat().st_size / 1024
            logger.info(f"Your JAR size            : {jar_size:.2f} KB")

        if combined_jar.exists():
            combined_size = combined_jar.stat().st_size / 1024
            logger.info(f"Combined JAR size        : {combined_size:.2f} KB")

        logger.info(f"DEX files created        : {len(dex_files)}")
        logger.info("=" * 50)

        if library_jars:
            SourceCompiler._print_library_details(library_jars, logger)

    @staticmethod
    def _print_library_details(library_jars, logger=None):
        if not logger:
            return

        logger.info("\nMerged Libraries:")
        logger.info("-" * 40)
        total_lib_size = 0

        for lib_jar in library_jars:
            lib_size = lib_jar.stat().st_size / 1024
            total_lib_size += lib_size
            logger.info(f"{lib_jar.name} ({lib_size:.2f} KB)")

        logger.info("-" * 40)
        logger.info(f"Total libraries size: {total_lib_size:.2f} KB")

    @staticmethod
    def _cleanup_temp_dirs(temp_dirs):
        for name, dir_path in temp_dirs.items():
            try:
                if name in ["jar", "combined"]:
                    if dir_path.exists():
                        dir_path.unlink()
                else:
                    if dir_path.exists():
                        shutil.rmtree(dir_path, ignore_errors=True)
            except OSError:
                pass
