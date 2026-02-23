# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : path_manager.py
# Purpose : Manages and resolves all file paths used in the build process.
# =============================================================================

import json
import os
import platform
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union

from sdk_detector import SDKDetector


class PathResolver:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.system = platform.system().lower()

    def is_absolute_path(self, path_str: str) -> bool:
        if not isinstance(path_str, str):
            return False

        if self.system == "windows":
            if len(path_str) >= 2 and path_str[1] == ":":
                return True
            if path_str.startswith("\\\\"):
                return True

        if path_str.startswith("/"):
            return True

        if path_str.startswith("file://"):
            return True

        if "${" in path_str and "}" in path_str:
            return True

        if path_str.startswith("~"):
            return False

        return False

    def resolve(
            self, path_value: Union[str, None], context: str = ""
    ) -> Optional[Path]:
        if path_value is None:
            return None

        if not isinstance(path_value, str):
            raise ValueError(
                f"Path must be string, got {type(path_value)} for {context}"
            )

        if not path_value.strip():
            return None

        if path_value.startswith("~"):
            expanded = Path(path_value).expanduser()
            return expanded.resolve()

        path_value = self._expand_env_vars(path_value)
        path = Path(path_value)

        if path.is_absolute():
            return path.resolve()

        if self.is_absolute_path(path_value):
            if (
                    self.system == "windows"
                    and len(path_value) >= 2
                    and path_value[1] == ":"
                    and (len(path_value) == 2 or path_value[2] not in ("\\", "/"))
            ):
                fixed_path = f"{path_value[:2]}/{path_value[2:]}"
                fixed_path = fixed_path.replace("\\", "/")
                return Path(fixed_path).resolve()

            print(
                f"  Warning: Path '{path_value}' looks absolute but not found. Using relative to project root."
            )

        return (self.project_root / path).resolve()

    @staticmethod
    def _expand_env_vars(path_str: str) -> str:

        def replace_env(match):
            env_var = match.group(1)
            return os.environ.get(env_var, match.group(0))

        pattern = r"\$\{([^}]+)\}"
        return re.sub(pattern, replace_env, path_str)


class PathManager:
    CONFIG_FILE = "build_config.json"
    DEFAULTS = {
        "directories": {
            "original_game": "OriginalGame",
            "modded": "ModdedGame",
            "src": "src",
        },
        "keystore": "keystore.json",
    }

    def __init__(
            self, project_root: Optional[Path] = None, config_path: Optional[Path] = None
    ):
        self.project_root = project_root or self._find_project_root()
        self.config = self._load_config(
            config_path or self.project_root / self.CONFIG_FILE
        )
        self.sdk_detector = SDKDetector()
        self.resolver = PathResolver(self.project_root)
        self.paths_config = self.config.get("paths", {})

        if project_root:
            self.project_root = Path(project_root).resolve()
        else:
            self.project_root = self._find_project_root()

        if config_path:
            self.config_path = Path(config_path).resolve()
        else:
            self.config_path = self.project_root / self.CONFIG_FILE

        self.config = self._load_config(self.config_path)

    @staticmethod
    def _find_project_root() -> Path:
        current = Path(__file__).resolve()

        for parent in current.parents:
            if (parent / PathManager.CONFIG_FILE).exists():
                return parent

        return Path.cwd()

    @staticmethod
    def _load_config(config_path: Path) -> Dict[str, Any]:
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Could not load config from {config_path}: {e}")
        return {}

    def get_paths(self) -> Dict[str, Path]:
        paths = {"project_root": self.project_root}

        self._resolve_directory_paths(paths)
        self._resolve_tool_paths(paths)
        self._resolve_output_paths(paths)
        self._resolve_libs_path(paths)
        self._resolve_keystore_path(paths)

        return paths

    def _resolve_directory_paths(self, paths: dict):
        dirs_config = self.paths_config.get("directories", {})
        defaults = self.DEFAULTS["directories"]

        for key, default in defaults.items():
            config_val = dirs_config.get(key)
            key_map = {
                "original_game": "original_game_dir",
                "modded": "modded_dir",
                "src": "src_dir",
            }
            paths[key_map[key]] = self.resolver.resolve(
                config_val or default, key_map[key]
            )

        decompiled = dirs_config.get("decompiled")
        if decompiled:
            paths["decompiled_dir"] = self.resolver.resolve(
                decompiled, "decompiled_dir"
            )

    def _resolve_tool_paths(self, paths: dict):
        tools_config = self.paths_config.get("tools", {})

        for config_key, path_key in [
            ("apktool", "apktool_jar"),
            ("baksmali", "baksmali_jar"),
            ("smali", "smali_jar"),
        ]:
            val = tools_config.get(config_key)
            if val:
                paths[path_key] = self.resolver.resolve(val, config_key)

        android_sdk = tools_config.get("android_sdk")
        if android_sdk:
            paths["android_sdk"] = self.resolver.resolve(android_sdk, "android_sdk")
        else:
            detected_sdk = self.sdk_detector.find_sdk()
            if detected_sdk:
                paths["android_sdk"] = detected_sdk

    def _resolve_output_paths(self, paths: dict):
        output_config = self.paths_config.get("output", {})

        for config_key, path_key in [
            ("build", "build_output_dir"),
            ("logs", "logs_dir"),
            ("temp", "temp_dir"),
        ]:
            val = output_config.get(config_key)
            if val:
                paths[path_key] = self.resolver.resolve(val, path_key)

    def _resolve_libs_path(self, paths: dict):
        download_config = self.paths_config.get("download_dependencies", {})
        libs_path = download_config.get("libs")
        if not libs_path:
            return

        resolved_libs = self.resolver.resolve(libs_path, "libs_dir")
        if not resolved_libs:
            return

        paths["libs_dir"] = resolved_libs
        if resolved_libs.exists():
            jar_count = len(list(resolved_libs.glob("*.jar")))
            print(f"\n  [PathManager] Libraries directory: {resolved_libs}")
            print(f"  [PathManager] Found {jar_count} JAR files")

    def _resolve_keystore_path(self, paths: dict):
        keystore = self.paths_config.get("keystore")
        val = keystore or self.DEFAULTS["keystore"]
        paths["keystore_config"] = self.resolver.resolve(val, "keystore_config")


def get_paths():
    return PathManager().get_paths()