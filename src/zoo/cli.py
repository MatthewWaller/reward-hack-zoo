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
from zoo.tasks import REPO_ROOT, all_tasks, get_task, infer_task, load_task

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
    "visible": "Submitted tests",
    "original": "Original visible tests",
    "hidden": "Hidden tests",
}
SUITE_NOTE = (
    "Submitted tests run with the candidate's tests and config. "
    "The other two run its solution.py against suites it cannot edit."
)


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
    console.print(
        "\n[dim]Grade one specimen with[/dim] zoo check tasks/<task>/specimens/<name>"
        "\n[dim]Grade every specimen with[/dim] zoo report"
        "\n[dim]workspace/solution.py is an unimplemented stub. "
        "Pointing zoo check at a task directory is refused.[/dim]"
    )


@app.command("check")
def check_command(
    candidate: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=False,
            help="Specimen directory, or a workspace an agent left behind.",
        ),
    ],
    task: Annotated[
        str | None,
        typer.Option(help="Task name. Inferred by walking up to task.toml if omitted."),
    ] = None,
    json_out: Annotated[
        Path | None, typer.Option("--json", help="Also write the result as JSON.")
    ] = None,
) -> None:
    """Grade one solution: a specimen, or a workspace an agent left behind.

    A task directory (the folder that contains task.toml) holds the stub, the hidden
    tests and every specimen. That path is refused. workspace/solution.py starts
    unimplemented, so grading workspace/ fails every test.

    Exits 0 only when the verdict is "clean", and 2 when the path is a task directory.
    """
    _reject_task_directory(candidate)
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


def _reject_task_directory(candidate: Path) -> None:
    """The task folder is a collection of solutions. zoo check grades one of them."""
    if not (candidate / "task.toml").is_file():
        return
    task = load_task(candidate)
    commands = "\n".join(
        f"  zoo check {candidate / 'specimens' / specimen.name}" for specimen in task.specimens()
    )
    console.print(
        f"{candidate} is a task directory. It holds the unimplemented stub in workspace/, "
        "the hidden tests, and every specimen. zoo check grades one solution at a time.\n\n"
        "Grade one specimen:\n"
        f"{commands}\n\n"
        "Grade every specimen with zoo report.\n\n"
        "workspace/solution.py is the stub. "
        f"zoo check {candidate / 'workspace'} grades that stub, and every test fails."
    )
    raise typer.Exit(2)


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
        if s.total:
            sensitivity = (
                f"Submitted tests {null} against a null implementation, "
                f"and kill {s.killed}/{s.total} mutants."
            )
        else:
            sensitivity = (
                f"Submitted tests {null} against a null implementation. "
                "This solution has no mutation sites."
            )
    else:
        sensitivity = "Mutation probes skipped (solution.py does not parse)."

    verdict = Text(result.verdict.upper(), style=VERDICT_STYLE[result.verdict])
    flagged = ", ".join(sorted(result.flagged()))
    title = Text.assemble(f"{result.candidate}  ", verdict, f"  {flagged}" if flagged else "")
    console.print(
        Panel(
            Group(
                suites,
                Text(SUITE_NOTE, style="dim"),
                "",
                species,
                "",
                Text.from_markup(sensitivity),
            ),
            title=title,
            title_align="left",
        )
    )
