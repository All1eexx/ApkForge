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

from platform_utils import setup_utf8_environment, run_java_tool


class DexConverter:
    def __init__(self, android_sdk: Path, logger=None):
        self.android_sdk = android_sdk
        self.logger = logger
        self.system = platform.system().lower()
        setup_utf8_environment()

    def find_d8(self) -> str:
        if self.logger:
            self.logger.info("    Searching for D8/DX compiler...")

        build_tools_dir = self._find_build_tools_dir()
        if build_tools_dir is None:
            self._raise_build_tools_not_found()
            return ""

        build_tools_version = self._get_latest_build_tools(build_tools_dir)

        d8_jar = self._try_find_d8_jar(build_tools_version)
        if d8_jar is not None:
            return d8_jar

        d8_executable = self._try_find_d8_executable(build_tools_version)
        if d8_executable is not None:
            return d8_executable

        self._raise_d8_not_found(build_tools_version)
        return ""

    def _find_build_tools_dir(self) -> Optional[Path]:
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

    def _raise_build_tools_not_found(self):
        raise FileNotFoundError(
            "Android build-tools not found. Please install Android SDK build-tools.\n"
            "Make sure ANDROID_HOME or ANDROID_SDK_ROOT is set correctly."
        )

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
    def _parse_version(version_str: str) -> tuple:
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

    def _get_latest_build_tools(self, build_tools_dir: Path) -> Path:
        versions = self._collect_build_tools_versions(build_tools_dir)

        if not versions:
            raise FileNotFoundError(f"No build-tools versions found in {build_tools_dir}")

        versions.sort(key=lambda x: self._parse_version(x.name), reverse=True)
        latest = versions[0]

        if self.logger:
            self.logger.info(f"    Using build-tools: {latest.name}")

        return latest

    def _try_find_d8_jar(self, build_tools_version: Path) -> Optional[str]:
        d8_jar = build_tools_version / "d8.jar"
        if d8_jar.exists():
            if self.logger:
                self.logger.info("    Found d8.jar")
            return str(d8_jar)
        return None

    def _get_d8_candidates(self) -> List[str]:
        if self.system == "windows":
            return ["d8.bat", "d8.cmd", "d8.exe", "d8", "dx.bat", "dx.cmd", "dx.exe", "dx"]
        else:
            return ["d8", "dx"]

    def _try_find_d8_executable(self, build_tools_version: Path) -> Optional[str]:
        candidates = self._get_d8_candidates()

        for candidate in candidates:
            tool_path = build_tools_version / candidate
            if tool_path.exists():
                if self.logger:
                    self.logger.info(f"    Found: {candidate}")
                return str(tool_path)

        return None

    def _raise_d8_not_found(self, build_tools_version: Path):
        raise FileNotFoundError(
            f"D8/DX not found in {build_tools_version}\n"
            "Please ensure Android SDK build-tools are properly installed."
        )

    def convert_to_dex(self, combined_jar: Path, android_jar: Path, output_dir: Path, min_api: int = 21) -> List[Path]:
        if self.logger:
            self.logger.info("  Converting combined JAR to DEX...")

        d8_path = self.find_d8()
        cmd = self._build_d8_command(d8_path, combined_jar, android_jar, output_dir, min_api)

        run_java_tool(cmd, "D8 dex conversion failed", "d8")

        dex_files = list(output_dir.glob("*.dex"))
        if not dex_files:
            raise RuntimeError("No DEX files generated")

        if self.logger:
            self.logger.info(f"    Generated {len(dex_files)} DEX files")
            for dex in dex_files:
                size = dex.stat().st_size / 1024
                self.logger.info(f"      - {dex.name} ({size:.2f} KB)")

        return dex_files

    def _build_d8_command(self, d8_path: str, combined_jar: Path, android_jar: Path,
                          output_dir: Path, min_api: int) -> List[str]:
        base_args = [str(combined_jar), '--lib', str(android_jar),
                     '--output', str(output_dir), '--min-api', str(min_api)]

        if d8_path.endswith('.jar'):
            return ['java', '-jar', d8_path] + base_args
        elif self.system == "windows":
            if d8_path.endswith('.bat') or d8_path.endswith('.cmd'):
                return ['cmd', '/c', d8_path] + base_args
            else:
                return [d8_path] + base_args
        else:
            return [d8_path] + base_args