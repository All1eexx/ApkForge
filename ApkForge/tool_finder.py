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
import platform
import shutil
from pathlib import Path
from typing import List, Optional


class ToolFinder:
    def __init__(
            self,
            android_sdk: Optional[Path] = None,
            logger: Optional[logging.Logger] = None,
    ):
        self.android_sdk = android_sdk
        self.logger = logger or logging.getLogger(__name__)
        self.system = platform.system().lower()

    def find_cmake(self) -> Optional[str]:
        cmake_path = shutil.which("cmake")
        if cmake_path:
            return cmake_path

        sdk_cmake = self._find_sdk_tool(
            "cmake.exe" if self.system == "windows" else "cmake"
        )
        if sdk_cmake:
            return sdk_cmake

        for path in self._get_cmake_paths():
            if path.exists():
                return str(path)

        self._print_cmake_help()
        return None

    def find_ninja(self) -> Optional[str]:
        ninja_path = shutil.which("ninja")
        if ninja_path:
            return ninja_path

        sdk_ninja = self._find_sdk_tool(
            "ninja.exe" if self.system == "windows" else "ninja"
        )
        if sdk_ninja:
            return sdk_ninja

        for path in self._get_ninja_paths():
            if path.exists():
                return str(path)

        self._print_ninja_help()
        return None

    def find_ndk(self) -> Optional[Path]:
        if not self.android_sdk or not self.android_sdk.exists():
            return None

        ndk_paths = self._collect_ndk_paths()

        if not ndk_paths:
            return None

        ndk_paths.sort(key=self._parse_ndk_version, reverse=True)
        return ndk_paths[0]

    def _find_sdk_tool(self, tool_executable: str) -> Optional[str]:
        if not self.android_sdk or not self.android_sdk.exists():
            return None

        cmake_dir = self.android_sdk / "cmake"
        if not cmake_dir.exists():
            return None

        for version_dir in cmake_dir.iterdir():
            if not version_dir.is_dir():
                continue

            tool_path = version_dir / "bin" / tool_executable
            if tool_path.exists():
                return str(tool_path)

        return None

    def _get_cmake_paths(self) -> List[Path]:
        home = Path.home()

        if self.system == "windows":
            return [
                Path(r"C:\Program Files\CMake\bin\cmake.exe"),
                Path(r"C:\Program Files (x86)\CMake\bin\cmake.exe"),
                home / "AppData/Local/Programs/CMake/bin/cmake.exe",
            ]
        elif self.system == "darwin":
            return [
                Path("/Applications/CMake.app/Contents/bin/cmake"),
                Path("/usr/local/bin/cmake"),
                Path("/opt/homebrew/bin/cmake"),
            ]
        else:
            return [
                Path("/usr/bin/cmake"),
                Path("/usr/local/bin/cmake"),
                Path("/snap/bin/cmake"),
                home / ".local/bin/cmake",
            ]

    def _get_ninja_paths(self) -> List[Path]:
        home = Path.home()

        if self.system == "windows":
            return [
                Path(r"C:\Program Files\Ninja\ninja.exe"),
                home / "AppData/Local/Programs/Ninja/ninja.exe",
            ]
        elif self.system == "darwin":
            return [
                Path("/usr/local/bin/ninja"),
                Path("/opt/homebrew/bin/ninja"),
            ]
        else:
            return [
                Path("/usr/bin/ninja"),
                Path("/usr/local/bin/ninja"),
                Path("/snap/bin/ninja"),
                home / ".local/bin/ninja",
            ]

    def _collect_ndk_paths(self) -> List[Path]:
        ndk_paths = []

        ndk_dir = self.android_sdk / "ndk"
        if ndk_dir.exists():
            for item in ndk_dir.iterdir():
                if item.is_dir():
                    ndk_paths.append(item)

        ndk_bundle = self.android_sdk / "ndk-bundle"
        if ndk_bundle.exists():
            ndk_paths.append(ndk_bundle)

        return ndk_paths

    @staticmethod
    def _parse_ndk_version(path: Path) -> tuple:
        name = path.name

        version_str = name.replace("android-ndk-", "")

        parts = version_str.split(".")
        version_nums = []

        for part in parts:
            try:
                num_str = "".join(c for c in part if c.isdigit())
                version_nums.append(int(num_str) if num_str else 0)
            except ValueError:
                version_nums.append(0)

        while len(version_nums) < 3:
            version_nums.append(0)

        return tuple(version_nums[:3])

    def _print_cmake_help(self):
        self.logger.error("\nCMake not found. Installation options:")
        self.logger.info("  1. Install via package manager:")

        if self.system == "windows":
            self.logger.info("     - Chocolatey: choco install cmake")
            self.logger.info("     - Scoop: scoop install cmake")
        elif self.system == "darwin":
            self.logger.info("     - Homebrew: brew install cmake")
        else:
            self.logger.info("     - APT: sudo apt-get install cmake")
            self.logger.info("     - DNF: sudo dnf install cmake")

        self.logger.info("  2. Download from: https://cmake.org/download/")
        self.logger.info("  3. Install via Android Studio SDK Manager")

    def _print_ninja_help(self):
        self.logger.error("\nNinja not found.")
        self.logger.info("  Install via package manager (same as CMake)")
        self.logger.info(
            "  Or download from: https://github.com/ninja-build/ninja/releases"
        )
