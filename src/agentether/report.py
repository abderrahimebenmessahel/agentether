"""The run report.

``agentether report <memory_dir>`` builds a single, self-contained report of a
run: the timeline of the events, the claims of the agent, the verifications,
the detected loops and the budget.

The HTML variant escapes everything that comes from the model, so a report can
never carry a script into the browser of whoever reads it.

.. versionadded:: 0.3.0-alpha
"""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any

from .ledger import compute_stats, read_claims
from .state_manager import StateManager

__all__ = ["build_report", "render_html", "render_markdown"]


def _read_events(memory_dir: Path) -> list[dict[str, Any]]:
    """Read the event log of a project."""
    path = memory_dir / "events.jsonl"
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                events.append(record)
    return events


def _read_state(memory_dir: Path) -> dict[str, Any]:
    """Read the state of a project (an empty state when it cannot be read).

    The state is read in a fresh event loop; when the caller already runs a
    loop, the read happens in a worker thread.
    """
    import asyncio
    import concurrent.futures

    async def _load() -> dict[str, Any]:
        return await StateManager(memory_dir).load()

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        try:
            return asyncio.run(_load())
        except Exception:
            return {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        try:
            return pool.submit(asyncio.run, _load()).result()
        except Exception:
            return {}


def build_report(memory_dir: str | os.PathLike[str]) -> dict[str, Any]:
    """Collect everything that is known about a run.

    Args:
        memory_dir: The project memory directory.

    Returns:
        A JSON-serialisable report.
    """
    directory = Path(memory_dir)
    claims = read_claims(directory)
    events = _read_events(directory)
    state = _read_state(directory)
    stats = compute_stats(claims)
    loops = [event for event in events if event.get("event") == "loop_detected"]
    rejections = [event for event in events if event.get("event") == "verification_failed"]
    return {
        "memory_dir": str(directory),
        "roadmap": list(state.get("roadmap", [])),
        "completed_steps": list(state.get("completed_steps", [])),
        "breaker": dict(state.get("breaker", {})),
        "budget": dict(state.get("budget", {})),
        "last_failure": state.get("last_failure"),
        "stats": stats.to_dict(),
        "claims": claims,
        "events": events,
        "loop_detections": len(loops),
        "verifier_rejections": len(rejections),
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render the report as Markdown."""
    stats = report["stats"]
    lines = [
        "# AgenTether run report",
        "",
        f"- Memory directory: `{report['memory_dir']}`",
        f"- Steps completed: {len(report['completed_steps'])} of {len(report['roadmap'])}",
        f"- Claims recorded: {stats['total_claims']}",
        f"- Claims verified true: {stats['verified_true']}",
        f"- False claim rate: {stats['false_claim_rate']:.3f}",
        f"- Verifier rejections: {report['verifier_rejections']}",
        f"- Loop detections: {report['loop_detections']}",
        "",
        "## Roadmap",
        "",
    ]
    completed = set(report["completed_steps"])
    for name in report["roadmap"]:
        mark = "x" if name in completed else " "
        lines.append(f"- [{mark}] {name}")
    if not report["roadmap"]:
        lines.append("_(no roadmap recorded)_")
    lines.extend(["", "## Timeline", "", "| When | Event | Detail |", "| --- | --- | --- |"])
    for event in report["events"]:
        detail = ""
        for key in ("step", "attempt", "reason", "similarity"):
            if key in event:
                detail = f"{key}={event[key]}"
                break
        lines.append(f"| {event.get('ts', '')} | {event.get('event', '')} | {detail} |")
    if len(report["events"]) == 0:
        lines.append("| _(no events)_ | | |")
    lines.extend(
        [
            "",
            "## Claims",
            "",
            "| Step | Attempt | Claimed | Summary | Verified |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for claim in report["claims"]:
        verification = claim.get("verification")
        verdict = "n/a"
        if isinstance(verification, dict):
            verdict = "yes" if verification.get("ok") else "NO"
        summary = str(claim.get("claimed_summary", "")).replace("|", "\\|")
        lines.append(
            f"| {claim.get('step', '')} | {claim.get('attempt', '')} "
            f"| {claim.get('claimed_status', '')} | {summary} | {verdict} |"
        )
    if not report["claims"]:
        lines.append("| _(no claims)_ | | | |")
    lines.append("")
    return "\n".join(lines)


def render_html(report: dict[str, Any]) -> str:
    """Render the report as a self-contained HTML page.

    Everything that comes from the model is escaped: a report can never carry
    a script into the browser of whoever reads it.
    """
    stats = report["stats"]
    body: list[str] = [
        "<!DOCTYPE html>",
        "<html lang='en'><head><meta charset='utf-8'>",
        "<title>AgenTether run report</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;margin:2rem;max-width:60rem}",
        "table{border-collapse:collapse;margin:1rem 0}",
        "td,th{border:1px solid #ccc;padding:.3rem .6rem;text-align:left}",
        "th{background:#f4f4f4}",
        "code{background:#f4f4f4;padding:0 .2rem}",
        "</style></head><body>",
        "<h1>AgenTether run report</h1>",
        "<ul>",
        f"<li>Memory directory: <code>{html.escape(str(report['memory_dir']))}</code></li>",
        f"<li>Steps completed: {len(report['completed_steps'])} of {len(report['roadmap'])}</li>",
        f"<li>Claims recorded: {stats['total_claims']}</li>",
        f"<li>Claims verified true: {stats['verified_true']}</li>",
        f"<li>False claim rate: {stats['false_claim_rate']:.3f}</li>",
        f"<li>Verifier rejections: {report['verifier_rejections']}</li>",
        f"<li>Loop detections: {report['loop_detections']}</li>",
        "</ul>",
        "<h2>Roadmap</h2><ul>",
    ]
    completed = set(report["completed_steps"])
    for name in report["roadmap"]:
        mark = "x" if name in completed else " "
        body.append(f"<li>[{html.escape(mark)}] {html.escape(str(name))}</li>")
    if not report["roadmap"]:
        body.append("<li><em>(no roadmap recorded)</em></li>")
    body.append("</ul>")
    body.append("<h2>Timeline</h2><table><tr><th>When</th><th>Event</th><th>Detail</th></tr>")
    for event in report["events"]:
        detail = ""
        for key in ("step", "attempt", "reason", "similarity"):
            if key in event:
                detail = f"{key}={event[key]}"
                break
        body.append(
            "<tr><td>{ts}</td><td>{event}</td><td>{detail}</td></tr>".format(
                ts=html.escape(str(event.get("ts", ""))),
                event=html.escape(str(event.get("event", ""))),
                detail=html.escape(detail),
            )
        )
    body.append("</table>")
    body.append(
        "<h2>Claims</h2><table><tr><th>Step</th><th>Attempt</th><th>Claimed</th>"
        "<th>Summary</th><th>Verified</th></tr>"
    )
    for claim in report["claims"]:
        verification = claim.get("verification")
        verdict = "n/a"
        if isinstance(verification, dict):
            verdict = "yes" if verification.get("ok") else "NO"
        body.append(
            "<tr><td>{step}</td><td>{attempt}</td><td>{status}</td>"
            "<td>{summary}</td><td>{verdict}</td></tr>".format(
                step=html.escape(str(claim.get("step", ""))),
                attempt=html.escape(str(claim.get("attempt", ""))),
                status=html.escape(str(claim.get("claimed_status", ""))),
                summary=html.escape(str(claim.get("claimed_summary", ""))),
                verdict=html.escape(verdict),
            )
        )
    body.append("</table></body></html>")
    return "\n".join(body)
