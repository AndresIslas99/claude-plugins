We want to put transfer jobs that travel the same route onto shared batches. Please add a new module, `transferlib/consolidation.py`, with the contract below.

Two frozen dataclasses:

- `Job(job_id: str, source: str, target: str, size_gb: float)`
- `Batch(source: str, target: str, jobs: Tuple[Job, ...])`, with a read-only property `total_size_gb` that returns the sum of the sizes of its jobs

And one function, `consolidate(jobs, capacity_gb)`. It takes a sequence of `Job` and the capacity of one batch in gigabytes, and returns a `list` of `Batch`. The rules:

- A route is the pair (source, target). Region names are compared ignoring case and surrounding whitespace, so `" us-east-1 "` and `"US-EAST-1"` are the same region. A batch's `source` and `target` hold the trimmed, upper-case names.
- Jobs only share a batch when they are on the same route. us-east-1 to eu-west-1 and eu-west-1 to us-east-1 are different routes.
- Go through the jobs in the order given. Put each job into the earliest-opened batch of its route that still has room for it, which means the batch's total size plus the job's size is at most `capacity_gb` (reaching the capacity exactly is fine). If no batch on the route has room, open a new batch on that route with this job. Do not reorder the jobs to pack them tighter, even when that would need fewer batches.
- Inside a batch, `jobs` keeps the order in which the jobs were placed. The batches hold the same `Job` objects that were passed in, not changed copies.
- The result is sorted by route: source first, then target, comparing the trimmed, upper-case names in ascending order. Batches on the same route stay in the order they were opened.
- No jobs gives an empty list. The input sequence is not modified.

Validation happens before anything is packed, and the first problem found raises `ValueError` with one of these exact messages. First check the capacity, then check each job in the order given:

- `"capacity must be positive"` when `capacity_gb` is zero, negative or NaN. This applies even when there are no jobs.
- `"size must be positive for job <job_id>"` when a job's size is zero, negative or NaN
- `"job <job_id> exceeds capacity"` when a job's size is more than `capacity_gb` (a job whose size is exactly the capacity is fine)

Export `Job`, `Batch` and `consolidate` from `transferlib/__init__.py` and add them to `__all__`.
