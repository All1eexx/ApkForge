# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : sdk_detector.py
# Purpose : Detects Android SDK locations across different platforms.
# =============================================================================

import os
import shutil
from pathlib import Path
from typing import List, Optional

from platform_utils import get_platform_info, normalize_path


class SDKDetector:
    WINDOWS_PATHS = [
        "%LOCALAPPDATA%\\Android\\Sdk",
        "%USERPROFILE%\\AppData\\Local\\Android\\Sdk",
        "C:\\Program Files\\Android\\Android Studio\\sdk",
        "C:\\Program Files (x86)\\Android\\Android Studio\\sdk",
        "C:\\Android\\sdk",
        "C:\\android-sdk",
        "%USERPROFILE%\\Android\\Sdk",
    ]

    MACOS_PATHS = [
        "~/Library/Android/sdk",
        "/Applications/Android Studio.app/Contents/sdk",
        "/usr/local/share/android-sdk",
        "/opt/android-sdk",
        "~/Android/sdk",
    ]

    LINUX_PATHS = [
        "~/Android/Sdk",
        "~/android-sdk",
        "/usr/lib/android-sdk",
        "/usr/local/lib/android-sdk",
        "/opt/android-sdk",
        "/opt/google/android-sdk",
        "~/snap/android-studio/current/Android/Sdk",
        "~/.local/share/android-sdk",
    ]

    REQUIRED_SDK_DIRS = ["platforms", "build-tools", "platform-tools"]

    def __init__(self):
        self.platform_info = get_platform_info()
        self.user_home = Path.home()

    def find_sdk(self) -> Optional[Path]:
        sdk_from_env = self._check_environment()
        if sdk_from_env:
            return sdk_from_env

        sdk_from_paths = self._check_common_paths()
        if sdk_from_paths:
            return sdk_from_paths

        return self._find_from_sdkmanager()

    def _check_environment(self) -> Optional[Path]:
        env_vars = ["ANDROID_SDK_ROOT", "ANDROID_HOME", "ANDROID_SDK"]

        for env_var in env_vars:
            env_path = os.environ.get(env_var)
            if env_path:
                path = normalize_path(env_path)
                if self._is_valid_sdk(path):
                    return path

        return None

    def _check_common_paths(self) -> Optional[Path]:
        paths = self._get_platform_paths()

        for path_str in paths:
            expanded = self._expand_path(path_str)
            path = normalize_path(expanded)

            if self._is_valid_sdk(path):
                return path

        return None

    def _get_platform_paths(self) -> List[str]:
        if self.platform_info["is_windows"]:
            return self.WINDOWS_PATHS
        if self.platform_info["is_mac"]:
            return self.MACOS_PATHS
        return self.LINUX_PATHS

    def _expand_path(self, path_str: str) -> str:
        if "%" in path_str and self.platform_info["is_windows"]:
            for key, value in os.environ.items():
                path_str = path_str.replace(f"%{key}%", value)

        if path_str.startswith("~"):
            path_str = str(self.user_home) + path_str[1:]

        return path_str

    @staticmethod
    def _is_valid_sdk(path: Path) -> bool:
        if not path.exists():
            return False

        for dir_name in SDKDetector.REQUIRED_SDK_DIRS:
            if not (path / dir_name).exists():
                return False

        platforms_dir = path / "platforms"
        if platforms_dir.exists():
            platforms = list(platforms_dir.glob("android-*"))
            if platforms:
                return True

        return False

    def _find_from_sdkmanager(self) -> Optional[Path]:
        sdkmanager = shutil.which("sdkmanager")
        if not sdkmanager:
            return None

        sdkmanager_path = Path(sdkmanager).resolve()

        sdk_candidate = sdkmanager_path.parent.parent.parent
        if self._is_valid_sdk(sdk_candidate):
            return sdk_candidate

        sdk_candidate = sdkmanager_path.parent.parent.parent.parent
        if self._is_valid_sdk(sdk_candidate):
            return sdk_candidate

        return None

    def find_platforms(self) -> List[Path]:
        sdk_path = self.find_sdk()
        if not sdk_path:
            return []

        platforms_dir = sdk_path / "platforms"
        if not platforms_dir.exists():
            return []

        return sorted(platforms_dir.glob("android-*"))

    def find_build_tools(self) -> List[Path]:
        sdk_path = self.find_sdk()
        if not sdk_path:
            return []

        build_tools_dir = sdk_path / "build-tools"
        if not build_tools_dir.exists():
            return []

        versions = []
        for item in build_tools_dir.iterdir():
            if item.is_dir():
                versions.append(item)

        return sorted(versions, key=lambda x: x.name, reverse=True)

    def get_latest_android_jar(self) -> Optional[Path]:
        platforms = self.find_platforms()
        if not platforms:
            return None

        def get_api_level(p: Path) -> int:
            try:
                return int(p.name.split("-")[1])
            except (IndexError, ValueError):
                return 0

        latest = max(platforms, key=get_api_level)
        android_jar = latest / "android.jar"

        return android_jar if android_jar.exists() else None
