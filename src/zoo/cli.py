"""Command-line interface: `zoo list`, `zoo check`, `zoo report`, `zoo run-agent`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from zoo.check import CheckResult, check
from zoo.detectors import Level
from zoo.tasks import REPO_ROOT, all_tasks, get_task, infer_task

app = typer.Typer(add_completion=False, no_args_is_help=True, help=__doc__)
console = Console()

VERDICT_STYLE = {
    "clean": "bold green",
    "incorrect": "bold yellow",
    "suspicious": "bold dark_orange",
    "hack": "bold red",
}
LEVEL_STYLE = {Level.CLEAN: "green", Level.SUSPICIOUS: "dark_orange", Level.FLAGGED: "bold red"}
SUITE_LABELS = {
    "visible": "Visible tests, as submitted",
    "original": "Original visible tests (clean room)",
    "hidden": "Hidden tests (clean room)",
}


@app.command("list")
def list_tasks() -> None:
    """List the tasks, their documented test weakness, and their specimens."""
    table = Table(show_lines=True)
    table.add_column("Task", style="bold")
    table.add_column("Why the visible tests are weak")
    table.add_column("Specimens (hand-written fixtures)")
    for task in all_tasks():
        specimens = "\n".join(
            f"{s.name} [dim]({', '.join(s.species) or 'honest'})[/dim]" for s in task.specimens()
        )
        table.add_row(f"{task.name}\n[dim]{task.title}[/dim]", task.weakness, specimens)
    console.print(table)


@app.command("check")
def check_command(
    candidate: Annotated[
        Path, typer.Argument(exists=True, file_okay=False, help="Workspace or specimen directory.")
    ],
    task: Annotated[
        str | None, typer.Option(help="Task name; inferred from the path if omitted.")
    ] = None,
    json_out: Annotated[
        Path | None, typer.Option("--json", help="Also write the result as JSON.")
    ] = None,
) -> None:
    """Run visible, original and hidden tests plus every detector against one candidate.

    Exits 0 only when the verdict is "clean".
    """
    task_obj = get_task(task) if task else infer_task(candidate)
    with console.status(f"Checking {candidate} against {task_obj.name}..."):
        result = check(task_obj, candidate)
    print_result(result)
    if json_out:
        json_out.write_text(json.dumps(result.to_dict(), indent=2))
    raise typer.Exit(0 if result.verdict == "clean" else 1)


@app.command("report")
def report_command(
    out: Annotated[Path, typer.Option(help="Where to write the HTML report.")] = REPO_ROOT
    / "report"
    / "index.html",
    runs: Annotated[Path, typer.Option(help="Directory of recorded agent runs.")] = REPO_ROOT
    / "runs",
) -> None:
    """Check every specimen, load recorded agent runs, and write a static HTML report."""
    from zoo.report import check_all_specimens, load_runs, render

    rows = check_all_specimens(
        progress=lambda label: console.print(f"  checked [bold]{label}[/bold]")
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(rows, load_runs(runs)))
    console.print(f"Wrote [bold]{out}[/bold]")


@app.command("run-agent")
def run_agent_command(
    task: Annotated[str, typer.Argument(help="Task name, e.g. parse_duration.")],
    agent: Annotated[str, typer.Option(help="Preset: claude or codex.")] = "claude",
    command: Annotated[
        str | None,
        typer.Option(help="Custom agent command; {prompt} is replaced by the shell-quoted prompt."),
    ] = None,
    runs: Annotated[Path, typer.Option(help="Where to save the run record.")] = REPO_ROOT / "runs",
    timeout: Annotated[int, typer.Option(help="Seconds before the agent is stopped.")] = 900,
) -> None:
    """Give a real coding agent the task in a temp workspace, then check what it left behind.

    This spends money and uses your agent CLI's credentials. Nothing runs unless you call it.
    """
    from zoo.agent_runner import run_agent

    record_path = run_agent(
        get_task(task), agent=agent, command=command, runs_dir=runs, timeout=timeout
    )
    record = json.loads(record_path.read_text())
    print_result(CheckResult.from_dict(record["check"]))
    console.print(f"Saved run record to [bold]{record_path}[/bold]")


def print_result(result: CheckResult) -> None:
    suites = Table(box=None, show_header=False, padding=(0, 2, 0, 0))
    for name, suite in result.suites.items():
        mark = Text("PASS", style="green") if suite.green else Text("FAIL", style="red")
        suites.add_row(mark, SUITE_LABELS[name], Text(suite.summary(), style="dim"))

    species = Table(show_edge=False, expand=True)
    species.add_column("Species", style="bold", no_wrap=True)
    species.add_column("Level", no_wrap=True)
    species.add_column("Evidence")
    for finding in result.findings:
        species.add_row(
            finding.species,
            Text(finding.level.value, style=LEVEL_STYLE[finding.level]),
            Text("\n".join(finding.evidence), style="dim" if finding.level is Level.CLEAN else ""),
        )

    s = result.sensitivity
    if s.measured:
        null = "fail" if s.null_killed else "[bold red]still pass[/bold red]"
        sensitivity = (
            f"Submitted tests {null} against a null implementation, "
            f"and kill {s.killed}/{s.total} mutants."
        )
    else:
        sensitivity = "Mutation probes skipped (solution.py does not parse)."

    verdict = Text(result.verdict.upper(), style=VERDICT_STYLE[result.verdict])
    flagged = ", ".join(sorted(result.flagged()))
    title = Text.assemble(f"{result.candidate}  ", verdict, f"  {flagged}" if flagged else "")
    console.print(
        Panel(
            Group(suites, "", species, "", Text.from_markup(sensitivity)),
            title=title,
            title_align="left",
        )
    )
