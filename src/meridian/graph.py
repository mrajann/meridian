"""Dependency graph traversal over a service catalog."""

from __future__ import annotations

from meridian.catalog import ServiceEntry


class DependencyGraph:
    """Traverses depends_on / depended_on_by edges across a service catalog.

    Traversal is breadth-first and tracks visited nodes, so a cycle in the
    data (which shouldn't exist, but catalog files are hand-authored) cannot
    cause an infinite loop.
    """

    def __init__(self, catalog: dict[str, ServiceEntry]) -> None:
        self._catalog = catalog

    def dependencies(self, name: str, depth: int | None = None) -> set[str]:
        """Services `name` depends on, transitively up to `depth` hops.

        depth=None (the default) walks the full transitive closure, which is
        what cascade detection needs: postgres-primary's full blast radius,
        not just its direct callers.
        """
        return set(self._hops(name, depth, "depends_on"))

    def dependents(self, name: str, depth: int | None = None) -> set[str]:
        """Services that depend on `name`, transitively up to `depth` hops."""
        return set(self._hops(name, depth, "depended_on_by"))

    def dependencies_with_hops(self, name: str, depth: int | None = None) -> dict[str, int]:
        """Like dependencies(), but maps each service to its shortest hop
        distance from `name` (1 = direct)."""
        return self._hops(name, depth, "depends_on")

    def dependents_with_hops(self, name: str, depth: int | None = None) -> dict[str, int]:
        """Like dependents(), but maps each service to its shortest hop
        distance from `name` (1 = direct)."""
        return self._hops(name, depth, "depended_on_by")

    def _hops(self, name: str, depth: int | None, attr: str) -> dict[str, int]:
        if name not in self._catalog:
            raise KeyError(f"unknown service: {name!r}")

        distance: dict[str, int] = {}
        frontier = {name}
        hops = 0

        while frontier and (depth is None or hops < depth):
            hops += 1
            next_frontier: set[str] = set()
            for node in frontier:
                for neighbor in getattr(self._catalog[node], attr):
                    if neighbor not in distance and neighbor != name:
                        distance[neighbor] = hops
                        next_frontier.add(neighbor)
            frontier = next_frontier

        return distance
