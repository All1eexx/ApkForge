# =============================================================================
# Android APK Build Tool
# =============================================================================
# Repository : https://github.com/All1eexx/Unity-Online-LAUNCHER
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : main.py
# Purpose : Main entry point for the APK build tool. Orchestrates the entire
#           build process from decompilation to signing.
# =============================================================================

import logging
import os
import platform
import shutil
import time
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from abi_filter import ABIFilter
from apk_analyzer import ApkAnalyzer
from apk_builder import ApkBuilder
from apk_signer import ApkSigner
from config import KeystoreConfig
from cpp_builder import NativeBuilder
from decompiler import Decompiler
from dex_converter import DexConverter
from file_cleaner import FileCleaner
from file_finder import FileFinder
from jar_builder import JarBuilder
from java_compiler import JavaCompiler
from kotlin_compiler import KotlinCompiler
from manifest_manager import ManifestManager
from manifest_updater import ManifestUpdater
from pipeline_manager import PipelineManager
from project_config import init_project_config
from resource_manager import ResourceManager
from smali_decompiler import SmaliDecompiler
from smali_updater import SmaliUpdater
from strings_updater import StringsUpdater
from yaml_updater import YamlUpdater


class ApkForge:
    ANDROID_NS = "http://schemas.android.com/apk/res/android"
    MANIFEST_FILE = "AndroidManifest.xml"

    UNSIGNED_APK = "unsigned.apk"
    ALIGNED_APK = "aligned.apk"

    def __init__(self):
        self._warnings_occurred = False
        self.unsigned_apk_path = None
        self.aligned_apk_path = None
        self.signed_apk_path = None
        self.start_time = time.perf_counter()
        self.start_datetime = datetime.now()

        from path_manager import PathManager

        self.path_manager = PathManager()
        self.paths = self.path_manager.get_paths()

        self.platform_info = (
            f"{platform.system()} {platform.release()} ({platform.machine()})"
        )
        self.changed_values = []
        self.build_summary = {}
        self.signed_apk = None
        self.apk_analyzer = None
        self.config = None
        self._setup_output()

    def has_warnings(self):
        return self._warnings_occurred

    def _log_warning(self, message):
        print(f"\n[WARNING] {message}")
        self._warnings_occurred = True

    @staticmethod
    def _setup_output():
        try:
            if os.name == "nt":
                import sys

                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    def _print_platform_info(self):
        print(f"\nPlatform: {self.platform_info}")
        print(f"Python: {platform.python_version()}")
        print(f"Working directory: {Path.cwd()}")

        android_sdk = self.paths["android_sdk"]
        print(f"Android SDK path: {android_sdk}")

        if android_sdk.exists():
            self._print_sdk_components(android_sdk)
        else:
            print("Android SDK exists: [ERROR]")
            print("Will search in system paths...")

    @staticmethod
    def _print_sdk_components(android_sdk):
        print("Android SDK exists: [OK]")

        components = {
            "platforms": android_sdk / "platforms",
            "build-tools": android_sdk / "build-tools",
            "platform-tools": android_sdk / "platform-tools",
        }

        for name, component_path in components.items():
            if component_path.exists():
                if name == "platforms":
                    ApkForge._print_platform_versions(component_path)
                else:
                    print(f"  {name}: [OK]")
            else:
                print(f"  {name}: [ERROR] (not found)")

    @staticmethod
    def _print_platform_versions(platforms_path):
        versions = list(platforms_path.glob("android-*"))
        if versions:
            version_names = [v.name for v in versions[:3]]
            print(f"  platforms: {', '.join(version_names)}")
        else:
            print("  platforms: directory exists but no platforms found")

    def run(self):
        try:
            self._print_header()

            self._load_project_config()

            pipeline_steps = self.config.raw_config.get("pipeline", [])

            if pipeline_steps:
                pipeline = PipelineManager(self)

                if self.config.raw_config.get("debug_pipeline", False):
                    print("\nAvailable pipeline steps:")
                    for step in pipeline.list_available_steps():
                        print(f"  • {step}")

                success = pipeline.run(pipeline_steps)

                if self.config.raw_config.get("save_pipeline_report", False):
                    report_path = self.paths["project_root"] / "pipeline_report.json"
                    pipeline.save_report(report_path)

                if not success:
                    import sys

                    print("\n[WARNING] Pipeline completed with errors")
                    sys.exit(1)

            else:
                print("\n[WARNING] No pipeline defined in build_config.json")
                print("    Add 'pipeline' section with list of methods to execute:")
                print("""
    "pipeline": [
        "_load_keystore_config",
        "_find_files",
        "_decompile_apk",
        "_build_apk",
        "_sign_apk",
        "_print_final_summary"
    ]
                """)

        except Exception as e:
            print(f"\n[ERROR] Build failed: {e}")
            import traceback

            traceback.print_exc()
            import sys

            sys.exit(1)

    @staticmethod
    def _print_header():
        print("=" * 60)
        print(f"   BUILD TOOL STARTED: {time.ctime(time.time())}")
        print("=" * 60)

    def _load_project_config(self):
        print("\nLoading project configuration...")
        self.config = init_project_config(self.paths["project_root"])
        self.config.update_from_env()

    def _load_keystore_config(self):
        print("\nLoading keystore configuration...")
        print(f"  Project root: {self.paths['project_root']}")

        keystore_config_path = self.config.get_keystore_config_path(
            self.paths["project_root"]
        )
        print(f"  Keystore config: {keystore_config_path}")

        config = KeystoreConfig(keystore_config_path, self.paths["project_root"])
        config.load()
        config.validate()

        print(f"[OK] Keystore: {config.path.name}")
        print(f"[OK] Keystore alias: {config.alias}")
        print("[OK] Keystore config loaded and validated")
        self.keystore_config = config

    def _find_files(self):
        print("\nFinding required files...")
        finder = FileFinder(self.paths)
        self.found_files = finder.find_all()

        print(f"  Apktool: {self.found_files['apktool_jar']}")
        print(f"  Baksmali: {self.found_files['baksmali_jar']}")
        print(f"  Smali: {self.found_files['smali_jar']}")
        print(f"  Source APK: {self.found_files['source_apk']}")
        print("[OK] All required files found")

    def _copy_resources(self):
        print("\n" + "=" * 50)
        print("Merging Resources")
        print("=" * 50)

        resource_manager = ResourceManager(
            self.paths, config=self.config.raw_config if self.config else None
        )

        differences = resource_manager.list_resource_differences()
        if any(differences.values()):
            print("\n  Resource changes detected:")
            if differences["new"]:
                print(f"    New files: {len(differences['new'])}")
            if differences["updated"]:
                print(f"    Updated files: {len(differences['updated'])}")
            if differences["missing"]:
                print(f"    Files only in target: {len(differences['missing'])}")

        dirs, total_files = resource_manager.merge_resources()

        if dirs > 0 or total_files > 0:
            self.changed_values.append(
                {
                    "Name": "Resources",
                    "Old": "Original resources",
                    "New": f"Merged with custom resources ({total_files} total files)",
                }
            )

    def _prepare_decompile_directory(self):
        print("\nPreparing decompile directory...")
        if self.paths["modded_dir"].exists():
            print(f"  Removing existing directory: {self.paths['modded_dir']}")
            shutil.rmtree(self.paths["modded_dir"], ignore_errors=True)
        print(f"  [OK] Directory ready: {self.paths['modded_dir']}")

    def _run_apktool_decompile(self):
        print("\nRunning apktool decompile...")
        print(f"  Source: {self.found_files['source_apk']}")
        print(f"  Output: {self.paths['modded_dir']}")

        decompiler = Decompiler(
            self.found_files["apktool_jar"],
            self.found_files["source_apk"],
            self.paths["modded_dir"],
        )
        decompiler.decompile()
        print("  [OK] Apktool decompile completed")

    def _count_decompiled_files(self):
        file_count = sum(
            len(files) for _, _, files in os.walk(self.paths["modded_dir"])
        )
        print(f"  [OK] Extracted {file_count} files")
        self.build_summary["decompiled_files"] = file_count
        return file_count

    def _verify_decompile_success(self):
        required_dirs = ["res", "smali"]
        missing = []

        for dir_name in required_dirs:
            if not (self.paths["modded_dir"] / dir_name).exists():
                missing.append(dir_name)

        if missing:
            raise RuntimeError(f"Decompile failed: missing directories {missing}")

        print("  [OK] Decompile verification passed")
        return True

    def _analyze_apk_structure(self):
        print("\nAnalyzing APK structure...")
        self.apk_analyzer = ApkAnalyzer(
            self.paths["modded_dir"],
            config=self.config.raw_config if self.config else None,
        )
        self.apk_analyzer.analyze()

        if self.config.auto_multidex and self.apk_analyzer.has_multidex:
            print("\n  Checking multidex configuration...")
            updated = self.apk_analyzer.update_manifest_for_multidex()
            if updated:
                print("  [OK] Added multiDexEnabled=true to manifest")
                self.changed_values.append(
                    {
                        "Name": "AndroidManifest.xml multiDexEnabled",
                        "Old": "false/not set",
                        "New": "true",
                    }
                )

        dex_info = self.apk_analyzer.get_dex_info()
        self.build_summary["dex_count"] = dex_info["dex_count"]
        self.build_summary["dex_directories"] = dex_info["dex_directories"]
        self.build_summary["package_name"] = dex_info["package_name"]

    def _filter_abis(self):
        if not hasattr(self.config, "abi_keep_only") or not self.config.abi_keep_only:
            return

        print("\n" + "=" * 50)
        print("Filtering ABI Directories")
        print("=" * 50)

        abi_config = {
            "keep_only": self.config.abi_keep_only,
            "remove_others": self.config.abi_remove_others,
            "warn_if_missing": self.config.abi_warn_if_missing,
        }

        abi_filter = ABIFilter(
            self.paths["modded_dir"],
            config={"abi": abi_config},
            logger=logging.getLogger(__name__),
        )

        kept_dirs = abi_filter.filter()

        if kept_dirs:
            print(
                f"\n  [OK] ABI filtering complete. Kept: {', '.join(d.name for d in kept_dirs)}"
            )
            self.changed_values.append(
                {
                    "Name": "ABI Directories",
                    "Old": "All",
                    "New": f"Kept: {', '.join(d.name for d in kept_dirs)}",
                }
            )

    def _update_apktool_yml(self):
        print("\nUpdating apktool.yml...")
        yml_path = self.paths["modded_dir"] / "apktool.yml"
        print(f"  Path: {yml_path}")

        updater = YamlUpdater(yml_path)
        updater.load()

        old_values = updater.extract_values()
        self._store_old_apk_values(old_values)
        self._print_old_apk_values(old_values)

        new_apk_name, updated = updater.update(
            self.config.version_code, self.config.version_name, self.config.app_name
        )

        if updated:
            self._record_apktool_changes(new_apk_name)
        else:
            print("[INFO]: No changes needed in apktool.yml")

    def _store_old_apk_values(self, old_values):
        self.build_summary["old_version_code"] = old_values.get("version_code")
        self.build_summary["old_version_name"] = old_values.get("version_name")
        self.build_summary["old_apk_file_name"] = old_values.get("apk_file_name")

    @staticmethod
    def _print_old_apk_values(old_values):
        print(f"  Old versionCode: {old_values.get('version_code')}")
        print(f"  Old versionName: {old_values.get('version_name')}")
        print(f"  Old apkFileName: {old_values.get('apk_file_name')}")

    def _record_apktool_changes(self, new_apk_name):
        print(f"  New versionCode: {self.config.version_code}")
        print(f"  New versionName: {self.config.version_name}")
        print(f"  New apkFileName: {new_apk_name}")
        print("[OK] apktool.yml updated")

        self.changed_values.extend(
            [
                {
                    "Name": "apktool.yml versionCode",
                    "Old": self.build_summary["old_version_code"],
                    "New": str(self.config.version_code),
                },
                {
                    "Name": "apktool.yml versionName",
                    "Old": self.build_summary["old_version_name"],
                    "New": self.config.version_name,
                },
                {
                    "Name": "apktool.yml apkFileName",
                    "Old": self.build_summary["old_apk_file_name"],
                    "New": new_apk_name,
                },
            ]
        )

    def _update_build_config(self):
        print("\nUpdating BuildConfig.smali...")

        smali_path = self._find_build_config_smali()
        if not smali_path:
            print("   [WARNING]: BuildConfig.smali not found, skipping")
            return

        print(f"  Path: {smali_path.relative_to(self.paths['modded_dir'])}")

        updater = SmaliUpdater(smali_path)
        updater.load()
        old_values = updater.get_old_values()

        self._print_old_build_config(old_values)

        changes = updater.update_build_config(
            self.config.version_code,
            self.config.version_name,
            self.config.application_id,
            self.config.build_type,
        )

        if changes:
            self._record_build_config_changes(changes, old_values)
        else:
            print("   [INFO]: No changes made to BuildConfig.smali")

    def _find_build_config_smali(self):
        if self.apk_analyzer:
            return self.apk_analyzer.find_build_config()

        smali_files = list(self.paths["modded_dir"].rglob("BuildConfig.smali"))
        if smali_files:
            return smali_files[0]

        return None

    def _print_old_build_config(self, old_values):
        print(f"  Old VERSION_CODE: {old_values.get('VERSION_CODE', 'Not found')}")
        print(f"  Old VERSION_NAME: {old_values.get('VERSION_NAME', 'Not found')}")
        print(f"  Old APPLICATION_ID: {old_values.get('APPLICATION_ID', 'Not found')}")

        if "VERSION_CODE" in old_values and old_values["VERSION_CODE"].startswith("0x"):
            try:
                old_dec = int(old_values["VERSION_CODE"], 16)
                print(f"  Old VERSION_CODE (dec): {old_dec}")
            except ValueError:
                pass

        print(f"  New VERSION_CODE (hex): 0x{self.config.version_code:x}")
        print(f"  New VERSION_CODE (dec): {self.config.version_code}")

    def _record_build_config_changes(self, changes, old_values):
        print(f"[OK] BuildConfig.smali updated ({len(changes)} changes)")

        for field, value in changes:
            print(f"  {field}: {value}")
            old_value = old_values.get(field, "?")

            if field == "VERSION_CODE":
                self._record_version_code_change(old_value)
            elif field == "VERSION_NAME":
                self._record_simple_change(
                    "BuildConfig.smali VERSION_NAME", old_value, value
                )
            elif field == "APPLICATION_ID":
                self._record_simple_change(
                    "BuildConfig.smali APPLICATION_ID", old_value, value
                )
            elif field == "BUILD_TYPE":
                self._record_simple_change(
                    "BuildConfig.smali BUILD_TYPE", old_value, value
                )

    def _record_version_code_change(self, old_value):
        try:
            if old_value.startswith("0x"):
                old_dec = int(old_value, 16)
                old_display = f"{old_dec} (0x{old_dec:x})"
            else:
                old_display = old_value
        except (ValueError, AttributeError):
            old_display = old_value

        self.changed_values.append(
            {
                "Name": "BuildConfig.smali VERSION_CODE",
                "Old": old_display,
                "New": f"{self.config.version_code} (0x{self.config.version_code:x})",
            }
        )

    def _record_simple_change(self, name, old_value, new_value):
        self.changed_values.append({"Name": name, "Old": old_value, "New": new_value})

    def _update_strings(self):
        print("\nUpdating strings.xml...")

        strings_files = list((self.paths["modded_dir"] / "res").rglob("strings.xml"))
        if not strings_files:
            print("   [WARNING]: strings.xml not found, skipping")
            return

        strings_path = strings_files[0]
        print(f"  Path: {strings_path.relative_to(self.paths['modded_dir'])}")

        updater = StringsUpdater(strings_path)
        success, message = updater.update_app_name(self.config.app_name)

        if success:
            print(
                f"  [OK] {message}"
                if "already" not in message.lower()
                else f"  [INFO] INFO: {message}"
            )
            old_app_name = updater.get_old_app_name()
            self.changed_values.append(
                {
                    "Name": "strings.xml app_name",
                    "Old": old_app_name if old_app_name else "?",
                    "New": self.config.app_name,
                }
            )
        else:
            print(f"   [WARNING]: {message}")

    def _update_manifest(self):
        print(f"\nUpdating {self.MANIFEST_FILE}...")
        manifest_path = self.paths["modded_dir"] / self.MANIFEST_FILE
        custom_manifest_path = self.paths["src_dir"] / "main" / self.MANIFEST_FILE

        print(f"  Main manifest: {manifest_path}")
        print(f"  Custom manifest: {custom_manifest_path}")

        if not custom_manifest_path.exists():
            print("  [WARNING] : Custom manifest not found, skipping manifest update")
            return

        old_package = ManifestManager(manifest_path).get_package_name() or "Not set"

        updater = ManifestUpdater(manifest_path, custom_manifest_path)
        success = updater.update(self.config.application_id)

        if success:
            print(f"[OK] {self.MANIFEST_FILE} merged successfully")
            self.changed_values.append(
                {
                    "Name": f"{self.MANIFEST_FILE} package",
                    "Old": old_package,
                    "New": self.config.application_id,
                }
            )
        else:
            print(f"[ERROR] Failed to merge {self.MANIFEST_FILE}")

    def _build_native_libs(self):
        print("\n" + "=" * 50)
        print("Building Native C++ Libraries")
        print("=" * 50)

        src_structure = self.config.raw_config.get("paths", {}).get(
            "source_structure", {}
        )
        cmakelists_rel_path = src_structure.get("cmakelists")

        if not cmakelists_rel_path:
            raise KeyError(
                "Missing 'cmakelists' path in build_config.json > paths > source_structure"
            )

        cmake_lists = self.paths["project_root"] / cmakelists_rel_path
        print(f"  Using CMakeLists.txt: {cmake_lists}")

        if not cmake_lists.exists():
            raise FileNotFoundError(f"CMakeLists.txt not found at {cmake_lists}")

        try:
            builder = NativeBuilder(
                self.paths,
                config=self.config.raw_config if self.config else None,
                cmakelists_path=cmake_lists,
            )
            builder.build()

            if builder.build_success:
                self.changed_values.append(
                    {
                        "Name": "Native Libraries",
                        "Old": "Not built",
                        "New": "Built and integrated",
                    }
                )
            else:
                raise RuntimeError("Native build failed - no libraries produced")

        except (FileNotFoundError, RuntimeError) as e:
            pipeline_config = self.config.raw_config.get("pipeline_behavior", {})
            if pipeline_config.get("stop_on_error", True):
                raise
            else:
                self._log_warning(f"Native build failed (ignored): {e}")
                self.build_summary["native_build"] = f"Failed: {str(e)[:100]}"

    def _prepare_compilation_directories(self):
        print("\nPreparing compilation directories...")

        self.temp_dirs = {
            "classes": self.paths["modded_dir"] / "temp_classes",
            "jar": self.paths["modded_dir"] / "temp.jar",
            "dex": self.paths["modded_dir"] / "temp_dex",
            "combined": self.paths["modded_dir"] / "temp_combined.jar",
            "src": self.paths["modded_dir"] / "temp_src",
        }

        for name, dir_path in self.temp_dirs.items():
            if name not in ["jar", "combined"]:
                dir_path.mkdir(exist_ok=True, parents=True)
                print(f"  [OK] Created: {dir_path.name}")

        return self.temp_dirs

    def _find_android_jar(self):
        print("\nLocating Android framework...")

        platforms_dir = self.paths["android_sdk"] / "platforms"
        if not platforms_dir.exists():
            raise FileNotFoundError(f"Platforms directory not found: {platforms_dir}")

        android_platforms = list(platforms_dir.glob("android-*"))
        if not android_platforms:
            raise FileNotFoundError(f"No Android platforms found in {platforms_dir}")

        def get_version(p):
            try:
                return int(p.name.split("-")[1])
            except (IndexError, ValueError):
                return 0

        latest = max(android_platforms, key=get_version)
        self.android_jar = latest / "android.jar"

        if not self.android_jar.exists():
            raise FileNotFoundError(f"android.jar not found at {self.android_jar}")

        print(f"  [OK] Using Android API {latest.name}")
        print(f"  [OK] android.jar: {self.android_jar}")

        return self.android_jar

    def _find_source_files(self):
        print("\nScanning source files...")

        self.java_files = []
        self.kotlin_files = []

        src_structure = self.config.raw_config.get("paths", {}).get(
            "source_structure", {}
        )

        java_paths = src_structure.get("java", [])
        if isinstance(java_paths, str):
            java_paths = [java_paths]

        for java_path in java_paths:
            full_path = self.paths["project_root"] / java_path
            if full_path.exists():
                found_files = list(full_path.rglob("*.java"))
                self.java_files.extend(found_files)
                print(f"  Found {len(found_files)} Java files in {java_path}")
            else:
                print(f"  Warning: Java path not found: {java_path}")

        kotlin_paths = src_structure.get("kotlin", [])
        if isinstance(kotlin_paths, str):
            kotlin_paths = [kotlin_paths]

        for kotlin_path in kotlin_paths:
            full_path = self.paths["project_root"] / kotlin_path
            if full_path.exists():
                found_files = list(full_path.rglob("*.kt"))
                self.kotlin_files.extend(found_files)
                print(f"  Found {len(found_files)} Kotlin files in {kotlin_path}")
            else:
                print(f"  Warning: Kotlin path not found: {kotlin_path}")

        self._print_file_list("Java", self.java_files)
        self._print_file_list("Kotlin", self.kotlin_files)

        if not (self.java_files or self.kotlin_files):
            print("  [INFO] No source files found")

        return self.java_files, self.kotlin_files

    def _print_file_list(self, language, files):
        if files:
            print(f"  [OK] Found {len(files)} {language} files")
            for f in files[:3]:
                print(f"    - {f.relative_to(self.paths['src_dir'])}")
            if len(files) > 3:
                print(f"    ... and {len(files) - 3} more")

    def _copy_source_to_temp(self):
        if not hasattr(self, "java_files") or not hasattr(self, "kotlin_files"):
            print("  [INFO] No source files found to copy")
            return

        print("\nCopying source files to temp directory...")

        for java_file in self.java_files:
            shutil.copy2(java_file, self.temp_dirs["src"])

        for kt_file in self.kotlin_files:
            shutil.copy2(kt_file, self.temp_dirs["src"])

        print(f"  [OK] Copied {len(self.java_files) + len(self.kotlin_files)} files")

    def _find_library_jars(self):
        libs_dir = self.paths.get("libs_dir")
        if not libs_dir or not libs_dir.exists():
            print("\n[INFO] No library JARs found")
            self.library_jars = []
            return []

        print("\nScanning library JARs...")
        self.library_jars = list(libs_dir.rglob("*.jar"))

        if self.library_jars:
            print(f"  [OK] Found {len(self.library_jars)} JAR files")
            total_size = sum(f.stat().st_size for f in self.library_jars) / (
                1024 * 1024
            )
            print(f"  [OK] Total size: {total_size:.2f} MB")

            jars_with_size = [(f, f.stat().st_size) for f in self.library_jars]
            jars_with_size.sort(key=lambda x: x[1], reverse=True)
            for jar, size in jars_with_size[:3]:
                print(f"    - {jar.name} ({size / 1024:.1f} KB)")
            if len(jars_with_size) > 3:
                print(f"    ... and {len(jars_with_size) - 3} more")

        return self.library_jars

    def _prepare_classpath(self):
        if not hasattr(self, "android_jar"):
            raise RuntimeError("android_jar not found. Run _find_android_jar first")

        if not hasattr(self, "library_jars"):
            self.library_jars = []

        classpath_items = [str(self.android_jar)]

        if self.library_jars:
            classpath_items.extend([str(jar) for jar in self.library_jars])

        self.classpath = os.pathsep.join(classpath_items)
        print(f"\nClasspath prepared with {len(classpath_items)} items")

        return self.classpath

    def _compile_java_files(self):
        if not hasattr(self, "java_files") or not self.java_files:
            print("  [INFO] No Java files to compile")
            return None

        if not hasattr(self, "classpath"):
            raise RuntimeError("Classpath not prepared. Run _prepare_classpath first")

        print(f"\nCompiling {len(self.java_files)} Java files...")

        compiler = JavaCompiler()
        result = compiler.compile(
            self.java_files, self.classpath, self.temp_dirs["classes"]
        )

        print(f"  [OK] Generated {result['class_files']} class files")

        return result

    def _compile_kotlin_files(self):
        if not hasattr(self, "kotlin_files") or not self.kotlin_files:
            print("  [INFO] No Kotlin files to compile")
            return

        if not hasattr(self, "classpath"):
            raise RuntimeError("Classpath not prepared. Run _prepare_classpath first")

        print(f"\nCompiling {len(self.kotlin_files)} Kotlin files...")

        compiler = KotlinCompiler()
        compiler.compile(
            self.kotlin_files,
            self.classpath,
            self.temp_dirs["classes"],
            self.temp_dirs["classes"],
        )

        class_files = list(self.temp_dirs["classes"].rglob("*.class"))
        print(f"  [OK] Generated {len(class_files)} class files")

    def _verify_compilation(self):
        if not hasattr(self, "temp_dirs"):
            raise RuntimeError(
                "Temp directories not created. Run _prepare_compilation_directories first"
            )

        class_files = list(self.temp_dirs["classes"].rglob("*.class"))

        if not class_files:
            raise RuntimeError("No compiled classes found. Compilation failed.")

        print("\nCompilation verification:")
        print(f"  [OK] {len(class_files)} class files generated")

        packages = set()
        for cf in class_files:
            rel_path = cf.relative_to(self.temp_dirs["classes"])
            if rel_path.parent.name != ".":
                packages.add(str(rel_path.parent))

        if packages:
            print(f"  [OK] Packages: {len(packages)}")
            for p in sorted(packages)[:5]:
                print(f"    - {p}")
            if len(packages) > 5:
                print(f"    ... and {len(packages) - 5} more")

    def _create_jar_from_classes(self):
        if not hasattr(self, "temp_dirs"):
            raise RuntimeError(
                "Temp directories not created. Run _prepare_compilation_directories first"
            )

        print("\nCreating JAR archive...")

        builder = JarBuilder()
        jar_path = builder.create_jar(self.temp_dirs["classes"], self.temp_dirs["jar"])

        size_kb = jar_path.stat().st_size / 1024
        print(f"  [OK] JAR created: {jar_path.name} ({size_kb:.2f} KB)")

        self.temp_jar = jar_path
        return jar_path

    def _combine_jars(self):
        if not hasattr(self, "temp_jar"):
            raise RuntimeError(
                "Main JAR not created. Run _create_jar_from_classes first"
            )

        if not hasattr(self, "library_jars"):
            self.library_jars = []

        if not self.library_jars:
            print("\nNo library JARs to combine")
            self.combined_jar = self.temp_jar
            return self.temp_jar

        print(f"\nCombining {len(self.library_jars)} library JARs...")

        builder = JarBuilder()
        combined = builder.combine_jars(
            self.temp_jar,
            self.library_jars,
            self.temp_dirs["combined"],
            self.paths["modded_dir"],
        )

        size_kb = combined.stat().st_size / 1024
        print(f"  [OK] Combined JAR: {combined.name} ({size_kb:.2f} KB)")

        self.combined_jar = combined
        return combined

    def _convert_jar_to_dex(self):
        if not hasattr(self, "combined_jar"):
            raise RuntimeError("Combined JAR not created. Run _combine_jars first")

        if not hasattr(self, "android_jar"):
            raise RuntimeError("android_jar not found. Run _find_android_jar first")

        print("\nConverting JAR to DEX...")

        converter = DexConverter(self.paths["android_sdk"])
        self.dex_files = converter.convert_to_dex(
            self.combined_jar, self.android_jar, self.temp_dirs["dex"]
        )

        total_size = sum(f.stat().st_size for f in self.dex_files) / 1024
        print(f"  [OK] Generated {len(self.dex_files)} DEX files ({total_size:.2f} KB)")

        for dex in self.dex_files:
            size = dex.stat().st_size / 1024
            print(f"    - {dex.name} ({size:.2f} KB)")

        return self.dex_files

    def _decompile_dex_to_smali(self):
        if not hasattr(self, "dex_files"):
            raise RuntimeError("DEX files not created. Run _convert_jar_to_dex first")

        print("\nDecompiling DEX to smali...")

        decompiler = SmaliDecompiler(
            self.found_files["baksmali_jar"], self.paths["modded_dir"]
        )

        target_dex_index = self.config.target_dex_index if self.config else None
        created_dirs = decompiler.decompile(self.dex_files, target_dex_index)

        smali_count = 0
        for dir_name in created_dirs:
            smali_dir = self.paths["modded_dir"] / dir_name
            smali_count += len(list(smali_dir.rglob("*.smali")))

        print(f"  [OK] Created {smali_count} smali files in {', '.join(created_dirs)}")

        return created_dirs

    def _cleanup_temp_dirs(self):
        print("\nCleaning up compilation temporary files...")

        temp_dirs = [
            self.paths["modded_dir"] / "temp_classes",
            self.paths["modded_dir"] / "temp_dex",
            self.paths["modded_dir"] / "temp_src",
        ]

        temp_files = [
            self.paths["modded_dir"] / "temp.jar",
            self.paths["modded_dir"] / "temp_combined.jar",
        ]

        cleaner = FileCleaner()
        cleaner.cleanup_temp_dirs(temp_dirs, "compilation")
        cleaner.cleanup_temp_files(temp_files, "compilation")

        print("  [OK] Temporary files cleaned up")

    def _merge_custom_smali(self):
        additional_dirs = self.config.get_absolute_paths(self.paths["project_root"])
        if not additional_dirs:
            return

        print("\n" + "=" * 50)
        print("Merging Custom Smali Files")
        print("=" * 50)

        for custom_dir in additional_dirs:
            if custom_dir.exists():
                merged = self.apk_analyzer.merge_smali_files(
                    custom_dir, self.config.target_dex_index
                )
                if merged > 0:
                    self.changed_values.append(
                        {
                            "Name": f"Smali files from {custom_dir.name}",
                            "Old": "0",
                            "New": str(merged),
                        }
                    )

    def _merge_smali_files(self, source_dir: Path):
        if not self.apk_analyzer:
            return

        merged = self.apk_analyzer.merge_smali_files(
            source_dir, self.config.target_dex_index
        )

        if merged > 0:
            self.changed_values.append(
                {"Name": "Compiled smali files", "Old": "0", "New": str(merged)}
            )

    def _build_unsigned_apk(self):
        print("\n" + "=" * 40)
        print("Building unsigned APK...")
        print("=" * 40)

        self.unsigned_apk_path = self.paths["project_root"] / self.UNSIGNED_APK
        builder = ApkBuilder(self.found_files["apktool_jar"])
        builder.build(self.paths["modded_dir"], self.unsigned_apk_path)
        print(f"[OK] Unsigned APK: {self.unsigned_apk_path.name}")

    def _build_signed_apk(self):
        self._build_unsigned_apk()
        self._zipalign_apk()
        self._sign_apk()
        self._verify_signature()
        self._cleanup_temp_files()

    def _zipalign_apk(self, input_apk=None):
        print("\n" + "=" * 40)
        print("Zipaligning APK...")
        print("=" * 40)

        input_apk = (
            input_apk
            or self.unsigned_apk_path
            or self.paths["project_root"] / self.UNSIGNED_APK
        )
        self.aligned_apk_path = self.paths["project_root"] / self.ALIGNED_APK

        signer = ApkSigner(self.paths["android_sdk"])
        build_tools = signer.find_build_tools()
        zipalign, _ = signer.locate_tools(build_tools)

        signer.zipalign(zipalign, input_apk, self.aligned_apk_path)
        print(f"[OK] Aligned APK: {self.aligned_apk_path.name}")
        return self.aligned_apk_path

    def _sign_apk(self, input_apk=None, output_apk=None):
        print("\n" + "=" * 40)
        print("Signing APK...")
        print("=" * 40)

        if not self.keystore_config:
            raise RuntimeError("Keystore not loaded. Run _load_keystore_config first")

        input_apk = (
            input_apk
            or self.aligned_apk_path
            or self.paths["project_root"] / self.ALIGNED_APK
        )

        if output_apk is None:
            signed_name = f"{self.config.app_name} ({self.config.version_name}).apk"
            signed_name = "".join(c for c in signed_name if c not in '<>:"/\\|?*')
            output_apk = self.paths["project_root"] / signed_name

        self.signed_apk_path = output_apk

        signer = ApkSigner(self.paths["android_sdk"])
        build_tools = signer.find_build_tools()
        _, apksigner = signer.locate_tools(build_tools)

        signer.sign(apksigner, input_apk, self.signed_apk_path, self.keystore_config)
        print(f"[OK] Signed APK: {self.signed_apk_path.name}")
        return self.signed_apk_path

    def _sign_existing_apk(self, apk_path=None):
        if apk_path is None:
            apk_path = self._select_apk_to_sign()

        self._zipalign_apk(apk_path)
        self._sign_apk()
        self._verify_signature()

    def _select_apk_to_sign(self):
        apk_files = list(self.paths["project_root"].glob("*.apk"))
        if not apk_files:
            raise FileNotFoundError("No APK files found")

        print("\nAvailable APKs to sign:")
        for i, apk in enumerate(apk_files, 1):
            size = apk.stat().st_size / (1024 * 1024)
            mod_time = datetime.fromtimestamp(apk.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M"
            )
            print(f"  {i}. {apk.name} ({size:.2f} MB) - {mod_time}")

        while True:
            try:
                choice = int(input("\nSelect APK to sign (number): ")) - 1
                if 0 <= choice < len(apk_files):
                    return apk_files[choice]
            except (ValueError, IndexError):
                pass
            print("Invalid choice, try again")

    def _verify_signature(self, apk_path=None):
        print("\n" + "=" * 40)
        print("Verifying APK signature...")
        print("=" * 40)

        apk_path = apk_path or self.signed_apk_path
        if not apk_path or not apk_path.exists():
            raise FileNotFoundError("No signed APK found")

        signer = ApkSigner(self.paths["android_sdk"])
        build_tools = signer.find_build_tools()
        _, apksigner = signer.locate_tools(build_tools)

        signer.verify(apksigner, apk_path)
        print(f"[OK] Signature verified for {apk_path.name}")

    def _cleanup_temp_files(self, files=None):
        print("\n" + "=" * 40)
        print("Cleaning up temporary files...")
        print("=" * 40)

        cleaner = FileCleaner()

        files_to_clean = files or [
            self.paths["project_root"] / self.UNSIGNED_APK,
            self.paths["project_root"] / self.ALIGNED_APK,
        ]

        existing_files = [f for f in files_to_clean if f.exists()]
        if existing_files:
            cleaner.cleanup_temp_files(existing_files)
            for f in existing_files:
                print(f"  [OK] Removed: {f.name}")
        else:
            print("  [i] No temporary files to clean up")

        cleaner.cleanup_temp_dirs(
            [
                self.paths["modded_dir"] / "temp_classes",
                self.paths["modded_dir"] / "temp_dex",
                self.paths["modded_dir"] / "temp_combine",
                self.paths["modded_dir"] / "temp_src",
            ]
        )
        print("[OK] Temporary files cleaned up")

    def _cleanup_all(self):
        print("\n" + "=" * 40)
        print("Full cleanup...")
        print("=" * 40)

        self._cleanup_temp_files()

        if self.paths["modded_dir"].exists():
            shutil.rmtree(self.paths["modded_dir"], ignore_errors=True)
            print(f"[OK] Removed {self.paths['modded_dir']}")

    def _show_apk_info(self, apk_path=None):
        apk_path = apk_path or self.signed_apk_path
        if not apk_path or not apk_path.exists():
            print("[WARNING] No APK found")
            return

        size_mb = apk_path.stat().st_size / (1024 * 1024)
        print(f"\nAPK: {apk_path.name}")
        print(f"Size: {size_mb:.2f} MB")
        print(f"Path: {apk_path.resolve()}")
        print(f"Modified: {datetime.fromtimestamp(apk_path.stat().st_mtime)}")

    def _list_apks(self):
        apks = list(self.paths["project_root"].glob("*.apk"))
        if not apks:
            print("No APK files found")
            return

        print("\nAPK files in project:")
        for apk in sorted(apks, key=lambda x: x.stat().st_mtime, reverse=True):
            size = apk.stat().st_size / (1024 * 1024)
            mod = datetime.fromtimestamp(apk.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            print(f"  {apk.name:<50} {size:6.2f} MB  {mod}")

    def _print_final_summary(self):
        if self.signed_apk_path and self.signed_apk_path.exists():
            self._print_apk_details()
        else:
            print("\n[WARNING]: Signed APK not found or not created")

    def _print_changed_values(self):
        print("\nChanged Values:")
        print("-" * 50)
        for item in self.changed_values:
            print(f"{item['Name']:<35} : {item['Old']} -> {item['New']}")

    def _print_apk_details(self):
        print("\n" + "=" * 50)
        print("APK DETAILS")
        print("=" * 50)

        apk_size_mb = self.signed_apk_path.stat().st_size / (1024 * 1024)
        print(f"File Name       : {self.signed_apk_path.name}")
        print(f"Full Path       : {self.signed_apk_path.resolve()}")
        print(f"File Size       : {apk_size_mb:.2f} MB")
        print(f"Package Name    : {self.config.application_id}")
        print(f"Version Code    : {self.config.version_code}")
        print(f"Version Name    : {self.config.version_name}")

        self._print_manifest_details()
        print("\n[OK] APK is ready and fully signed!")
        print("=" * 50)

    def _print_manifest_details(self):
        manifest_path = self.paths["modded_dir"] / self.MANIFEST_FILE
        if not manifest_path.exists():
            return

        try:
            ET.register_namespace("android", self.ANDROID_NS)
            tree = ET.parse(manifest_path)
            root = tree.getroot()

            self._print_sdk_versions(root)
            self._print_permissions(root)

        except (ET.ParseError, OSError) as e:
            print(f"[WARNING] Could not read manifest details: {e}")

    def _print_sdk_versions(self, root):
        uses_sdk = root.find("uses-sdk")
        if uses_sdk is not None:
            min_sdk = uses_sdk.get(f"{{{self.ANDROID_NS}}}minSdkVersion", "")
            target_sdk = uses_sdk.get(f"{{{self.ANDROID_NS}}}targetSdkVersion", "")
            print(f"Min SDK         : {min_sdk}")
            print(f"Target SDK      : {target_sdk}")

    def _print_permissions(self, root):
        permissions = [
            perm.get(f"{{{self.ANDROID_NS}}}name", "")
            for perm in root.findall("uses-permission")
            if perm.get(f"{{{self.ANDROID_NS}}}name", "")
        ]

        if permissions:
            print(f"Permissions     : {len(permissions)} total")
            for perm in permissions[:5]:
                print(f"  - {perm}")
            if len(permissions) > 5:
                print(f"  ... and {len(permissions) - 5} more")
        else:
            print("Permissions     : none")


def main():
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    os.environ["JAVA_TOOL_OPTIONS"] = "-Dfile.encoding=UTF-8"

    builder = ApkForge()
    builder.run()


if __name__ == "__main__":
    main()
