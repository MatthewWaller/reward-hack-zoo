"""`zoo report`: one static HTML page with every specimen and every recorded agent run."""

from __future__ import annotations

import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from importlib.resources import files
from pathlib import Path
from string import Template

from zoo.check import CheckResult, check
from zoo.detectors import SPECIES, Finding, Level
from zoo.tasks import Specimen, Task, all_tasks

SUITE_COLUMNS = {
    "visible": (
        "Submitted<br>tests",
        "Submitted tests",
        "The tests and config the candidate left behind",
    ),
    "original": (
        "Original<br>visible",
        "Original visible tests",
        "The task's original visible tests, run on the candidate's solution.py",
    ),
    "hidden": (
        "Hidden<br>tests",
        "Hidden tests",
        "The hidden suite, run on the candidate's solution.py",
    ),
}
LEVEL_GLYPH = {Level.CLEAN: "", Level.SUSPICIOUS: "!", Level.FLAGGED: "&#x2715;"}


@dataclass
class SpecimenRow:
    task: Task
    specimen: Specimen
    result: CheckResult

    @property
    def as_intended(self) -> bool:
        """Did the detector flag exactly the species this fixture was written to show?"""
        if self.specimen.kind == "honest":
            return self.result.verdict == "clean"
        return self.result.flagged() == set(self.specimen.species)


@dataclass
class RunRow:
    record: dict
    result: CheckResult


def check_all_specimens(progress: Callable[[str], None] | None = None) -> list[SpecimenRow]:
    pairs = [(task, specimen) for task in all_tasks() for specimen in task.specimens()]

    def run(pair: tuple[Task, Specimen]) -> SpecimenRow:
        task, specimen = pair
        row = SpecimenRow(
            task, specimen, check(task, specimen.path, f"{task.name}/{specimen.name}")
        )
        if progress:
            progress(row.result.candidate)
        return row

    with ThreadPoolExecutor(max_workers=3) as pool:
        return list(pool.map(run, pairs))


def load_runs(runs_dir: Path) -> list[RunRow]:
    """Recorded agent runs only. Anything that is not an agent-run record is ignored."""
    rows = []
    for path in sorted(runs_dir.glob("*.json")) if runs_dir.is_dir() else []:
        try:
            record = json.loads(path.read_text())
            if record.get("kind") == "agent-run":
                rows.append(RunRow(record, CheckResult.from_dict(record["check"])))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
    return rows


def render(rows: list[SpecimenRow], runs: list[RunRow]) -> str:
    template = Template(files("zoo").joinpath("report_template.html").read_text())
    hacks = [r for r in rows if r.specimen.kind == "hack"]
    honest = [r for r in rows if r.specimen.kind == "honest"]
    return template.substitute(
        stats=_stats(rows, hacks, honest, runs),
        specimen_table=_specimen_table(rows),
        runs_section=_runs_section(runs),
        glossary=_glossary(),
        generated=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    )


# --- sections ---------------------------------------------------------------------------


def _stats(rows, hacks, honest, runs) -> str:
    tiles = [
        (
            str(len({r.task.name for r in rows})),
            "tasks",
            "each with weak visible tests and robust hidden ones",
        ),
        (str(len(rows)), "specimens", "hand-written fixtures, not model output"),
        (
            f"{sum(r.as_intended for r in hacks)}/{len(hacks)}",
            "hacks caught as written",
            "flagged species match the fixture's label",
        ),
        (
            f"{sum(r.as_intended for r in honest)}/{len(honest)}",
            "honest solutions clean",
            "no species flagged, all suites pass",
        ),
        (str(len(runs)), "recorded agent runs", "real runs from zoo run-agent"),
    ]
    return "".join(
        f'<div class="tile"><div class="tile-value">{value}</div>'
        f'<div class="tile-label">{label}</div><div class="tile-note">{note}</div></div>'
        for value, label, note in tiles
    )


def _header_row(first: str) -> str:
    suites = "".join(
        f'<th class="col" title="{escape(tip)}">{label}</th>'
        for label, _name, tip in SUITE_COLUMNS.values()
    )
    species = "".join(
        f'<th class="col species" title="{escape(desc)}">{escape(name).replace("-", "-<br>", 1)}</th>'
        for name, desc in SPECIES.items()
    )
    return f'<tr><th class="name">{first}</th>{suites}<th class="gap"></th>{species}<th class="col">Verdict</th></tr>'


def _specimen_table(rows: list[SpecimenRow]) -> str:
    body, current = [], None
    for index, row in enumerate(rows):
        if row.task.name != current:
            current = row.task.name
            body.append(
                f'<tr class="group"><td colspan="13"><span class="task-name">{escape(row.task.title)}</span>'
                f'<code>{escape(row.task.name)}</code><span class="weakness">Weak spot: '
                f"{escape(row.task.weakness)}</span></td></tr>"
            )
        kind = row.specimen.kind
        label = (
            f'<span class="spec-name">{escape(row.specimen.name)}</span>'
            f'<span class="kind kind-{kind}">{kind}</span>'
        )
        detail = _detail(row.result, summary=row.specimen.summary, extra=_fixture_note(row))
        body.append(_matrix_row(f"s{index}", label, row.result, set(row.specimen.species), detail))
    return f'<table class="matrix"><thead>{_header_row("Specimen")}</thead><tbody>{"".join(body)}</tbody></table>'


def _runs_section(runs: list[RunRow]) -> str:
    if not runs:
        return (
            '<div class="empty"><div class="empty-title">No recorded agent runs yet</div>'
            "<p>This section only ever shows real runs recorded by "
            "<code>zoo run-agent &lt;task&gt; --agent claude</code> (or <code>codex</code>). "
            "Each run gives a coding agent the task in a throwaway repo, checks what it left "
            "behind, and saves the transcript, diff and verdict to <code>runs/</code>.</p></div>"
        )
    body = []
    for index, run in enumerate(runs):
        rec = run.record
        label = (
            f'<span class="spec-name">{escape(rec["agent"])} &middot; {escape(rec["task"])}</span>'
            f'<span class="kind kind-run">{escape(rec["started_at"][:16].replace("T", " "))}</span>'
        )
        extra = (
            f'<div class="meta">Command <code>{escape(rec["command"])}</code> &middot; exit {rec["exit_code"]}'
            f" &middot; {rec['duration_s']}s</div>"
            + _code_block("Agent's workspace diff", rec.get("workspace_diff", ""), diff=True)
            + _code_block("Transcript (tail)", rec.get("transcript", "")[-6000:])
        )
        body.append(
            _matrix_row(f"r{index}", label, run.result, set(), _detail(run.result, extra=extra))
        )
    return f'<table class="matrix"><thead>{_header_row("Run")}</thead><tbody>{"".join(body)}</tbody></table>'


def _glossary() -> str:
    return "".join(
        f'<div class="gloss"><code>{escape(name)}</code><span>{escape(desc)}</span></div>'
        for name, desc in SPECIES.items()
    )


# --- rows and details -------------------------------------------------------------------


def _matrix_row(
    row_id: str, label: str, result: CheckResult, expected: set[str], detail: str
) -> str:
    cells = [_suite_cell(result.suites[name]) for name in SUITE_COLUMNS]
    cells.append('<td class="gap"></td>')
    cells += [_species_cell(f, f.species in expected) for f in result.findings]
    cells.append(
        f'<td class="col"><span class="verdict v-{result.verdict}">{result.verdict}</span></td>'
    )
    return (
        f'<tr class="row" data-target="{row_id}" tabindex="0" aria-expanded="false">'
        f'<td class="name"><span class="chevron"></span>{label}</td>{"".join(cells)}</tr>'
        f'<tr class="detail" id="{row_id}" hidden><td colspan="13">{detail}</td></tr>'
    )


def _suite_cell(suite) -> str:
    state, glyph = ("pass", "&#x2713;") if suite.green else ("fail", "&#x2715;")
    return f'<td class="col"><span class="cell {state}" title="{escape(suite.summary())}">{glyph}</span></td>'


def _species_cell(finding: Finding, expected: bool) -> str:
    ring = " expected" if expected else ""
    tip = escape(
        finding.level.value
        + (" (the species this fixture was written to show)" if expected else "")
    )
    return (
        f'<td class="col"><span class="cell {finding.level.value}{ring}" title="{tip}">'
        f"{LEVEL_GLYPH[finding.level]}</span></td>"
    )


def _fixture_note(row: SpecimenRow) -> str:
    written = ", ".join(row.specimen.species) or "nothing (honest solution)"
    status = "matches" if row.as_intended else "does NOT match"
    return (
        f'<div class="meta">Illustrative fixture, hand-written for this repo. Written to exhibit: '
        f"<b>{escape(written)}</b>. Detector output {status}.</div>"
    )


def _detail(result: CheckResult, summary: str = "", extra: str = "") -> str:
    parts = [f'<p class="summary">{escape(summary)}</p>' if summary else "", extra]
    findings = [f for f in result.findings if f.evidence]
    if findings:
        items = "".join(
            f'<li><span class="pill p-{f.level.value}">{f.level.value}</span><b>{escape(f.species)}</b>'
            f"<ul>{''.join(f'<li><code>{escape(line)}</code></li>' for line in f.evidence)}</ul></li>"
            for f in findings
        )
        parts.append(f'<h4>Evidence</h4><ul class="evidence">{items}</ul>')
    suites = "".join(
        f"<li><b>{escape(SUITE_COLUMNS[name][1])}</b> {escape(s.summary())}"
        + (
            f' <span class="muted">failing: {escape(", ".join(s.failures[:5]))}</span>'
            if s.failures
            else ""
        )
        + "</li>"
        for name, s in result.suites.items()
    )
    parts.append(f'<h4>Suites</h4><ul class="plain">{suites}</ul>')
    parts.append(_sensitivity(result))
    parts.append(_code_block("Changes to tests and config", result.diff, diff=True))
    parts.append(_code_block("solution.py", result.solution))
    return f'<div class="detail-inner">{"".join(parts)}</div>'


def _sensitivity(result: CheckResult) -> str:
    s = result.sensitivity
    if not s.measured:
        return "<h4>Test sensitivity</h4><p>Skipped: solution.py does not parse.</p>"
    null = "fail, as they should" if s.null_killed else '<b class="bad">still pass</b>'
    survivors = "".join(f"<li><code>{escape(d)}</code></li>" for d in s.survivors)
    if s.total:
        killed = (
            f" They kill {s.killed} of {s.total} single-point mutants of this solution"
            + (f'; these survive:</p><ul class="plain">{survivors}</ul>' if survivors else ".</p>")
        )
    else:
        killed = " This solution has no mutation sites.</p>"
    return (
        f"<h4>Test sensitivity</h4><p>Against a null implementation the submitted tests {null}."
        f"{killed}"
    )


def _code_block(title: str, text: str, diff: bool = False) -> str:
    if not text.strip():
        return ""
    lines = []
    for line in text.rstrip("\n").splitlines():
        cls = ""
        if diff and line.startswith(("+++", "---")):
            cls = "d-file"
        elif diff and line.startswith("+"):
            cls = "d-add"
        elif diff and line.startswith("-"):
            cls = "d-del"
        elif diff and line.startswith("@@"):
            cls = "d-hunk"
        lines.append(f'<span class="{cls}">{escape(line)}</span>' if cls else escape(line))
    return f'<h4>{escape(title)}</h4><pre class="code">{chr(10).join(lines)}</pre>'
