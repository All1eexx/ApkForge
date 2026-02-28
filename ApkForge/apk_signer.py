# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : apk_signer.py
# Purpose : Signs APK using apksigner and zipalign.
# =============================================================================

import platform
import shutil
from pathlib import Path
from typing import Tuple

from config import KeystoreConfig
from platform_utils import run_command, setup_utf8_environment, run_java_tool


class ApkSigner:
    def __init__(self, android_sdk: Path, logger=None):
        self.android_sdk = android_sdk
        self.logger = logger
        self.system = platform.system().lower()
        setup_utf8_environment()

    def find_build_tools(self) -> Path:
        build_tools_dir = self.android_sdk / "build-tools"
        if not build_tools_dir.exists():
            raise FileNotFoundError("Android build-tools directory not found")

        build_tools_versions = self._collect_build_tools(build_tools_dir)

        if not build_tools_versions:
            raise FileNotFoundError("No build-tools versions found")

        build_tools = self._select_latest_build_tools(build_tools_versions)
        if self.logger:
            self.logger.info(f"  Using build-tools: {build_tools.name}")

        return build_tools

    @staticmethod
    def _collect_build_tools(build_tools_dir: Path):
        versions = []
        for item in build_tools_dir.iterdir():
            if item.is_dir():
                try:
                    version_parts = item.name.split(".")
                    if all(part.isdigit() for part in version_parts[:2]):
                        versions.append(item)
                except (AttributeError, ValueError):
                    pass
        return versions

    @staticmethod
    def _select_latest_build_tools(versions):
        def version_key(build_path):
            parts = build_path.name.split(".")
            try:
                return (
                    int(parts[0]) if len(parts) > 0 else 0,
                    int(parts[1]) if len(parts) > 1 else 0,
                    int(parts[2]) if len(parts) > 2 else 0,
                )
            except (ValueError, IndexError):
                return 0, 0, 0

        versions.sort(key=version_key, reverse=True)
        return versions[0]

    def locate_tools(self, build_tools: Path) -> Tuple[Path, Path]:
        zipalign = self._find_tool(
            build_tools, "zipalign", ["zipalign", "zipalign.exe", "zipalign.bat"]
        )
        apksigner = self._find_tool(
            build_tools,
            "apksigner",
            ["apksigner", "apksigner.jar", "apksigner.bat", "apksigner.sh"],
        )

        return zipalign, apksigner

    def _find_tool(self, build_tools: Path, tool_name: str, alternatives: list) -> Path:
        tool_path = build_tools / tool_name

        if not tool_path.exists():
            for alt_name in alternatives:
                alt_path = build_tools / alt_name
                if alt_path.exists():
                    tool_path = alt_path
                    break

        if not tool_path.exists():
            which_path = shutil.which(tool_name.replace(".exe", "").replace(".bat", ""))
            if which_path:
                tool_path = Path(which_path)
                if self.logger:
                    self.logger.info(f"  Found {tool_name} in PATH: {tool_path}")
            else:
                raise FileNotFoundError(f"{tool_name} not found")

        return tool_path

    def zipalign(self, zipalign: Path, input_apk: Path, output_apk: Path):
        if self.logger:
            self.logger.info("  Zipaligning APK...")

        cmd = [
            str(zipalign),
            "-f",
            "-p",
            "4",
            str(input_apk),
            str(output_apk),
        ]

        result = run_command(cmd)
        self._check_result(result, "zipalign")

        if self.logger:
            self.logger.info("  [OK] APK zipaligned")

    def sign(self, apksigner: Path, input_apk: Path, output_apk: Path, keystore: KeystoreConfig):
        if self.logger:
            self.logger.info("  Signing APK...")

        sign_cmd = self._build_command(apksigner, input_apk, output_apk, keystore)

        run_java_tool(sign_cmd, "APK signing failed", "apksigner")

        if self.logger:
            self.logger.info("  [OK] APK signed successfully")

    def verify(self, apksigner: Path, signed_apk: Path):
        if self.logger:
            self.logger.info("  Verifying APK signature...")

        verify_cmd = self._build_verify_command(apksigner, signed_apk)

        run_java_tool(verify_cmd, "APK verification failed", "apksigner")

        if self.logger:
            self.logger.info("  [OK] APK signature verified")

    @staticmethod
    def _build_command(apksigner: Path, input_apk: Path, output_apk: Path, keystore: KeystoreConfig) -> list:
        base_cmd = (
            ["java", "-jar", str(apksigner)]
            if apksigner.suffix == ".jar"
            else [str(apksigner)]
        )

        sign_args = [
            "sign",
            "--ks", str(keystore.path),
            "--ks-key-alias", keystore.alias,
            "--ks-pass", f"pass:{keystore.password}",
            "--key-pass", f"pass:{keystore.key_password}",
            "--v1-signing-enabled", "true",
            "--v2-signing-enabled", "true",
            "--v3-signing-enabled", "true",
            "--v4-signing-enabled", "true",
            "--out", str(output_apk),
            str(input_apk),
        ]

        return base_cmd + sign_args

    @staticmethod
    def _build_verify_command(apksigner: Path, signed_apk: Path) -> list:
        if apksigner.suffix == ".jar":
            return [
                "java", "-jar", str(apksigner),
                "verify", "--verbose", "--print-certs", str(signed_apk)
            ]
        else:
            return [
                str(apksigner),
                "verify", "--verbose", "--print-certs", str(signed_apk)
            ]

    @staticmethod
    def _check_result(result, step_name):
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout
            if error_msg and len(error_msg) > 500:
                error_msg = error_msg[:500] + "..."
            raise RuntimeError(f"{step_name} failed: {error_msg}")