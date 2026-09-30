"""Loading tasks and their specimens from the `tasks/` directory.

Layout of one task::

    tasks/<name>/
        task.toml            title, entrypoints, and the documented test weakness
        SPEC.md              what the agent is asked to build
        workspace/           what the agent sees: a stub solution.py and tests/
        hidden/              robust tests the agent never sees
        specimens/<name>/    hand-written example solutions (overlaid on workspace/)

`zoo check` grades one specimen directory, or a workspace an agent left behind.
The task directory itself is refused: it is the stub, the hidden tests and every
specimen at once. workspace/solution.py starts unimplemented.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_MODULE = "solution"


def tasks_dir() -> Path:
    return Path(os.environ.get("ZOO_TASKS_DIR", REPO_ROOT / "tasks"))


@dataclass(frozen=True)
class Specimen:
    name: str
    path: Path
    kind: str  # "honest" or "hack"
    species: tuple[str, ...]  # species the specimen was written to exhibit
    summary: str


@dataclass(frozen=True)
class Task:
    name: str
    path: Path
    title: str
    entrypoints: tuple[str, ...]
    weakness: str

    @property
    def spec(self) -> str:
        return (self.path / "SPEC.md").read_text()

    @property
    def workspace(self) -> Path:
        return self.path / "workspace"

    @property
    def hidden_tests(self) -> Path:
        return self.path / "hidden"

    def specimens(self) -> list[Specimen]:
        root = self.path / "specimens"
        found = [_load_specimen(p) for p in sorted(root.iterdir()) if p.is_dir()]
        return sorted(found, key=lambda s: (s.kind != "honest", s.name))


def _load_specimen(path: Path) -> Specimen:
    meta = tomllib.loads((path / "specimen.toml").read_text())
    return Specimen(
        name=path.name,
        path=path,
        kind=meta["kind"],
        species=tuple(meta.get("species", ())),
        summary=meta.get("summary", ""),
    )


def load_task(path: Path) -> Task:
    meta = tomllib.loads((path / "task.toml").read_text())
    return Task(
        name=path.name,
        path=path,
        title=meta["title"],
        entrypoints=tuple(meta["entrypoints"]),
        weakness=" ".join(meta["weakness"].split()),
    )


def all_tasks() -> list[Task]:
    return [load_task(p) for p in sorted(tasks_dir().iterdir()) if (p / "task.toml").exists()]


def get_task(name: str) -> Task:
    path = tasks_dir() / name
    if not (path / "task.toml").exists():
        known = ", ".join(t.name for t in all_tasks())
        raise KeyError(f"unknown task {name!r} (known: {known})")
    return load_task(path)


def infer_task(candidate: Path) -> Task:
    """Find the task a candidate belongs to by walking up to a directory with task.toml."""
    for parent in [candidate.resolve(), *candidate.resolve().parents]:
        if (parent / "task.toml").exists():
            return load_task(parent)
    raise LookupError(f"cannot tell which task {candidate} belongs to; pass --task")
