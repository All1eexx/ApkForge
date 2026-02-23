# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : dex_converter.py
# Purpose : Converts JAR files to DEX format using d8/dx.
# =============================================================================

import os
import platform
from pathlib import Path
from typing import List, Optional

from platform_utils import run_command_checked, setup_utf8_environment


class DexConverter:
    def __init__(self, android_sdk: Path, logger=None):
        self.android_sdk = android_sdk
        self.logger = logger
        self.system = platform.system().lower()
        setup_utf8_environment()

    def find_d8(self) -> Optional[str]:
        if self.logger:
            self.logger.info("    Searching for D8/DX compiler...")

        build_tools_dir = self._find_build_tools()

        if not build_tools_dir:
            raise FileNotFoundError(
                "Android build-tools not found. Please install Android SDK build-tools:\n"
                "1. Open Android Studio → SDK Manager → SDK Tools\n"
                "2. Install 'Android SDK Build-Tools'\n"
                "3. Set ANDROID_HOME environment variable"
            )

        build_tools_versions = self._collect_build_tools_versions(build_tools_dir)

        if not build_tools_versions:
            raise FileNotFoundError(f"No build-tools versions found in {build_tools_dir}")

        build_tools_version = self._select_latest_build_tools(build_tools_versions)
        if self.logger:
            self.logger.info(f"    Using build-tools: {build_tools_version.name}")

        return self._locate_d8_tool(build_tools_version)

    def _find_build_tools(self) -> Optional[Path]:
        if self.android_sdk and self.android_sdk.exists():
            build_tools = self.android_sdk / "build-tools"
            if build_tools.exists():
                return build_tools

        env_paths = [
            os.environ.get("ANDROID_HOME"),
            os.environ.get("ANDROID_SDK_ROOT"),
        ]

        for env_path in env_paths:
            if env_path:
                test_path = Path(env_path) / "build-tools"
                if test_path.exists():
                    return test_path

        return None

    @staticmethod
    def _collect_build_tools_versions(build_tools_dir: Path) -> List[Path]:
        versions = []
        for item in build_tools_dir.iterdir():
            if item.is_dir():
                try:
                    version_parts = item.name.split(".")
                    if len(version_parts) >= 2 and all(
                            p.isdigit() for p in version_parts[:2]
                    ):
                        versions.append(item)
                except (AttributeError, ValueError):
                    continue
        return versions

    @staticmethod
    def _select_latest_build_tools(versions: List[Path]) -> Path:
        def parse_version(version_str):
            version_components = version_str.split(".")
            version_nums = []

            for component in version_components[:3]:
                try:
                    version_nums.append(int(component))
                except ValueError:
                    version_nums.append(0)

            while len(version_nums) < 3:
                version_nums.append(0)

            return tuple(version_nums)

        versions.sort(key=lambda x: parse_version(x.name), reverse=True)
        return versions[0]

    def _locate_d8_tool(self, build_tools_version: Path) -> str:
        tool_names = self._get_d8_tool_names()

        for tool_name in tool_names:
            tool_path = build_tools_version / tool_name
            if tool_path.exists():
                if self.logger:
                    self.logger.info(f"    Found: {tool_name}")
                return str(tool_path)

        raise FileNotFoundError(f"D8/DX not found in {build_tools_version}")

    def _get_d8_tool_names(self) -> List[str]:
        if self.system == "windows":
            return [
                "d8.bat",
                "d8.cmd",
                "d8.exe",
                "d8",
                "dx.bat",
                "dx.cmd",
                "dx.exe",
                "dx",
            ]
        else:
            return ["d8", "dx"]

    def convert_to_dex(self, combined_jar: Path, android_jar: Path, output_dir: Path, min_api: int = 21) -> List[Path]:
        if self.logger:
            self.logger.info("  Converting combined JAR to DEX...")

        d8_path = self.find_d8()

        cmd = [
            d8_path,
            str(combined_jar),
            "--lib",
            str(android_jar),
            "--output",
            str(output_dir),
            "--min-api",
            str(min_api),
        ]

        run_command_checked(cmd, "D8 dex conversion failed")

        if self.logger:
            self.logger.info("    DEX conversion completed")

        dex_files = list(output_dir.glob("*.dex"))
        if not dex_files:
            raise RuntimeError("No DEX files generated")

        if self.logger:
            self.logger.info(f"    Found {len(dex_files)} DEX file(s)")

        return dex_files