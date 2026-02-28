# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : tool_finder.py
# Purpose : Locates required tools (CMake, Ninja, NDK) in system paths,
#           Android SDK, and standard installation directories.
# =============================================================================

import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

from platform_utils import (
    get_platform_info,
    find_executable,
    normalize_path,
    to_native_path,
)


class ToolFinder:
    CMAKE_DOWNLOAD_URL = "https://cmake.org/download/"
    NINJA_DOWNLOAD_URL = "https://github.com/ninja-build/ninja/releases"

    def __init__(
            self,
            android_sdk: Optional[Path] = None,
            logger: Optional[logging.Logger] = None,
    ):
        self.android_sdk = normalize_path(android_sdk) if android_sdk else None
        self.logger = logger or logging.getLogger(__name__)
        self.platform_info = get_platform_info()

    def find_cmake(self) -> Optional[str]:
        cmake = find_executable("cmake")
        if cmake:
            self.logger.info(f"Found CMake in PATH: {cmake}")
            return cmake

        sdk_cmake = self._find_sdk_cmake()
        if sdk_cmake:
            return sdk_cmake

        for path in self._get_cmake_paths():
            if path.exists():
                self.logger.info(f"Found CMake at: {path}")
                return to_native_path(path)

        self._print_cmake_help()
        return None

    def find_ninja(self) -> Optional[str]:
        ninja = find_executable("ninja")
        if ninja:
            self.logger.info(f"Found Ninja in PATH: {ninja}")
            return ninja

        sdk_ninja = self._find_sdk_ninja()
        if sdk_ninja:
            return sdk_ninja

        for path in self._get_ninja_paths():
            if path.exists():
                self.logger.info(f"Found Ninja at: {path}")
                return to_native_path(path)

        self._print_ninja_help()
        return None

    def find_ndk(self) -> Optional[Path]:
        if not self.android_sdk or not self.android_sdk.exists():
            return None

        ndk_paths = self._collect_ndk_paths()

        if not ndk_paths:
            return None

        ndk_paths.sort(key=self._parse_ndk_version, reverse=True)

        ndk = ndk_paths[0]
        self.logger.info(f"Found NDK: {ndk.name}")

        return ndk

    def find_java_home(self) -> Optional[Path]:
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            path = normalize_path(java_home)
            java_exe = "java.exe" if self.platform_info["is_windows"] else "java"
            if (path / "bin" / java_exe).exists():
                return path

        java = find_executable("java")
        if java:
            java_path = normalize_path(java)

            if java_path.parent.name == "bin":
                candidate = java_path.parent.parent
                javac_exe = "javac.exe" if self.platform_info["is_windows"] else "javac"
                if (candidate / "bin" / javac_exe).exists():
                    return candidate

        return None

    def _find_sdk_cmake(self) -> Optional[str]:
        if not self.android_sdk or not self.android_sdk.exists():
            return None

        cmake_dir = self.android_sdk / "cmake"
        if not cmake_dir.exists():
            return None

        versions = [item for item in cmake_dir.iterdir() if item.is_dir()]
        if not versions:
            return None

        versions.sort(key=lambda x: x.name, reverse=True)

        cmake_exe = "cmake.exe" if self.platform_info["is_windows"] else "cmake"

        for version_dir in versions:
            cmake_path = version_dir / "bin" / cmake_exe
            if cmake_path.exists():
                self.logger.info(f"Found CMake in Android SDK: {cmake_path}")
                return to_native_path(cmake_path)

        return None

    def _find_sdk_ninja(self) -> Optional[str]:
        if not self.android_sdk or not self.android_sdk.exists():
            return None

        cmake_dir = self.android_sdk / "cmake"
        if not cmake_dir.exists():
            return None

        ninja_exe = "ninja.exe" if self.platform_info["is_windows"] else "ninja"

        for version_dir in cmake_dir.iterdir():
            if not version_dir.is_dir():
                continue

            ninja_path = version_dir / "bin" / ninja_exe
            if ninja_path.exists():
                self.logger.info(f"Found Ninja in Android SDK: {ninja_path}")
                return to_native_path(ninja_path)

        return None

    def _get_cmake_paths(self) -> List[Path]:
        if self.platform_info["is_windows"]:
            return [
                Path("C:/Program Files/CMake/bin/cmake.exe"),
                Path("C:/Program Files (x86)/CMake/bin/cmake.exe"),
                Path.home() / "AppData/Local/Programs/CMake/bin/cmake.exe",
            ]
        if self.platform_info["is_mac"]:
            return [
                Path("/Applications/CMake.app/Contents/bin/cmake"),
                Path("/usr/local/bin/cmake"),
                Path("/opt/homebrew/bin/cmake"),
                Path("/opt/local/bin/cmake"),
            ]
        return [
            Path("/usr/bin/cmake"),
            Path("/usr/local/bin/cmake"),
            Path("/snap/bin/cmake"),
            Path.home() / ".local/bin/cmake",
            Path("/opt/cmake/bin/cmake"),
        ]

    def _get_ninja_paths(self) -> List[Path]:
        ninja_exe = "ninja.exe" if self.platform_info["is_windows"] else "ninja"

        if self.platform_info["is_windows"]:
            return [
                Path("C:/Program Files/Ninja") / ninja_exe,
                Path.home() / "AppData/Local/Programs/Ninja" / ninja_exe,
                Path("C:/tools/ninja") / ninja_exe,
            ]
        if self.platform_info["is_mac"]:
            return [
                Path("/usr/local/bin") / ninja_exe,
                Path("/opt/homebrew/bin") / ninja_exe,
                Path("/opt/local/bin") / ninja_exe,
            ]
        return [
            Path("/usr/bin") / ninja_exe,
            Path("/usr/local/bin") / ninja_exe,
            Path("/snap/bin") / ninja_exe,
            Path.home() / ".local/bin" / ninja_exe,
        ]

    def _collect_ndk_paths(self) -> List[Path]:
        ndk_paths = []

        if not self.android_sdk:
            return ndk_paths

        ndk_dir = self.android_sdk / "ndk"
        if ndk_dir.exists():
            ndk_paths.extend(item for item in ndk_dir.iterdir() if item.is_dir())

        ndk_bundle = self.android_sdk / "ndk-bundle"
        if ndk_bundle.exists():
            ndk_paths.append(ndk_bundle)

        side_by_side = self.android_sdk / "ndk" / "side-by-side"
        if side_by_side.exists():
            ndk_paths.extend(item for item in side_by_side.iterdir() if item.is_dir())

        return ndk_paths

    @staticmethod
    def _parse_ndk_version(path: Path) -> Tuple[int, int, int]:
        name = path.name

        name = name.replace("android-ndk-", "").replace("ndk-", "")

        parts = name.split(".")
        version_nums = []

        for part in parts[:3]:
            num_str = "".join(c for c in part if c.isdigit())
            try:
                version_nums.append(int(num_str) if num_str else 0)
            except ValueError:
                version_nums.append(0)

        while len(version_nums) < 3:
            version_nums.append(0)

        return tuple(version_nums[:3])

    def _get_platform_package_managers(self):
        if self.platform_info["is_windows"]:
            return ["  • Chocolatey: choco install", "  • Scoop: scoop install"]
        if self.platform_info["is_mac"]:
            return ["  • Homebrew: brew install", "  • MacPorts: sudo port install"]
        return [
            "  • APT: sudo apt-get install",
            "  • DNF: sudo dnf install",
            "  • Pacman: sudo pacman -S",
        ]

    def _print_cmake_help(self):
        self.logger.error("\nCMake not found. Installation options:")

        for pm in self._get_platform_package_managers():
            self.logger.info(f"{pm} cmake")

        self.logger.info(f"  • Download: {self.CMAKE_DOWNLOAD_URL}")
        self.logger.info("  • Android Studio SDK Manager (includes CMake)")

    def _print_ninja_help(self):
        self.logger.error("\nNinja not found. Installation options:")

        for pm in self._get_platform_package_managers():
            if "choco" in pm:
                self.logger.info(f"{pm} ninja")
            elif "scoop" in pm:
                self.logger.info(f"{pm} ninja")
            elif "brew" in pm:
                self.logger.info(f"{pm} ninja")
            elif "port" in pm:
                self.logger.info(f"{pm} ninja")
            else:
                self.logger.info(f"{pm} ninja-build")

        self.logger.info(f"  • Download: {self.NINJA_DOWNLOAD_URL}")
