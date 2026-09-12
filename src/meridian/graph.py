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
        return self._traverse(name, depth, "depends_on")

    def dependents(self, name: str, depth: int | None = None) -> set[str]:
        """Services that depend on `name`, transitively up to `depth` hops."""
        return self._traverse(name, depth, "depended_on_by")

    def _traverse(self, name: str, depth: int | None, attr: str) -> set[str]:
        if name not in self._catalog:
            raise KeyError(f"unknown service: {name!r}")

        visited: set[str] = set()
        frontier = {name}
        hops = 0

        while frontier and (depth is None or hops < depth):
            next_frontier: set[str] = set()
            for node in frontier:
                for neighbor in getattr(self._catalog[node], attr):
                    if neighbor not in visited and neighbor != name:
                        visited.add(neighbor)
                        next_frontier.add(neighbor)
            frontier = next_frontier
            hops += 1

        return visited
