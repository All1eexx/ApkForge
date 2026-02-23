# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : native_build_config.py
# Purpose : Configuration handler for C++ native builds.
# =============================================================================

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Optional


class NativeBuildConfig:
    def __init__(
            self,
            cpp_dir: Path,
            project_root: Path,
            ndk_path: Optional[Path] = None,
            logger: Optional[logging.Logger] = None,
    ):
        self.cpp_dir = cpp_dir
        self.project_root = project_root
        self.ndk_path = ndk_path
        self.logger = logger or logging.getLogger(__name__)

        self.build_type = self._load_build_type()
        self.target_abi = self._detect_target_abi()
        self.target_lib_name = self._parse_target_library_name()

    def _load_build_type(self) -> str:
        try:
            config_path = self.project_root / "build_config.json"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    build_type = config.get("build", {}).get("type", "release")
                    return build_type.lower()
        except Exception as e:
            self.logger.warning(f"Could not load build_type from config: {e}")

        self.logger.warning("Using 'release' as default build type")
        return "release"

    def _detect_target_abi(self) -> str:
        cmake_file = self.cpp_dir / "CMakeLists.txt"
        default_abi = "arm64-v8a"

        if not cmake_file.exists():
            return default_abi

        try:
            content = cmake_file.read_text(encoding="utf-8")

            pattern = r'set\s*\(\s*ANDROID_ABI\s+["${}]?(\w+[-\w]*)'
            match = re.search(pattern, content, re.IGNORECASE)

            if match:
                return match.group(1)
        except Exception as e:
            self.logger.warning(f"Could not read CMakeLists.txt: {e}")

        return default_abi

    def _parse_target_library_name(self) -> Optional[str]:
        cmake_file = self.cpp_dir / "CMakeLists.txt"

        if not cmake_file.exists():
            return None

        try:
            content = cmake_file.read_text(encoding="utf-8")

            patterns = [
                r"add_library\s*\(\s*(\w+)",
                r"project\s*\(\s*(\w+)",
            ]

            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1)
        except Exception as e:
            self.logger.warning(f"Could not parse library name: {e}")

        return None

    def prepare_build_directory(self) -> Path:
        build_dir = self.cpp_dir / "build"

        if build_dir.exists():
            shutil.rmtree(build_dir, ignore_errors=True)

        build_dir.mkdir(parents=True, exist_ok=True)
        return build_dir

    def get_cmake_args(self, cmake_path: str, ninja_path: str, build_dir: Path) -> list:
        args = [
            cmake_path,
            "-S",
            str(self.cpp_dir),
            "-B",
            str(build_dir),
            "-G",
            "Ninja",
            f"-DCMAKE_MAKE_PROGRAM={ninja_path}",
            f"-DCMAKE_BUILD_TYPE={self.build_type.capitalize()}",
            f"-DBUILD_TYPE={self.build_type.capitalize()}",
        ]

        if self.ndk_path:
            toolchain = self.ndk_path / "build/cmake/android.toolchain.cmake"

            if toolchain.exists():
                args.extend(
                    [
                        f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
                        f"-DANDROID_ABI={self.target_abi}",
                        "-DANDROID_STL=c++_shared",
                    ]
                )
                self.logger.info(f"Configuring for Android ABI: {self.target_abi}")
            else:
                self.logger.warning("NDK toolchain file not found")

        return args

    def get_build_args(self, cmake_path: str, build_dir: Path) -> list:
        return [
            cmake_path,
            "--build",
            str(build_dir),
            "--config",
            self.build_type.capitalize(),
        ]

    def get_target_library_name(self) -> Optional[str]:
        return self.target_lib_name

    def get_build_type(self) -> str:
        return self.build_type

    def get_target_abi(self) -> str:
        return self.target_abi
