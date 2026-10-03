from __future__ import annotations

import math

from latencylab.model import Model

# The character that joins task names into a critical-path identity. A name
# containing it would make two different chains report the same path.
PATH_SEPARATOR = ">"

# The largest mu whose median duration, e^mu, is still a finite float. Past it
# every typical draw is infinite and the v2 engine's math.exp overflows.
MAX_LOGNORMAL_MU = math.log(math.nextafter(math.inf, 0.0))

# The schema version whose engine reads only the flat event-to-task wiring.
LEGACY_VERSION = 1


class ModelValidationError(ValueError):
    pass


def _validate_dist(name: str, dist: str, p: dict[str, float]) -> None:
    # NaN fails every comparison below (so `< 0` would let it through) and the
    # v1 engine never pops a NaN completion time, so a NaN hangs it forever.
    for key, value in p.items():
        if not math.isfinite(value):
            raise ModelValidationError(
                f"{name} {dist} parameter '{key}' must be a finite number "
                f"(got {value})"
            )
    if dist == "fixed":
        if "value" not in p:
            raise ModelValidationError(f"{name} fixed dist requires 'value'")
        if p["value"] < 0:
            raise ModelValidationError(f"{name} fixed value must be >= 0")
        return
    if dist == "normal":
        for k in ("mean", "std"):
            if k not in p:
                raise ModelValidationError(f"{name} normal dist requires '{k}'")
        if p["mean"] < 0:
            raise ModelValidationError(f"{name} normal mean must be >= 0")
        if p["std"] < 0:
            raise ModelValidationError(f"{name} normal std must be >= 0")
        if "min" in p and p["min"] < 0:
            raise ModelValidationError(f"{name} normal min must be >= 0")
        return
    if dist == "lognormal":
        for k in ("mu", "sigma"):
            if k not in p:
                raise ModelValidationError(f"{name} lognormal dist requires '{k}'")
        if p["sigma"] < 0:
            raise ModelValidationError(f"{name} lognormal sigma must be >= 0")
        if p["mu"] > MAX_LOGNORMAL_MU:
            raise ModelValidationError(
                f"{name} lognormal mu must be <= {MAX_LOGNORMAL_MU:.2f}, "
                "beyond which the median duration is too large to represent"
            )
        return
    raise ModelValidationError(f"{name} has unsupported dist '{dist}'")


def _validate_name(kind: str, name: str) -> None:
    if PATH_SEPARATOR in name:
        raise ModelValidationError(
            f"{kind} name '{name}' must not contain '{PATH_SEPARATOR}', "
            "which separates names in a critical path"
        )


def validate_model(model: Model) -> None:
    if model.version not in (1, 2):
        raise ModelValidationError(
            f"Unsupported model version: {model.version} (expected 1 or 2)"
        )

    if model.entry_event not in model.events:
        raise ModelValidationError(
            f"entry_event '{model.entry_event}' must exist in events"
        )

    for ev_name in model.events:
        _validate_name("event", ev_name)

    for ctx_name, ctx in model.contexts.items():
        if ctx.concurrency < 1:
            raise ModelValidationError(
                f"context '{ctx_name}' concurrency must be >= 1 (got {ctx.concurrency})"
            )
        if ctx.policy != "fifo":
            raise ModelValidationError(
                (
                    f"context '{ctx_name}' policy must be 'fifo' in MVP "
                    f"(got {ctx.policy!r})"
                )
            )

    for task_name, task in model.tasks.items():
        _validate_name("task", task_name)
        if task.context not in model.contexts:
            raise ModelValidationError(
                f"task '{task_name}' references unknown context '{task.context}'"
            )

        _validate_dist(
            name=f"task '{task_name}'",
            dist=task.duration_ms.dist,
            p=task.duration_ms.params,
        )

        for ev in task.emit:
            if ev not in model.events:
                raise ModelValidationError(
                    (
                        f"task '{task_name}' emits unknown event '{ev}' "
                        "(must exist in events)"
                    )
                )

    for ev, edges in model.wiring_edges.items():
        if ev not in model.events:
            raise ModelValidationError(f"wiring references unknown event '{ev}'")
        for edge in edges:
            if edge.task not in model.tasks:
                raise ModelValidationError(
                    f"wiring for event '{ev}' references unknown task '{edge.task}'"
                )
            if edge.delay_ms is None:
                continue
            # The v1 engine walks the flat wiring map, which carries no delay,
            # so a delay in a v1 model would be dropped without a word.
            if model.version == LEGACY_VERSION:
                raise ModelValidationError(
                    f"wiring '{ev}' -> '{edge.task}' has delay_ms, which only "
                    "schema_version 2 runs; declare the model as schema_version 2"
                )
            _validate_dist(
                name=f"wiring '{ev}' -> '{edge.task}' delay_ms",
                dist=edge.delay_ms.dist,
                p=edge.delay_ms.params,
            )
