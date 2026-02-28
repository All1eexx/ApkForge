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
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union

from sdk_detector import SDKDetector
from platform_utils import normalize_path, get_platform_info


class PathResolver:
    def __init__(self, project_root: Path):
        self.project_root = normalize_path(project_root)
        self.platform_info = get_platform_info()

    def resolve(
            self, path_value: Union[str, Path, None], context: str = ""
    ) -> Optional[Path]:
        if path_value is None:
            return None

        if isinstance(path_value, Path):
            path_value = str(path_value)

        if not isinstance(path_value, str):
            raise ValueError(
                f"Path must be string or Path, got {type(path_value)} for {context}"
            )

        path_value = path_value.strip()
        if not path_value:
            return None

        path_value = self._expand_env_vars(path_value)

        path = Path(path_value)

        path = path.expanduser()

        if path.is_absolute():
            return normalize_path(path)

        if self.platform_info["is_windows"] and re.match(
                r"^[a-zA-Z]:[^\\/]", path_value
        ):
            path = Path(path_value[0:2] + "/" + path_value[2:])

        return normalize_path(self.project_root / path)

    @staticmethod
    def _expand_env_vars(path_str: str) -> str:

        def replace_env(match):
            env_var = match.group(1)
            return os.environ.get(env_var, match.group(0))

        pattern = r"\$\{([^}]+)\}"
        path_str = re.sub(pattern, replace_env, path_str)

        if not get_platform_info()["is_windows"]:
            pattern = r"\$([a-zA-Z_][a-zA-Z0-9_]*)"
            path_str = re.sub(pattern, replace_env, path_str)

        return path_str


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
        self.project_root = normalize_path(project_root or self._find_project_root())
        self.config_path = normalize_path(
            config_path or self.project_root / self.CONFIG_FILE
        )
        self.config = self._load_config(self.config_path)
        self.sdk_detector = SDKDetector()
        self.resolver = PathResolver(self.project_root)
        self.paths_config = self.config.get("paths", {})

    @staticmethod
    def _find_project_root() -> Path:
        current = Path(__file__).resolve()

        for parent in current.parents:
            config_file = parent / PathManager.CONFIG_FILE
            if config_file.exists():
                return parent

        return Path.cwd().resolve()

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
        paths = {
            "project_root": self.project_root,
            "config_path": self.config_path,
        }

        self._resolve_directory_paths(paths)
        self._resolve_tool_paths(paths)
        self._resolve_output_paths(paths)
        self._resolve_libs_path(paths)
        self._resolve_keystore_path(paths)

        return paths

    def _resolve_directory_paths(self, paths: Dict[str, Path]):
        dirs_config = self.paths_config.get("directories", {})
        defaults = self.DEFAULTS["directories"]

        dir_mapping = {
            "original_game": "original_game_dir",
            "modded": "modded_dir",
            "src": "src_dir",
        }

        for config_key, path_key in dir_mapping.items():
            config_val = dirs_config.get(config_key)
            default_val = defaults.get(config_key)

            resolved = self.resolver.resolve(config_val or default_val, path_key)
            if resolved:
                paths[path_key] = resolved

        decompiled = dirs_config.get("decompiled")
        if decompiled:
            resolved = self.resolver.resolve(decompiled, "decompiled_dir")
            if resolved:
                paths["decompiled_dir"] = resolved

    def _resolve_tool_paths(self, paths: Dict[str, Path]):
        tools_config = self.paths_config.get("tools", {})

        jar_tools = [
            ("apktool", "apktool_jar"),
            ("baksmali", "baksmali_jar"),
            ("smali", "smali_jar"),
        ]

        for config_key, path_key in jar_tools:
            val = tools_config.get(config_key)
            if val:
                resolved = self.resolver.resolve(val, config_key)
                if resolved:
                    paths[path_key] = resolved

        android_sdk = tools_config.get("android_sdk")
        if android_sdk:
            resolved = self.resolver.resolve(android_sdk, "android_sdk")
            if resolved:
                paths["android_sdk"] = resolved
        else:
            detected_sdk = self.sdk_detector.find_sdk()
            if detected_sdk:
                paths["android_sdk"] = normalize_path(detected_sdk)

    def _resolve_output_paths(self, paths: Dict[str, Path]):
        output_config = self.paths_config.get("output", {})

        output_mapping = {
            "build": "build_output_dir",
            "logs": "logs_dir",
            "temp": "temp_dir",
        }

        for config_key, path_key in output_mapping.items():
            val = output_config.get(config_key)
            if val:
                resolved = self.resolver.resolve(val, path_key)
                if resolved:
                    paths[path_key] = resolved

        if "temp_dir" in paths:
            paths["temp_dir"].mkdir(parents=True, exist_ok=True)

    def _resolve_libs_path(self, paths: Dict[str, Path]):
        download_config = self.paths_config.get("download_dependencies", {})
        libs_path = download_config.get("libs")

        if libs_path:
            resolved = self.resolver.resolve(libs_path, "libs_dir")
            if resolved:
                paths["libs_dir"] = resolved

    def _resolve_keystore_path(self, paths: Dict[str, Path]):
        keystore = self.paths_config.get("keystore")
        val = keystore or self.DEFAULTS["keystore"]

        resolved = self.resolver.resolve(val, "keystore_config")
        if resolved:
            paths["keystore_config"] = resolved

    def get_relative_path(self, path: Path, base: Optional[Path] = None) -> str:
        base = base or self.project_root
        try:
            return str(path.relative_to(base))
        except ValueError:
            return str(path)

    @staticmethod
    def to_posix(path: Path) -> str:
        return str(path.as_posix())

    @staticmethod
    def to_native(path: Path) -> str:
        return str(path)


def get_paths() -> Dict[str, Path]:
    return PathManager().get_paths()
