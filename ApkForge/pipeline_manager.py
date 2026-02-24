# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : pipeline_manager.py
# Purpose : Manages dynamic pipeline execution of ApkForge methods and any
#           function/method from any .py file with optional arguments.
# =============================================================================

import ast
import importlib
import inspect
import json
import re
import threading
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


class TimeoutInput:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.user_input = None
        self.input_received = False

    def get_input(self):
        try:
            self.user_input = input().lower().strip()
            self.input_received = True
        except Exception as e:
            print(f"\n[ERROR] Input handler error: {type(e).__name__}: {e}")


def ask_continue_with_timeout(timeout: int = 30) -> bool:
    print(
        f"\nContinue pipeline? (y/n) - Auto-continue in {timeout}s: ",
        end="",
        flush=True,
    )

    handler = TimeoutInput(timeout)
    thread = threading.Thread(target=handler.get_input)
    thread.daemon = True
    thread.start()

    for i in range(timeout):
        if handler.input_received:
            break
        time.sleep(1)
        remaining = timeout - i - 1
        if remaining > 0 and not handler.input_received:
            print(
                f"\rContinue pipeline? (y/n) - Auto-continue in {remaining}s: ",
                end="",
                flush=True,
            )

    print()

    if not handler.input_received:
        print(f"[INFO] Timeout reached ({timeout}s), continuing automatically...")
        return True

    return handler.user_input in ("y", "yes")


class StepStatus(Enum):
    PENDING = "[.]"
    RUNNING = "[>]"
    SUCCESS = "[OK]"
    FAILED = "[ERROR]"
    SKIPPED = "[-]"


class PipelineStep:
    def __init__(self, raw: str):
        self.raw = raw
        self.status = StepStatus.PENDING
        self.duration = 0.0
        self.error: Optional[str] = None
        self.start_time: Optional[float] = None

    @property
    def display_name(self) -> str:
        return self.raw.split("(")[0].strip()


class PipelineManager:
    def __init__(self, build_tool):
        self.build_tool = build_tool
        self._module_cache: Dict[str, Any] = {}
        self._instance_cache: Dict[str, Any] = {}
        self.results: List[Dict[str, Any]] = []

        raw_config = (
                getattr(getattr(build_tool, "config", None), "raw_config", {}) or {}
        )
        self.pipeline_config: Dict[str, Any] = raw_config.get(
            "pipeline_behavior",
            {"stop_on_error": True, "stop_on_warning": False, "timeout_seconds": 30},
        )

    def run(self, step_strings: List[str]) -> bool:
        print("\n" + "=" * 60)
        print("   PIPELINE EXECUTION")
        print("=" * 60)
        print(f"   Steps total: {len(step_strings)}")
        print("=" * 60)

        self.results = []
        overall_success = True
        total = len(step_strings)

        for i, raw_step in enumerate(step_strings, 1):
            step = PipelineStep(raw_step)
            print(f"\n[{i}/{total}] {step.display_name}")

            keep_going = self._execute_step(step)

            if step.status == StepStatus.FAILED:
                overall_success = False

            if not keep_going:
                print("\n[INFO] Pipeline stopped.")
                break

        self._print_summary()
        return overall_success

    def list_available_steps(self) -> List[str]:
        return sorted(
            name
            for name in dir(self.build_tool)
            if not (name.startswith("__") and name.endswith("__"))
            and callable(getattr(self.build_tool, name))
        )

    def save_report(self, report_path: Path):
        success_count = sum(1 for r in self.results if r["status"] == "success")
        failed_count = sum(1 for r in self.results if r["status"] == "failed")

        report = {
            "timestamp": datetime.now().isoformat(),
            "results": self.results,
            "total_time": sum(r.get("duration", 0) for r in self.results),
            "success_count": success_count,
            "failed_count": failed_count,
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Report saved to: {report_path}")

    def _execute_step(self, step: PipelineStep) -> bool:
        step.status = StepStatus.RUNNING
        step.start_time = time.time()

        try:
            func, args, kwargs = self._parse_step(step.raw)
            func(*args, **kwargs)

            has_warnings = (
                    hasattr(self.build_tool, "has_warnings")
                    and self.build_tool.has_warnings()
            )

            step.duration = time.time() - step.start_time

            if has_warnings and self.pipeline_config.get("stop_on_warning", False):
                if hasattr(self.build_tool, "_warnings_occurred"):
                    self.build_tool._warnings_occurred = False
                return self._on_step_error(
                    step, Exception("Step completed with warnings"), is_warning=True
                )

            step.status = StepStatus.SUCCESS
            self.results.append(
                {
                    "step": step.display_name,
                    "status": "success",
                    "duration": step.duration,
                }
            )
            print(f"  [OK] Completed in {step.duration:.2f}s")
            return True

        except Warning as w:
            step.duration = time.time() - step.start_time
            return self._on_step_error(step, w, is_warning=True)

        except Exception as e:
            step.duration = time.time() - step.start_time
            return self._on_step_error(step, e, is_warning=False)

    def _on_step_error(
            self, step: PipelineStep, error: Exception, is_warning: bool
    ) -> bool:
        step.status = StepStatus.FAILED
        step.error = str(error)

        if is_warning:
            print(f"  [WARNING] {error}")
        else:
            print(f"  [ERROR] {error}")

        self.results.append(
            {
                "step": step.display_name,
                "status": "failed",
                "error": str(error),
                "duration": step.duration,
            }
        )

        stop_key = "stop_on_warning" if is_warning else "stop_on_error"
        if self.pipeline_config.get(stop_key, True):
            timeout = self.pipeline_config.get("timeout_seconds", 30)
            if not ask_continue_with_timeout(timeout):
                print("\n[INFO] Pipeline stopped by user.")
                return False
        else:
            label = "warning" if is_warning else "error"
            print(
                f"  [INFO] Continuing despite {label} (configured in pipeline_behavior)."
            )

        return True

    def _parse_step(self, step_str: str) -> Tuple[Callable, list, dict]:
        step_str = step_str.strip()

        name, args_str = self._split_name_and_args(step_str)

        args, kwargs = self._parse_args(args_str) if args_str is not None else ([], {})

        func = self._resolve_callable(name)

        return func, args, kwargs

    @staticmethod
    def _split_name_and_args(step_str: str) -> Tuple[str, Optional[str]]:
        match = re.match(
            r"^(?P<name>[^(]+?)(?:\((?P<args>.*)\))?$", step_str, re.DOTALL
        )
        if not match:
            raise ValueError(f"Cannot parse step string: '{step_str}'")

        name = match.group("name").strip()
        args_str = match.group("args")

        return name, args_str

    @staticmethod
    def _parse_args(args_str: str) -> Tuple[list, dict]:
        args_str = args_str.strip()

        if not args_str:
            return [], {}

        try:
            tree = ast.parse(f"_f({args_str})", mode="eval")
            call = tree.body
            if not isinstance(call, ast.Call):
                raise ValueError("Parsed expression is not a function call.")

            args = [ast.literal_eval(a) for a in call.args]
            kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in call.keywords}

            return args, kwargs

        except Exception as e:
            raise ValueError(
                f"Cannot parse arguments '{args_str}': {e}\n"
                f"Only literal values are supported: strings, numbers, booleans, None, lists, dicts."
            )

    def _resolve_callable(self, name: str) -> Callable:
        parts = name.split(".")

        if len(parts) == 1:
            return self._resolve_build_tool_method(name)

        if len(parts) == 2:
            module_name, attr_name = parts
            module = self._import_module(module_name)
            attr = self._getattr_or_raise(module, attr_name, module_name)

            if inspect.isclass(attr):
                raise ValueError(
                    f"'{name}' is a class, not callable directly.\n"
                    f"Use '{module_name}.{attr_name}.method_name' to call a method."
                )

            if callable(attr):
                return attr

            raise TypeError(f"'{name}' is not callable (type: {type(attr).__name__})")

        if len(parts) == 3:
            module_name, class_name, method_name = parts
            module = self._import_module(module_name)
            cls = self._getattr_or_raise(module, class_name, module_name)

            if not inspect.isclass(cls):
                raise TypeError(f"'{module_name}.{class_name}' is not a class.")

            instance = self._get_or_create_instance(cls, class_name)
            method = self._getattr_or_raise(instance, method_name, class_name)

            if not callable(method):
                raise TypeError(f"'{class_name}.{method_name}' is not callable.")

            return method

        raise ValueError(
            f"Too many dots in '{name}'. "
            f"Maximum supported depth is 'module.ClassName.method'."
        )

    def _resolve_build_tool_method(self, name: str) -> Callable:
        method = getattr(self.build_tool, name, None)

        if method is None:
            all_methods = self.list_available_steps()
            similar = [m for m in all_methods if name.lower() in m.lower()]
            hint = ""
            if similar:
                hint = f"\n  Did you mean one of: {', '.join(similar[:5])}"
            raise AttributeError(
                f"Method '{name}' not found on ApkForge.{hint}\n"
                f"  For functions in other files use: 'module_name.function_name'"
            )

        if not callable(method):
            raise TypeError(f"'{name}' exists on ApkForge but is not callable.")

        return method

    def _get_or_create_instance(self, cls, class_name: str) -> Any:
        if class_name in self._instance_cache:
            return self._instance_cache[class_name]

        instance = self._auto_create_instance(cls, class_name)
        self._instance_cache[class_name] = instance
        return instance

    def _auto_create_instance(self, cls, class_name: str) -> Any:

        try:
            sig = inspect.signature(cls.__init__)
            params = [
                p
                for name, p in sig.parameters.items()
                if name != "self" and p.default is inspect.Parameter.empty
            ]
        except (ValueError, TypeError):
            params = []

        if not params:
            try:
                return cls()
            except Exception as e:
                raise RuntimeError(f"Cannot instantiate '{class_name}()': {e}")
        param_map = {
            "modded_dir": lambda: self.build_tool.paths.get("modded_dir"),
            "android_sdk": lambda: self.build_tool.paths.get("android_sdk"),
            "paths": lambda: self.build_tool.paths,
            "config": lambda: getattr(self.build_tool, "config", None),
            "logger": lambda: None,
            "apktool_jar": lambda: (
                self.build_tool.found_files.get("apktool_jar")
                if hasattr(self.build_tool, "found_files")
                else None
            ),
            "baksmali_jar": lambda: (
                self.build_tool.found_files.get("baksmali_jar")
                if hasattr(self.build_tool, "found_files")
                else None
            ),
            "source_apk": lambda: (
                self.build_tool.found_files.get("source_apk")
                if hasattr(self.build_tool, "found_files")
                else None
            ),
        }

        constructor_args = []
        for p in params:
            if p.name in param_map:
                constructor_args.append(param_map[p.name]())
            else:
                raise RuntimeError(
                    f"Cannot auto-instantiate '{class_name}'.\n"
                    f"  Unknown required parameter: '{p.name}'\n"
                    f"  Pass constructor args directly in the pipeline step:\n"
                    f"  e.g. \"module.{class_name}.method('arg1', 'arg2')\"\n"
                    f"  Or instantiate it manually and add it to the build_tool."
                )

        try:
            return cls(*constructor_args)
        except Exception as e:
            raise RuntimeError(
                f"Failed to instantiate '{class_name}' "
                f"with args {[type(a).__name__ for a in constructor_args]}: {e}"
            )

    def _import_module(self, module_name: str) -> Any:
        if module_name not in self._module_cache:
            try:
                self._module_cache[module_name] = importlib.import_module(module_name)
            except ImportError as e:
                raise ImportError(
                    f"Cannot import module '{module_name}': {e}\n"
                    f"  Make sure the file '{module_name}.py' exists and is on the Python path."
                )
        return self._module_cache[module_name]

    @staticmethod
    def _getattr_or_raise(obj: Any, attr: str, owner_name: str) -> Any:
        value = getattr(obj, attr, None)
        if value is None:
            raise AttributeError(f"'{attr}' not found in '{owner_name}'.")
        return value

    def _print_summary(self):
        print("\n" + "=" * 60)
        print("PIPELINE EXECUTION SUMMARY")
        print("=" * 60)

        total_time = sum(r.get("duration", 0) for r in self.results)
        success_count = sum(1 for r in self.results if r["status"] == "success")
        failed_count = sum(1 for r in self.results if r["status"] == "failed")

        for result in self.results:
            icon = "[OK]" if result["status"] == "success" else "[ERROR]"
            print(f"  {icon} {result['step']:<35} ({result.get('duration', 0):.2f}s)")
            if result.get("error"):
                err = result["error"]
                if len(err) > 120:
                    err = err[:120] + "..."
                print(f"       {err}")

        if self.results:
            print("-" * 60)
            print(f"  Total time : {total_time:.2f}s")
            print(
                f"  Steps      : {len(self.results)} total, "
                f"{success_count} OK, {failed_count} failed"
            )

        print("=" * 60)
