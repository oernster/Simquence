from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latencylab.io import (
    read_model_json,
    write_runs_csv,
    write_summary_json,
    write_trace_csv,
)
from latencylab.metrics import add_task_metadata, aggregate_runs
from latencylab.model import Model
from latencylab.sim import simulate_many
from latencylab.validate import validate_model

# The exit status for a model that cannot be read or is not valid; argparse
# already uses the same status for a command line it cannot parse.
EXIT_BAD_MODEL = 2

# What reading, parsing and validating a malformed model raises. JSON syntax
# errors and ModelValidationError are both ValueError; a missing field is a
# KeyError; a list where an object belongs is an AttributeError or TypeError.
_BAD_MODEL_ERRORS = (OSError, ValueError, KeyError, TypeError, AttributeError)


def _describe(exc: BaseException) -> str:
    if isinstance(exc, KeyError):
        return f"missing field {exc}"
    return str(exc)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="latencylab", description="LatencyLab simulator")
    sub = p.add_subparsers(dest="cmd", required=True)

    sim = sub.add_parser("simulate", help="Run simulations for a model")
    sim.add_argument("--model", required=True, type=Path)
    sim.add_argument("--runs", required=True, type=int)
    sim.add_argument("--seed", required=True, type=int)
    sim.add_argument("--out-summary", required=True, type=Path)
    sim.add_argument("--out-runs", required=True, type=Path)
    sim.add_argument("--out-trace", required=False, type=Path)
    sim.add_argument(
        "--max-tasks-per-run",
        required=False,
        type=int,
        default=200_000,
        help="Safety limit to prevent infinite runs in cyclic models",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    p = _build_parser()
    args = p.parse_args(argv)

    if args.cmd == "simulate":
        try:
            model = Model.from_json(read_model_json(args.model))
            validate_model(model)
        except _BAD_MODEL_ERRORS as exc:
            print(
                f"latencylab: cannot use model {args.model}: {_describe(exc)}",
                file=sys.stderr,
            )
            return EXIT_BAD_MODEL

        runs, traces = simulate_many(
            model=model,
            runs=args.runs,
            seed=args.seed,
            max_tasks_per_run=args.max_tasks_per_run,
            want_trace=bool(args.out_trace),
        )

        summary = aggregate_runs(model=model, runs=runs)
        summary = add_task_metadata(summary, model=model)
        write_summary_json(args.out_summary, summary)
        write_runs_csv(args.out_runs, runs)
        if args.out_trace:
            write_trace_csv(args.out_trace, traces)

        return 0

    raise AssertionError(f"Unhandled command: {args.cmd}")
