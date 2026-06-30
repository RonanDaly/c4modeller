import unittest

from PySide6.QtCore import QRectF

from c4modeller.gui import (
    ROUTE_MARGIN,
    fallback_route_points,
    relationship_obstacle_ids,
    route_orthogonal_path,
    segment_crosses_rect,
)
from c4modeller.model import ElementType, Workspace


class RoutingTests(unittest.TestCase):
    def test_orthogonal_route_avoids_obstacles(self) -> None:
        source = QRectF(0, 0, 100, 80)
        target = QRectF(320, 0, 100, 80)
        obstacle = QRectF(180, -20, 80, 120)

        path = route_orthogonal_path(source, target, [obstacle])

        self.assertIsNotNone(path)
        assert path is not None
        keepout = obstacle.adjusted(-ROUTE_MARGIN, -ROUTE_MARGIN, ROUTE_MARGIN, ROUTE_MARGIN)
        for start, end in zip(path, path[1:]):
            self.assertFalse(
                segment_crosses_rect(
                    (start.x(), start.y()),
                    (end.x(), end.y()),
                    keepout,
                )
            )

    def test_orthogonal_route_can_route_between_children_inside_parent(self) -> None:
        source = QRectF(90, 210, 220, 120)
        target = QRectF(390, 210, 220, 120)
        sibling_obstacle = QRectF(240, 190, 80, 160)

        path = route_orthogonal_path(source, target, [sibling_obstacle])

        self.assertIsNotNone(path)
        assert path is not None
        keepout = sibling_obstacle.adjusted(
            -ROUTE_MARGIN,
            -ROUTE_MARGIN,
            ROUTE_MARGIN,
            ROUTE_MARGIN,
        )
        for start, end in zip(path, path[1:]):
            self.assertFalse(
                segment_crosses_rect(
                    (start.x(), start.y()),
                    (end.x(), end.y()),
                    keepout,
                )
            )

    def test_fallback_route_is_orthogonal(self) -> None:
        source = QRectF(0, 0, 100, 80)
        target = QRectF(320, 120, 100, 80)

        path = fallback_route_points(source, target)

        self.assertGreaterEqual(len(path), 2)
        for start, end in zip(path, path[1:]):
            self.assertTrue(start.x() == end.x() or start.y() == end.y())

    def test_relationship_obstacles_exclude_endpoint_ancestors(self) -> None:
        workspace = Workspace()
        system = workspace.add_element("Shop", ElementType.SOFTWARE_SYSTEM)
        api = workspace.add_element("API", ElementType.CONTAINER, parent_id=system.id)
        database = workspace.add_element(
            "Database",
            ElementType.CONTAINER,
            parent_id=system.id,
        )
        cache = workspace.add_element("Cache", ElementType.CONTAINER, parent_id=system.id)
        workspace.set_expanded(system.id, True)

        obstacle_ids = relationship_obstacle_ids(workspace, api.id, database.id)

        self.assertNotIn(system.id, obstacle_ids)
        self.assertNotIn(api.id, obstacle_ids)
        self.assertNotIn(database.id, obstacle_ids)
        self.assertIn(cache.id, obstacle_ids)


if __name__ == "__main__":
    unittest.main()
