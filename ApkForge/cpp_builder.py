# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : cpp_builder.py
# Purpose : Builds native C++ libraries using CMake.
# =============================================================================

import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from cmake_builder import CMakeBuilder
from library_deployer import LibraryDeployer
from native_build_config import NativeBuildConfig
from tool_finder import ToolFinder


class NativeBuilder:
    def __init__(
            self,
            paths: Dict[str, Path],
            config: Optional[dict] = None,
            cmakelists_path: Optional[Path] = None,
            logger: Optional[logging.Logger] = None,
    ):
        self.paths = paths
        self.project_root = paths["project_root"]
        self.config = config or {}
        self.cmakelists_path = cmakelists_path
        self.logger = logger or self._setup_logger()

        if not self.cmakelists_path:
            raise ValueError("cmakelists_path is required for NativeBuilder")

        self.cpp_dir = self.cmakelists_path.parent

        self.build_success = False
        self.build_summary = {}
        self.changed_values = []

    @staticmethod
    def _setup_logger() -> logging.Logger:
        logger = logging.getLogger("NativeBuilder")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("  %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _check_prerequisites(self) -> Tuple[bool, Optional[str], Optional[str], Optional[Path]]:
        if not self.cmakelists_path or not self.cmakelists_path.exists():
            self.logger.error(f"CMakeLists.txt not found at {self.cmakelists_path}")
            return False, None, None, None

        self.logger.info(f"Using CMakeLists.txt: {self.cmakelists_path}")

        tool_finder = ToolFinder(self.paths["android_sdk"], self.logger)

        cmake_path = tool_finder.find_cmake()
        ninja_path = tool_finder.find_ninja()

        if not cmake_path:
            self.logger.error("CMake not found. Please install CMake")
            return False, None, None, None

        if not ninja_path:
            self.logger.error("Ninja not found. Please install Ninja")
            return False, None, None, None

        self.logger.info(f"Using CMake: {cmake_path}")
        self.logger.info(f"Using Ninja: {ninja_path}")

        ndk_path = tool_finder.find_ndk()

        if ndk_path:
            self.logger.info(f"Using NDK: {ndk_path.name}")
        else:
            self.logger.info("NDK not found - building for host system only")

        return True, cmake_path, ninja_path, ndk_path

    @staticmethod
    def _get_target_abis() -> List[str]:
        from project_config import get_config

        config = get_config()

        if hasattr(config, "build_abis") and config.build_abis:
            return config.build_abis
        return config.abi_keep_only if config.abi_keep_only else ["arm64-v8a"]

    @staticmethod
    def _prepare_build_directory(cpp_dir: Path, abi: str) -> Path:
        abi_build_dir = cpp_dir / f"build_{abi}"
        if abi_build_dir.exists():
            shutil.rmtree(abi_build_dir, ignore_errors=True)
        abi_build_dir.mkdir(parents=True, exist_ok=True)
        return abi_build_dir

    def _build_single_abi(
            self, abi: str, cmake_path: str, ninja_path: str, ndk_path: Path
    ) -> bool:
        self.logger.info(f"\n{'=' * 40}")
        self.logger.info(f"Building for ABI: {abi}")
        self.logger.info(f"{'=' * 40}")

        abi_build_dir = self._prepare_build_directory(self.cpp_dir, abi)

        abi_config = NativeBuildConfig(
            self.cpp_dir, self.project_root, ndk_path, self.logger
        )
        abi_config.target_abi = abi

        builder = CMakeBuilder(cmake_path, ninja_path, self.logger)

        try:
            builder.configure(abi_build_dir, abi_config)
            builder.build(abi_build_dir, abi_config)

            deployer = LibraryDeployer(self.paths["modded_dir"], self.logger)
            lib_files = deployer.find_built_libraries(
                abi_build_dir, abi_config.get_target_library_name()
            )

            if lib_files:
                deployer.deploy_libraries(lib_files)
                self.logger.info(f"[OK] Successfully built for {abi}")
                return True
            else:
                self.logger.warning(f"[ERROR] No libraries found for {abi}")
                return False

        except Exception as e:
            self.logger.error(f"\n{'=' * 50}")
            self.logger.error(f"FAILED TO BUILD FOR {abi}")
            self.logger.error(f"{'=' * 50}")
            self.logger.error(str(e))
            if hasattr(e, 'stderr'):
                self.logger.error("\nCompiler output:")
                self.logger.error(e.stderr)

            return False

    def _update_build_summary(self, target_abis: List[str], success_count: int):
        if success_count > 0:
            self.build_success = True
            self.build_summary["native_build"] = (
                f"Success for {success_count}/{len(target_abis)} ABIs"
            )
            self.changed_values.append(
                {
                    "Name": "Native Libraries",
                    "Old": "Not built",
                    "New": f"Built for {', '.join(target_abis[:success_count])}",
                }
            )
            self.logger.info(
                f"\n[OK] Native libraries built successfully for {success_count} ABIs"
            )
        else:
            self.logger.warning("\n[ERROR] No libraries built successfully")

    def build(self) -> Optional[Path]:
        self.logger.info("\nBuilding native libraries...")

        prerequisites_ok, cmake_path, ninja_path, ndk_path = self._check_prerequisites()
        if not prerequisites_ok:
            return None

        target_abis = self._get_target_abis()
        self.logger.info(f"Target ABIs for compilation: {', '.join(target_abis)}")

        success_count = 0
        failed_abis = []

        for abi in target_abis:
            if self._build_single_abi(abi, cmake_path, ninja_path, ndk_path):
                success_count += 1
            else:
                failed_abis.append(abi)

        self._update_build_summary(target_abis, success_count)

        if success_count == 0 and target_abis:
            error_msg = f"Native build failed for all ABIs: {', '.join(failed_abis)}"
            self.logger.error(f"\n[ERROR] {error_msg}")
            raise RuntimeError(error_msg)

        if failed_abis and success_count > 0:
            self.logger.warning(
                f"\n[WARNING] Native build failed for some ABIs: {', '.join(failed_abis)}"
            )

        return self.cpp_dir / "build"