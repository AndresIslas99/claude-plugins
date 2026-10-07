We want to put shipments that travel the same lane onto shared trucks. Please add a new module, `freightlib/consolidation.py`, with the contract below.

Two frozen dataclasses:

- `Load(shipment_id: str, origin: str, destination: str, weight_lb: float)`
- `Truck(origin: str, destination: str, loads: Tuple[Load, ...])`, with a read-only property `total_weight_lb` that returns the sum of the weights of its loads

And one function, `consolidate(loads, capacity_lb)`. It takes a sequence of `Load` and the capacity of one truck in pounds, and returns a `list` of `Truck`. The rules:

- A lane is the pair (origin, destination). Place names are compared ignoring case and surrounding whitespace, so `" dallas "` and `"DALLAS"` are the same place. A truck's `origin` and `destination` hold the trimmed, upper-case names.
- Loads only share a truck when they are on the same lane. Dallas to Austin and Austin to Dallas are different lanes.
- Go through the loads in the order given. Put each load on the earliest-opened truck of its lane that still has room for it, which means the truck's total weight plus the load's weight is at most `capacity_lb` (reaching the capacity exactly is fine). If no truck on the lane has room, open a new truck on that lane with this load. Do not reorder the loads to pack them tighter, even when that would need fewer trucks.
- Inside a truck, `loads` keeps the order in which the loads were placed. The trucks hold the same `Load` objects that were passed in, not changed copies.
- The result is sorted by lane: origin first, then destination, comparing the trimmed, upper-case names in ascending order. Trucks on the same lane stay in the order they were opened.
- No loads gives an empty list. The input sequence is not modified.

Validation happens before anything is packed, and the first problem found raises `ValueError` with one of these exact messages. First check the capacity, then check each load in the order given:

- `"capacity must be positive"` when `capacity_lb` is zero, negative or NaN. This applies even when there are no loads.
- `"weight must be positive for load <shipment_id>"` when a load's weight is zero, negative or NaN
- `"load <shipment_id> exceeds capacity"` when a load's weight is more than `capacity_lb` (a load that weighs exactly the capacity is fine)

Export `Load`, `Truck` and `consolidate` from `freightlib/__init__.py` and add them to `__all__`.
