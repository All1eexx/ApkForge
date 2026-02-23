# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : platform_utils.py
# Purpose : Cross-platform utilities for path handling, executable finding,
#           and UTF-8 environment setup.
# =============================================================================

import os
import platform
import shutil
import sys
from pathlib import Path

UTF8_LOCALE = "C.UTF-8"
UTF8_ENCODING = "utf-8"
ENCODING_ERROR_HANDLER = "replace"


def get_platform_info():
    system = platform.system()
    release = platform.release()
    arch = platform.machine()
    python_version = platform.python_version()

    return {
        "system": system,
        "release": release,
        "arch": arch,
        "python_version": python_version,
        "is_windows": system == "Windows",
        "is_linux": system == "Linux",
        "is_mac": system == "Darwin",
        "is_unix": system in ["Linux", "Darwin", "FreeBSD", "OpenBSD", "NetBSD"],
    }


def _get_platform_extensions():
    plat_info = get_platform_info()

    if plat_info["is_windows"]:
        return ["", ".exe", ".bat", ".cmd", ".ps1"]
    elif plat_info["is_unix"]:
        return ["", ".sh", ".bash"]

    return [""]


def _search_in_paths(name, extensions, search_paths):
    for search_path in search_paths:
        if isinstance(search_path, str):
            search_path = Path(search_path)

        if search_path.exists():
            for ext in extensions:
                exe_file = search_path / (name + ext)
                if exe_file.exists():
                    return str(exe_file)

    return None


def find_executable(name, additional_paths=None):
    name = str(name)

    exe_path = shutil.which(name)
    if exe_path:
        return exe_path

    extensions = _get_platform_extensions()

    for ext in extensions:
        exe_path = shutil.which(name + ext)
        if exe_path:
            return exe_path

    if additional_paths:
        return _search_in_paths(name, extensions, additional_paths)

    return None


def get_temp_dir():
    temp_dir = (
            Path(os.environ.get("TEMP", ""))
            or Path(os.environ.get("TMP", ""))
            or Path("/tmp")
            or Path.home() / "tmp"
    )

    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def normalize_path(path):
    if isinstance(path, str):
        path = Path(path)
    path = path.expanduser().resolve()

    if platform.system() == "Windows":
        return Path(str(path).replace("/", "\\"))
    else:
        return Path(str(path).replace("\\", "/"))


def run_command(cmd, **kwargs):
    import subprocess

    if isinstance(cmd, (list, tuple)):
        cmd = [str(c) for c in cmd]
    else:
        cmd = str(cmd)

    defaults = {
        "capture_output": True,
        "text": True,
        "encoding": UTF8_ENCODING,
        "errors": ENCODING_ERROR_HANDLER,
        "shell": False,
        "env": os.environ.copy(),
    }

    defaults["env"]["PYTHONIOENCODING"] = UTF8_ENCODING
    defaults["env"]["LC_ALL"] = UTF8_LOCALE

    for key, value in defaults.items():
        if key not in kwargs:
            kwargs[key] = value

    try:
        return subprocess.run(cmd, **kwargs)
    except FileNotFoundError as e:
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        raise RuntimeError(f"Command not found: {cmd_str}\nError: {e}") from e
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"Failed to run command: {e}") from e


def setup_utf8_environment():
    os.environ["PYTHONIOENCODING"] = UTF8_ENCODING
    os.environ["LC_ALL"] = UTF8_LOCALE
    os.environ["LANG"] = UTF8_LOCALE

    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(
                encoding=UTF8_ENCODING, errors=ENCODING_ERROR_HANDLER
            )
    except (AttributeError, OSError):
        pass

    try:
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(
                encoding=UTF8_ENCODING, errors=ENCODING_ERROR_HANDLER
            )
    except (AttributeError, OSError):
        pass


def run_command_checked(cmd, error_prefix: str):
    result = run_command(cmd)
    if result.returncode != 0:
        error_msg = result.stderr if result.stderr else result.stdout
        if error_msg and len(error_msg) > 500:
            error_msg = error_msg[:500] + "..."
        raise RuntimeError(f"{error_prefix}: {error_msg}")
    return result


def create_arg_file(args, prefix: str = "args") -> "Path":
    import os
    import tempfile
    import time

    temp_dir = Path(tempfile.gettempdir())
    argfile = temp_dir / f"{prefix}_{os.getpid()}_{int(time.time() * 1000)}.txt"

    with open(argfile, "w", encoding="utf-8", newline="\n") as f:
        for arg in args:
            if isinstance(arg, Path):
                arg = str(arg.resolve())
            arg_str = str(arg)
            arg_str = arg_str.replace("\\", "\\\\")
            arg_str = arg_str.replace('"', '\\"')
            if " " in arg_str:
                arg_str = f'"{arg_str}"'
            f.write(f"{arg_str}\n")

    return argfile


def cleanup_arg_file(argfile: "Path"):
    if argfile.exists():
        try:
            argfile.unlink()
        except OSError:
            pass


def run_compiler_with_args(compiler_path, args, file_count, compiler_name, logger=None):
    if logger:
        logger.info(f"    Compiling {file_count} {compiler_name} files...")

    argfile = create_arg_file(args, prefix=f"{compiler_name.lower()}_args")

    try:
        cmd = [compiler_path, f"@{argfile}"]
        result = run_command(cmd)

        if result.returncode != 0:
            error_msg = format_compiler_error(result, compiler_name)
            raise RuntimeError(error_msg)

        return result

    finally:
        cleanup_arg_file(argfile)


def format_compiler_error(result, compiler_name):
    error_msg = f"{compiler_name} compilation failed (code: {result.returncode})\n"

    if result.stderr:
        error_lines = result.stderr.strip().split("\n")
        for i, line in enumerate(error_lines[:20]):
            if line.strip():
                error_msg += f"  [{i + 1}] {line.strip()}\n"

    return error_msg
