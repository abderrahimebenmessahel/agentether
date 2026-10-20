"""The capability probe of the candidate models of the trial.

The probe asks a model to do **one real step of a real task** with the
prompt of the trial, and it checks what the trial needs:

(i)   the model follows the ``FILE: path`` protocol of the harness;
(ii)  the answer ends with a telemetry object that parses, with the exact
      step name and the artifacts of the step;
(iii) the model honours a low temperature (the same prompt twice gives
      the same answer);
(iv)  the model handles the context of the prompt;
(v)   the model stays available (several calls in a row, no error).

The raw results are written to a JSON file.  The answers themselves are
**not** kept: only the metrics of every call.

    python benchmarks/probe.py --provider groq --models a,b --requests 12 \\
        --out benchmarks/results/probe-groq.json

The script never prints a key and never writes one.

.. versionadded:: 0.3.0a1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import build_prompt, parse_file_blocks
from tasks import TASKS

from agentether import TelemetryParseError, parse_telemetry
from agentether.adapters.openai_compatible import (
    OpenAICompatibleError,
    OpenAICompatibleTransientError,
    TokenBucketLimiter,
    list_free_models,
    openai_compatible_complete,
    provider_for,
    resolve_provider_key,
)

#: The step of the trial that the probe uses.  It asks for two files, so a
#: model that only writes one of them is caught.
PROBE_TASK = TASKS[0]
PROBE_STEP = PROBE_TASK.steps[-1]
PROBE_EXPECTED = tuple(spec.path for spec in PROBE_TASK.steps[-1].files)


def _normalise(text: str) -> str:
    """A rough normal form of an answer, to compare two answers."""
    return " ".join(text.split())


async def probe_model(
    provider: str,
    model: str,
    requests: int,
    limiter: TokenBucketLimiter,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Probe one model and return the metrics of the calls."""
    spec = provider_for(provider)
    prompt = build_prompt(PROBE_STEP)
    metrics: dict[str, Any] = {
        "provider": provider,
        "model": model,
        "requests": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "errors": 0,
        "telemetry_ok": 0,
        "step_ok": 0,
        "progress_ok": 0,
        "file_block_ok": 0,
        "artifacts_ok": 0,
        "answers": [],
    }
    answers: list[str] = []
    started = time.monotonic()
    for _index in range(requests):
        try:
            output = await openai_compatible_complete(
                prompt,
                spec=spec,
                model=model,
                api_key_resolver=lambda: resolve_provider_key(spec),
                max_retries=1,
                timeout=timeout,
                temperature=0.0,
                limiter=limiter,
            )
        except (OpenAICompatibleError, OpenAICompatibleTransientError) as exc:
            metrics["errors"] += 1
            metrics["answers"].append({"error": type(exc).__name__, "message": str(exc)[:200]})
            continue
        metrics["requests"] += 1
        usage = output.usage
        if usage is not None:
            metrics["input_tokens"] += usage.input_tokens
            metrics["output_tokens"] += usage.output_tokens
        text = output.text
        answers.append(text)

        blocks = parse_file_blocks(text)
        metrics["file_block_ok"] += 1 if blocks else 0
        try:
            telemetry = parse_telemetry(text, PROBE_STEP.name)
        except TelemetryParseError as exc:
            metrics["answers"].append({"telemetry_error": exc.reason[:200]})
            continue
        metrics["telemetry_ok"] += 1
        metrics["step_ok"] += 1 if telemetry.step == PROBE_STEP.name else 0
        metrics["progress_ok"] += 1 if telemetry.progress == 100 else 0
        claimed = tuple(telemetry.artifacts or ())
        metrics["artifacts_ok"] += 1 if set(PROBE_EXPECTED) <= set(claimed) else 0

    # (iii) the same prompt twice must give the same answer.
    deterministic = None
    if len(answers) >= 2:
        deterministic = _normalise(answers[0]) == _normalise(answers[1])

    total = max(1, metrics["requests"])
    return {
        "provider": provider,
        "model": model,
        "requests_sent": requests,
        "requests_ok": metrics["requests"],
        "errors": metrics["errors"],
        "input_tokens": metrics["input_tokens"],
        "output_tokens": metrics["output_tokens"],
        "tokens_per_request": round(
            (metrics["input_tokens"] + metrics["output_tokens"]) / total, 1
        ),
        "telemetry_rate": metrics["telemetry_ok"] / total,
        "step_exact_rate": metrics["step_ok"] / total,
        "progress_100_rate": metrics["progress_ok"] / total,
        "file_block_rate": metrics["file_block_ok"] / total,
        "artifacts_rate": metrics["artifacts_ok"] / total,
        "deterministic": deterministic,
        "seconds": round(time.monotonic() - started, 1),
        "notes": metrics["answers"][:4],
    }


async def main_async(args: argparse.Namespace) -> int:
    """Run the probe."""
    spec = provider_for(args.provider)
    if spec.key_variables():
        resolve_provider_key(spec)
    limiter = TokenBucketLimiter(min(args.rate_limit, spec.requests_per_minute))
    models = list(args.models)
    results: list[dict[str, Any]] = []
    for model in models:
        print(f"--- {spec.name} / {model} ---", flush=True)
        result = await probe_model(args.provider, model, args.requests, limiter, args.timeout)
        print(json.dumps(result, indent=2)[:1200], flush=True)
        results.append(result)
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provider": args.provider,
        "requests_per_model": args.requests,
        "results": results,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"written: {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point of the probe."""
    parser = argparse.ArgumentParser(description="Probe the candidate models.")
    parser.add_argument("--provider", default="openrouter")
    parser.add_argument("--models", nargs="*", default=[])
    parser.add_argument("--requests", type=int, default=12)
    parser.add_argument("--rate-limit", type=int, default=15)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--list", action="store_true", help="only list the free models of the provider"
    )
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)

    if args.list:
        spec = provider_for(args.provider)
        found = list_free_models(spec)
        print(json.dumps(found, indent=2))
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(
                json.dumps(
                    {
                        "provider": args.provider,
                        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "free_models": found,
                    },
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            print(f"written: {out}")
        return 0

    if not args.models:
        print("no model was given", file=sys.stderr)
        return 2
    if not args.output:
        args.output = f"benchmarks/results/probe-{args.provider}.json"
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
