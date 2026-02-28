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
import subprocess
import time
import tempfile
import warnings
from pathlib import Path
from typing import List, Optional, Union

UTF8_LOCALE = "C.UTF-8"
UTF8_ENCODING = "utf-8"
ENCODING_ERROR_HANDLER = "replace"
WINDOWS_EXECUTABLE_EXTENSIONS = [".exe", ".bat", ".cmd", ".ps1", ""]
UNIX_EXECUTABLE_EXTENSIONS = ["", ".sh", ".bash"]


def get_platform_info():
    system = platform.system()
    release = platform.release()
    arch = platform.machine()
    python_version = platform.python_version()

    arch_map = {
        "AMD64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64",
        "i386": "x86",
        "i686": "x86",
    }

    normalized_arch = arch_map.get(arch, arch)

    return {
        "system": system,
        "release": release,
        "arch": normalized_arch,
        "python_version": python_version,
        "is_windows": system == "Windows",
        "is_linux": system == "Linux",
        "is_mac": system == "Darwin",
        "is_unix": system in ["Linux", "Darwin", "FreeBSD", "OpenBSD", "NetBSD"],
    }


def get_executable_extensions() -> List[str]:
    return (
        WINDOWS_EXECUTABLE_EXTENSIONS
        if get_platform_info()["is_windows"]
        else UNIX_EXECUTABLE_EXTENSIONS
    )


def _search_in_path(name: str, extensions: List[str], search_paths: List[Union[str, Path]]) -> Optional[str]:
    for search_path in search_paths:
        search_path = Path(search_path)
        if not search_path.exists():
            continue

        for ext in extensions:
            candidate = search_path / (name + ext)
            if candidate.exists():
                return os.path.normpath(str(candidate))
    return None


def find_executable(
        name: str, additional_paths: Optional[List[Union[str, Path]]] = None
) -> Optional[str]:
    name = str(name)

    exe_path = shutil.which(name)
    if exe_path:
        return os.path.normpath(exe_path)

    extensions = get_executable_extensions()
    for ext in extensions:
        exe_path = shutil.which(name + ext)
        if exe_path:
            return os.path.normpath(exe_path)

    if additional_paths:
        return _search_in_path(name, extensions, additional_paths)

    return None


def normalize_path(path: Union[str, Path]) -> Path:
    if isinstance(path, str):
        path = Path(path)

    path = path.expanduser().resolve()

    return path


def to_posix_path(path: Union[str, Path]) -> str:
    p = normalize_path(path)
    return str(p).replace("\\", "/")


def to_native_path(path: Union[str, Path]) -> str:
    return str(normalize_path(path))


def _get_windows_temp_candidates():
    return [
        os.environ.get("TEMP"),
        os.environ.get("TMP"),
        os.environ.get("USERPROFILE") + "\\AppData\\Local\\Temp",
        "C:\\Windows\\Temp",
    ]


def _get_unix_temp_candidates():
    return [
        os.environ.get("TMPDIR"),
        "/tmp",
        "/var/tmp",
        str(Path.home() / "tmp"),
    ]


def get_system_temp_dir() -> Path:
    candidates = (
        _get_windows_temp_candidates()
        if get_platform_info()["is_windows"]
        else _get_unix_temp_candidates()
    )

    for candidate in candidates:
        if candidate:
            path = Path(candidate)
            if path.exists() or path.parent.exists():
                path.mkdir(parents=True, exist_ok=True)
                return path

    fallback = Path.home() / ".apkforge" / "tmp"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _prepare_command_environment(cmd, kwargs):
    if isinstance(cmd, (list, tuple)):
        cmd = [str(c) for c in cmd]
    else:
        cmd = str(cmd)

    env = os.environ.copy()
    env.update(
        {
            "PYTHONIOENCODING": UTF8_ENCODING,
            "LC_ALL": UTF8_LOCALE,
            "LANG": UTF8_LOCALE,
        }
    )

    defaults = {
        "capture_output": True,
        "text": True,
        "encoding": UTF8_ENCODING,
        "errors": ENCODING_ERROR_HANDLER,
        "env": env,
        "shell": False,
    }

    if get_platform_info()["is_windows"] and isinstance(cmd, str):
        defaults["shell"] = True

    for key, value in defaults.items():
        if key not in kwargs:
            kwargs[key] = value

    return cmd, kwargs


def run_command(cmd: Union[str, List[str]], **kwargs) -> subprocess.CompletedProcess:
    cmd, kwargs = _prepare_command_environment(cmd, kwargs)

    try:
        return subprocess.run(cmd, **kwargs)
    except FileNotFoundError as e:
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        raise RuntimeError(f"Command not found: {cmd_str}\nError: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to run command: {e}") from e


def run_command_checked(cmd, error_prefix: str):
    result = run_command(cmd)
    if result.returncode != 0:
        error_msg = result.stderr if result.stderr else result.stdout
        if error_msg and len(error_msg) > 500:
            error_msg = error_msg[:500] + "..."
        raise RuntimeError(f"{error_prefix}: {error_msg}")
    return result


def _reconfigure_std_streams():
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(
                encoding=UTF8_ENCODING, errors=ENCODING_ERROR_HANDLER
            )
            sys.stderr.reconfigure(
                encoding=UTF8_ENCODING, errors=ENCODING_ERROR_HANDLER
            )
    except (AttributeError, OSError):
        try:
            sys.stdout = open(
                sys.stdout.fileno(),
                mode="w",
                encoding=UTF8_ENCODING,
                errors=ENCODING_ERROR_HANDLER,
                buffering=1,
            )
            sys.stderr = open(
                sys.stderr.fileno(),
                mode="w",
                encoding=UTF8_ENCODING,
                errors=ENCODING_ERROR_HANDLER,
                buffering=1,
            )
        except (AttributeError, OSError):
            pass


def setup_utf8_environment():
    os.environ["PYTHONIOENCODING"] = UTF8_ENCODING
    os.environ["LC_ALL"] = UTF8_LOCALE
    os.environ["LANG"] = UTF8_LOCALE

    _reconfigure_std_streams()


def _escape_arg_for_platform(arg: str) -> str:
    arg = arg.replace('"', '\\"')
    return f'"{arg}"' if " " in arg else arg


def create_arg_file(args: List[str], prefix: str = "args") -> Path:
    temp_dir = Path(tempfile.gettempdir())
    timestamp = int(time.time() * 1000)
    pid = os.getpid()
    argfile = temp_dir / f"{prefix}_{pid}_{timestamp}.txt"

    with open(argfile, "w", encoding=UTF8_ENCODING, newline="\n") as f:
        for arg in args:
            if isinstance(arg, Path):
                arg = to_native_path(arg)
            arg = str(arg)

            f.write(f"{_escape_arg_for_platform(arg)}\n")

    return argfile


def cleanup_arg_file(argfile: Path):
    try:
        if argfile.exists():
            argfile.unlink(missing_ok=True)
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


def _prepare_java_env():
    env = os.environ.copy()

    if "JAVA_HOME" in env:
        del env["JAVA_HOME"]

    java_path = shutil.which("java")
    if not java_path:
        raise RuntimeError(
            "Java not found in PATH. Please ensure Java is installed and added to PATH."
        )

    java_bin = str(Path(java_path).parent)
    env["PATH"] = java_bin + os.pathsep + env.get("PATH", "")

    return env, java_path


def run_java_tool(cmd, error_prefix: str, tool_name: str = "java"):
    env, java_path = _prepare_java_env()

    if tool_name:
        print(f"  [DEBUG] Running {tool_name} with Java from: {java_path}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding=UTF8_ENCODING,
            errors=ENCODING_ERROR_HANDLER,
            env=env,
            shell=False,
        )

        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout
            if error_msg and len(error_msg) > 500:
                error_msg = error_msg[:500] + "..."
            raise RuntimeError(f"{error_prefix}: {error_msg}")

        return result

    except FileNotFoundError as e:
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        raise RuntimeError(
            f"{error_prefix}: Command not found: {cmd_str}\nError: {e}"
        ) from e
    except Exception as e:
        raise RuntimeError(f"{error_prefix}: Failed to run command: {e}") from e


def run_d8_command(cmd, error_prefix: str):
    warnings.warn(
        "run_d8_command is deprecated. Use run_java_tool instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return run_java_tool(cmd, error_prefix, "d8")
