# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : cmake_builder.py
# Purpose : Wrapper for CMake commands. Handles CMake configuration and build
#           processes for native C++ libraries.
# =============================================================================

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from native_build_config import NativeBuildConfig


class CMakeBuilder:
    def __init__(
            self, cmake_path: str, ninja_path: str, logger: Optional[logging.Logger] = None
    ):
        self.cmake_path = cmake_path
        self.ninja_path = ninja_path
        self.logger = logger or logging.getLogger(__name__)

    def configure(self, build_dir: Path, config: NativeBuildConfig):
        self.logger.info("\nConfiguring CMake project...")

        args = config.get_cmake_args(self.cmake_path, self.ninja_path, build_dir)

        self.logger.info(f"  Build type: {config.get_build_type()}")
        self.logger.info(f"  Target ABI: {config.get_target_abi()}")

        if config.target_lib_name:
            self.logger.info(f"  Target library: {config.target_lib_name}")

        try:
            result = self._run_command(args, cwd=build_dir)
            self._log_output(result.stdout, is_error=False)
        except subprocess.CalledProcessError as e:
            self.logger.error("CMake configuration failed")
            self._log_output(e.stderr, is_error=True)
            raise RuntimeError("CMake configuration failed") from e

    def build(self, build_dir: Path, config: NativeBuildConfig):
        self.logger.info("\nBuilding with Ninja...")

        args = config.get_build_args(self.cmake_path, build_dir)

        try:
            result = self._run_command(args, cwd=build_dir)
            self._log_output(result.stdout, is_error=False)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Build failed with code {e.returncode}")

            self.logger.error("\n" + "=" * 50)
            self.logger.error("COMPLETE BUILD ERROR OUTPUT:")
            self.logger.error("=" * 50)

            if e.stderr:
                for line in e.stderr.strip().split("\n"):
                    self.logger.error(f"  {line}")

            if e.stdout and not e.stderr:
                for line in e.stdout.strip().split("\n")[-50:]:
                    self.logger.error(f"  {line}")

            self.logger.error("=" * 50)
            raise RuntimeError(f"Build failed with code {e.returncode}") from e

    def _run_command(self, cmd: list, cwd: Path) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["LC_ALL"] = "C.UTF-8"

        cmd_str = " ".join(str(c) for c in cmd[:5])
        if len(cmd) > 5:
            cmd_str += "..."
        self.logger.debug(f"Running: {cmd_str}")

        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )

        return result

    def _log_output(self, output: str, is_error: bool = False):
        if not output:
            return

        lines = [line for line in output.strip().split("\n") if line.strip()]

        if not lines:
            return

        for line in lines:
            if is_error:
                self.logger.error(f"  {line}")
            else:
                self.logger.info(f"  {line}")
