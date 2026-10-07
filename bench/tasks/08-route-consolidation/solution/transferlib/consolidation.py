"""Consolidating transfer jobs onto shared batches, route by route."""

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class Job:
    """A transfer job waiting for a batch."""

    job_id: str
    source: str
    target: str
    size_gb: float


@dataclass(frozen=True)
class Batch:
    """A batch on one route and the jobs placed in it, in placement order."""

    source: str
    target: str
    jobs: Tuple[Job, ...]

    @property
    def total_size_gb(self) -> float:
        """Return the combined size of the jobs in the batch."""
        return sum(item.size_gb for item in self.jobs)


def _region(name: str) -> str:
    """Normalize a region name: trimmed and upper case."""
    return name.strip().upper()


def consolidate(jobs: Sequence[Job], capacity_gb: float) -> List[Batch]:
    """Put jobs that travel the same route onto shared batches.

    Jobs are taken in the order given. Each goes into the earliest-opened batch of
    its route that still has room, or into a new batch when none has. The result is
    sorted by route, and batches on one route stay in the order they were opened.
    Raises ``ValueError`` for a bad capacity or a job that cannot be placed.
    """
    if not capacity_gb > 0:
        raise ValueError("capacity must be positive")
    for item in jobs:
        if not item.size_gb > 0:
            raise ValueError(f"size must be positive for job {item.job_id}")
        if item.size_gb > capacity_gb:
            raise ValueError(f"job {item.job_id} exceeds capacity")

    placed: Dict[Tuple[str, str], List[List[Job]]] = {}
    for item in jobs:
        route = (_region(item.source), _region(item.target))
        batches = placed.setdefault(route, [])
        for batch_jobs in batches:
            used = sum(other.size_gb for other in batch_jobs)
            if used + item.size_gb <= capacity_gb:
                batch_jobs.append(item)
                break
        else:
            batches.append([item])
    return [
        Batch(route[0], route[1], tuple(batch_jobs))
        for route in sorted(placed)
        for batch_jobs in placed[route]
    ]
