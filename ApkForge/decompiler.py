# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : decompiler.py
# Purpose : Decompiles APK using apktool and prepares the directory structure.
# =============================================================================

import shutil
import subprocess
from pathlib import Path


class Decompiler:
    MAX_ERROR_OUTPUT_LENGTH = 500
    LAST_LINES_TO_SHOW = 3

    def __init__(self, apktool_jar: Path, source_apk: Path, output_dir: Path):
        self.apktool_jar = apktool_jar
        self.source_apk = source_apk
        self.output_dir = output_dir

    @staticmethod
    def _run_command(cmd):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
            )
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to run command {' '.join(cmd)}: {e}")

    def decompile(self):
        print("  Running apktool...")
        self._prepare_output_directory()

        cmd = self._build_command()
        print(f"  Command: {' '.join(cmd)}")

        result = self._run_command(cmd)
        self._check_result(result)
        self._print_output(result)

    def _prepare_output_directory(self):
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir, ignore_errors=True)

    def _build_command(self):
        return [
            "java",
            "-jar",
            str(self.apktool_jar),
            "d",
            "-f",
            str(self.source_apk),
            "-o",
            str(self.output_dir),
        ]

    def _check_result(self, result):
        if result.returncode != 0:
            error_output = self._get_error_output(result)
            error_output = self._truncate_error(error_output)
            raise RuntimeError(
                f"Apktool failed with code {result.returncode}:\n{error_output}"
            )

    @staticmethod
    def _get_error_output(result):
        error_output = result.stderr if result.stderr else result.stdout
        return error_output if error_output else "No error output"

    def _truncate_error(self, error_output):
        if len(error_output) > self.MAX_ERROR_OUTPUT_LENGTH:
            return error_output[: self.MAX_ERROR_OUTPUT_LENGTH] + "..."
        return error_output

    def _print_output(self, result):
        if not result.stdout:
            return

        lines = result.stdout.strip().split("\n")
        last_lines = self._get_last_lines(lines)

        for line in last_lines:
            if line.strip():
                print(f"    {line.strip()}")

    def _get_last_lines(self, lines):
        if len(lines) > self.LAST_LINES_TO_SHOW:
            return lines[-self.LAST_LINES_TO_SHOW:]
        return lines