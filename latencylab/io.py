from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from latencylab.types import RunResult, TaskInstance
from latencylab.validate import ModelValidationError


def _refuse_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ModelValidationError(
                f"duplicate key '{key}' in model JSON; only one can be meant"
            )
        out[key] = value
    return out


def parse_model_json(text: str) -> Any:
    """Parse model JSON, refusing a key that appears twice in one object.

    Plain `json.loads` keeps the last of two equal keys, so a task block pasted
    and not renamed (or a second `wiring` object) silently replaced the first.
    """
    return json.loads(text, object_pairs_hook=_refuse_duplicate_keys)


def read_model_json(path: Path) -> Any:
    """Read and parse a model file: the one loader every caller shares."""
    return parse_model_json(path.read_text(encoding="utf-8"))


def write_summary_json(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def write_runs_csv(path: Path, runs: list[RunResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "run_id",
                "first_ui_event_time_ms",
                "last_ui_event_time_ms",
                "makespan_ms",
                "critical_path_ms",
                "critical_path_tasks",
                "failed",
                "failure_reason",
            ]
        )
        for r in runs:
            w.writerow(
                [
                    r.run_id,
                    r.first_ui_event_time_ms,
                    r.last_ui_event_time_ms,
                    r.makespan_ms,
                    r.critical_path_ms,
                    r.critical_path_tasks,
                    int(r.failed),
                    r.failure_reason or "",
                ]
            )


def write_trace_csv(path: Path, trace: list[TaskInstance]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "run_id",
                "instance_id",
                "task_name",
                "context",
                "enqueue_time_ms",
                "start_time_ms",
                "end_time_ms",
                "queue_wait_ms",
                "duration_ms",
                "parent_task_instance_id",
                "capacity_parent_instance_id",
                "emitted_events",
            ]
        )
        for t in trace:
            w.writerow(
                [
                    t.run_id,
                    t.instance_id,
                    t.task_name,
                    t.context,
                    t.enqueue_time_ms,
                    t.start_time_ms,
                    t.end_time_ms,
                    t.queue_wait_ms,
                    t.duration_ms,
                    t.parent_task_instance_id,
                    t.capacity_parent_instance_id,
                    ";".join(t.emitted_events),
                ]
            )
