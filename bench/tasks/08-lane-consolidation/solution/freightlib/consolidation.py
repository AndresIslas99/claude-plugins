"""Consolidating shipments onto shared trucks, lane by lane."""

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class Load:
    """A shipment waiting for a truck."""

    shipment_id: str
    origin: str
    destination: str
    weight_lb: float


@dataclass(frozen=True)
class Truck:
    """A truck on one lane and the loads placed on it, in placement order."""

    origin: str
    destination: str
    loads: Tuple[Load, ...]

    @property
    def total_weight_lb(self) -> float:
        """Return the combined weight of the loads on the truck."""
        return sum(item.weight_lb for item in self.loads)


def _place(name: str) -> str:
    """Normalize a place name: trimmed and upper case."""
    return name.strip().upper()


def consolidate(loads: Sequence[Load], capacity_lb: float) -> List[Truck]:
    """Put loads that travel the same lane onto shared trucks.

    Loads are taken in the order given. Each goes on the earliest-opened truck of
    its lane that still has room, or on a new truck when none has. The result is
    sorted by lane, and trucks on one lane stay in the order they were opened.
    Raises ``ValueError`` for a bad capacity or a load that cannot be placed.
    """
    if not capacity_lb > 0:
        raise ValueError("capacity must be positive")
    for item in loads:
        if not item.weight_lb > 0:
            raise ValueError(f"weight must be positive for load {item.shipment_id}")
        if item.weight_lb > capacity_lb:
            raise ValueError(f"load {item.shipment_id} exceeds capacity")

    placed: Dict[Tuple[str, str], List[List[Load]]] = {}
    for item in loads:
        lane = (_place(item.origin), _place(item.destination))
        trucks = placed.setdefault(lane, [])
        for truck_loads in trucks:
            used = sum(other.weight_lb for other in truck_loads)
            if used + item.weight_lb <= capacity_lb:
                truck_loads.append(item)
                break
        else:
            trucks.append([item])
    return [
        Truck(lane[0], lane[1], tuple(truck_loads))
        for lane in sorted(placed)
        for truck_loads in placed[lane]
    ]
