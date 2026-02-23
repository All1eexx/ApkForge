# =============================================================================
# ApkForge - Android APK Construction Toolkit
# =============================================================================
# Repository : https://github.com/All1eexx/ApkForge
# Author     : All1eexx
# License    : MIT License
# =============================================================================
# File    : pipeline_manager.py
# Purpose : Manages dynamic pipeline execution of ApkForge methods.
# =============================================================================

import inspect
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class TimeoutInput:
    def __init__(self, timeout=30):
        self.timeout = timeout
        self.user_input = None
        self.input_received = False

    def get_input(self):
        try:
            self.user_input = input().lower().strip()
            self.input_received = True
        except Exception as e:
            print(
                f"\n[ERROR] Unexpected error in input handler: {type(e).__name__}: {e}"
            )
            import traceback

            traceback.print_exc(limit=1)


def ask_continue_with_timeout(timeout=30):
    print(
        f"\nContinue pipeline? (y/n) - Auto-continue in {timeout}s: ",
        end="",
        flush=True,
    )

    input_handler = TimeoutInput(timeout)
    thread = threading.Thread(target=input_handler.get_input)
    thread.daemon = True
    thread.start()

    for i in range(timeout):
        if input_handler.input_received:
            break
        time.sleep(1)
        if i < timeout - 1:
            remaining = timeout - i - 1
            print(
                f"\rContinue pipeline? (y/n) - Auto-continue in {remaining}s: ",
                end="",
                flush=True,
            )

    print()

    if not input_handler.input_received:
        print(f"[INFO] Timeout reached ({timeout}s), continuing automatically...")
        return True

    return input_handler.user_input in ("y", "yes")


class StepStatus(Enum):
    PENDING = "[.]"
    RUNNING = "[>]"
    SUCCESS = "[OK]"
    FAILED = "[ERROR]"
    SKIPPED = "[-]"


class PipelineStep:
    def __init__(self, name: str, func: Callable):
        self.name = name
        self.func = func
        self.status = StepStatus.PENDING
        self.duration = 0.0
        self.error: Optional[str] = None
        self.start_time: Optional[float] = None


class PipelineManager:
    def __init__(self, build_tool):
        self.build_tool = build_tool
        self.steps: Dict[str, PipelineStep] = {}
        self.results: List[Dict[str, Any]] = []

        self.config = (
            build_tool.config.raw_config if hasattr(build_tool, "config") else {}
        )

        self._scan_build_tool_methods()

        self.pipeline_config = self.config.get(
            "pipeline_behavior",
            {"stop_on_error": True, "stop_on_warning": False, "timeout_seconds": 30},
        )

    def _scan_build_tool_methods(self):
        print("\n[Pipeline] Scanning available methods...")
        methods_found = 0

        for method_name in dir(self.build_tool):
            if method_name.startswith("__") and method_name.endswith("__"):
                continue

            method = getattr(self.build_tool, method_name)

            if inspect.ismethod(method) or inspect.isfunction(method):
                self.steps[method_name] = PipelineStep(method_name, method)
                methods_found += 1

                if methods_found <= 5:
                    print(f"  [OK] Registered: {method_name}")

        print(f"  [OK] Total {methods_found} methods available for pipeline")

    def list_available_steps(self) -> List[str]:
        return sorted(self.steps.keys())

    def get_step_info(self, step_name: str) -> Dict[str, Any]:
        if step_name not in self.steps:
            return {"error": f"Step '{step_name}' not found"}

        step = self.steps[step_name]
        doc = inspect.getdoc(step.func) or "No documentation"
        signature = str(inspect.signature(step.func))

        return {
            "name": step_name,
            "doc": doc.split("\n")[0] if doc else "No description",
            "full_doc": doc,
            "signature": signature,
            "is_private": step_name.startswith("_"),
        }

    def validate_pipeline(self, step_names: List[str]) -> tuple[bool, List[str]]:
        unknown = []
        for step_name in step_names:
            if step_name not in self.steps:
                unknown.append(step_name)

        return len(unknown) == 0, unknown

    def _handle_step_success(self, step: PipelineStep, step_name: str) -> bool:
        has_warnings = (
            hasattr(self.build_tool, "has_warnings") and self.build_tool.has_warnings()
        )
        if has_warnings and self.pipeline_config.get("stop_on_warning", False):
            raise Warning("Pipeline stopped due to warnings")

        step.duration = time.time() - step.start_time
        step.status = StepStatus.SUCCESS
        self.results.append(
            {"step": step_name, "status": "success", "duration": step.duration}
        )
        print(f"  [OK] Completed in {step.duration:.2f}s")
        return True

    def _handle_step_error(
        self,
        step: PipelineStep,
        step_name: str,
        error: Exception,
        is_warning: bool = False,
    ) -> bool:
        step.duration = time.time() - step.start_time
        step.status = StepStatus.FAILED
        step.error = str(error)

        error_type = "WARNING" if is_warning else "ERROR"
        if is_warning:
            print(f"  [WARNING] Stopped due to warnings: {error}")
        else:
            print(f"  [{error_type}] Failed: {error}")

        self.results.append(
            {
                "step": step_name,
                "status": "failed",
                "error": str(error),
                "duration": step.duration,
            }
        )

        stop_on = "stop_on_warning" if is_warning else "stop_on_error"

        if self.pipeline_config.get(stop_on, True):
            timeout = self.pipeline_config.get("timeout_seconds", 30)
            if not ask_continue_with_timeout(timeout):
                print("\n[INFO] Pipeline stopped by user")
                return False
        else:
            msg = "warning" if is_warning else "error"
            print(f"  [INFO] Continuing despite {msg} (configured)")

        return True

    def _execute_step(self, step: PipelineStep, step_name: str) -> bool:
        step.status = StepStatus.RUNNING
        step.start_time = time.time()
        step.error = None

        try:
            step.func()
            if (
                hasattr(self.build_tool, "has_warnings")
                and self.build_tool.has_warnings()
            ):
                self.build_tool._warnings_occurred = False
                return self._handle_step_error(
                    step,
                    step_name,
                    Exception("Step completed with warnings"),
                    is_warning=True,
                )

            return self._handle_step_success(step, step_name)
        except Warning as w:
            return self._handle_step_error(step, step_name, w, is_warning=True)
        except Exception as e:
            return self._handle_step_error(step, step_name, e, is_warning=False)

    def run(self, step_names: List[str]) -> bool:
        print("\n" + "=" * 60)
        print("   CUSTOM PIPELINE EXECUTION")
        print("=" * 60)

        is_valid, unknown = self.validate_pipeline(step_names)
        if not is_valid:
            print(f"\n[ERROR] Unknown steps: {', '.join(unknown)}")
            print("\nAvailable steps:")
            for step in self.list_available_steps()[:10]:
                info = self.get_step_info(step)
                print(f"  * {step:<30} - {info['doc']}")
            if len(self.steps) > 10:
                print(f"  ... and {len(self.steps) - 10} more")
            return False

        print(f"\nPipeline steps: {' -> '.join(step_names)}")
        print("-" * 60)

        overall_success = True

        for i, step_name in enumerate(step_names, 1):
            step = self.steps[step_name]
            print(f"\n[{i}/{len(step_names)}] {step.status.value} {step_name}")

            continue_pipeline = self._execute_step(step, step_name)

            if step.status == StepStatus.FAILED:
                overall_success = False

            if not continue_pipeline:
                break

        self._print_summary()
        return overall_success

    def _print_summary(self):
        print("\n" + "=" * 60)
        print("PIPELINE EXECUTION SUMMARY")
        print("=" * 60)

        total_time = sum(r.get("duration", 0) for r in self.results)

        for result in self.results:
            icon = "[OK]" if result["status"] == "success" else "[ERROR]"
            print(f"  {icon} {result['step']:<30} ({result['duration']:.2f}s)")
            if result.get("error"):
                print(f"     Error: {result['error']}")

        if total_time > 0:
            print("-" * 60)
            print(f"  Total time: {total_time:.2f}s")
            success_count = sum(1 for r in self.results if r["status"] == "success")
            failed_count = sum(1 for r in self.results if r["status"] == "failed")
            print(
                f"  Steps: {len(self.results)} total, {success_count} successful, {failed_count} failed"
            )

    def save_report(self, report_path: Path):
        import json
        from datetime import datetime

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
