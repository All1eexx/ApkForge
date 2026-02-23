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
import platform
import shutil
from pathlib import Path
from typing import List, Optional


class SDKDetector:
    ANDROID_SDK_PATH = "/opt/android-sdk"
    ANDROID_STUDIO_SDK_SUBPATH = "Android Studio"

    def __init__(self):
        self.system = platform.system().lower()
        self.user_home = Path.home()

    def find_sdk(self) -> Optional[Path]:
        sdk_path = self._get_sdk_from_environment()
        if sdk_path:
            return sdk_path

        search_paths = self._get_sdk_paths_by_platform()
        sdk_path = self._search_in_paths(search_paths)
        if sdk_path:
            return sdk_path

        return self._get_sdk_from_sdkmanager()

    @staticmethod
    def _get_sdk_from_environment() -> Optional[Path]:
        env_vars = ["ANDROID_SDK_ROOT", "ANDROID_HOME", "ANDROID_SDK"]
        for env_var in env_vars:
            env_path = os.environ.get(env_var)
            if env_path:
                path = Path(env_path)
                if path.exists():
                    return path.resolve()
        return None

    def _get_sdk_paths_by_platform(self) -> List[Path]:
        platform_paths = {
            "windows": self._get_windows_sdk_paths,
            "darwin": self._get_darwin_sdk_paths,
            "linux": self._get_linux_sdk_paths,
        }

        path_getter = platform_paths.get(self.system, self._get_default_sdk_paths)
        return path_getter()

    def _get_windows_sdk_paths(self) -> List[Path]:
        username = os.environ.get("USERNAME", "")
        return [
            self.user_home / "AppData" / "Local" / "Android" / "Sdk",
            Path(f"C:/Users/{username}/AppData/Local/Android/Sdk"),
            Path("C:/Program Files/Android/Android Studio") / "sdk",
            Path("C:/Program Files (x86)/Android/Android Studio") / "sdk",
            Path("C:/Android/sdk"),
            Path("C:/android-sdk"),
            self.user_home / "Android" / "Sdk",
        ]

    def _get_darwin_sdk_paths(self) -> List[Path]:
        return [
            self.user_home / "Library" / "Android" / "sdk",
            Path("/Applications/Android Studio.app/Contents/sdk"),
            Path("/usr/local/share/android-sdk"),
            Path(self.ANDROID_SDK_PATH),
            self.user_home / "Android" / "sdk",
        ]

    def _get_linux_sdk_paths(self) -> List[Path]:
        return [
            self.user_home / "Android" / "Sdk",
            self.user_home / "android-sdk",
            Path("/usr/lib/android-sdk"),
            Path("/usr/local/lib/android-sdk"),
            Path(self.ANDROID_SDK_PATH),
            Path("/opt/google/android-sdk"),
            self.user_home / "snap" / "android-studio" / "current" / "Android" / "Sdk",
            self.user_home / ".local" / "share" / "android-sdk",
        ]

    def _get_default_sdk_paths(self) -> List[Path]:
        return [
            self.user_home / "Android" / "Sdk",
            self.user_home / "android-sdk",
            Path("/usr/local/android-sdk"),
            Path(self.ANDROID_SDK_PATH),
        ]

    @staticmethod
    def _search_in_paths(search_paths: List[Path]) -> Optional[Path]:
        for path in search_paths:
            if path.exists():
                return path.resolve()
        return None

    @staticmethod
    def _get_sdk_from_sdkmanager() -> Optional[Path]:
        try:
            sdkmanager_path = shutil.which("sdkmanager")
            if sdkmanager_path:
                sdk_path = Path(sdkmanager_path).parent.parent
                if sdk_path.exists():
                    return sdk_path.resolve()
        except (OSError, TypeError):
            pass
        return None