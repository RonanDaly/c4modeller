import unittest

from PySide6.QtCore import QRectF

from c4modeller.gui import (
    ROUTE_MAX_PORTS_PER_SIDE,
    ROUTE_MARGIN,
    candidate_ports_for,
    fallback_route_points,
    path_segments,
    relationship_obstacle_ids,
    route_orthogonal_path,
    segment_overlap_length,
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

    def test_candidate_ports_include_multiple_positions_per_side(self) -> None:
        rect = QRectF(0, 0, 220, 120)

        ports = candidate_ports_for(rect)

        left_side_y_values = {
            anchor.y()
            for anchor, outlet in ports
            if anchor.x() == rect.left() and outlet.x() < anchor.x()
        }
        top_side_x_values = {
            anchor.x()
            for anchor, outlet in ports
            if anchor.y() == rect.top() and outlet.y() < anchor.y()
        }
        self.assertGreater(len(left_side_y_values), 1)
        self.assertGreater(len(top_side_x_values), 1)

    def test_candidate_ports_are_capped_per_side(self) -> None:
        rect = QRectF(0, 0, 1200, 900)

        ports = candidate_ports_for(rect)

        left_side_y_values = {
            anchor.y()
            for anchor, outlet in ports
            if anchor.x() == rect.left() and outlet.x() < anchor.x()
        }
        bottom_side_x_values = {
            anchor.x()
            for anchor, outlet in ports
            if anchor.y() == rect.bottom() and outlet.y() > anchor.y()
        }
        self.assertLessEqual(len(left_side_y_values), ROUTE_MAX_PORTS_PER_SIDE)
        self.assertLessEqual(len(bottom_side_x_values), ROUTE_MAX_PORTS_PER_SIDE)

    def test_second_route_prefers_different_ports_or_segments(self) -> None:
        source = QRectF(0, 0, 120, 100)
        target = QRectF(360, 0, 120, 100)
        first_path = route_orthogonal_path(source, target, [])
        self.assertIsNotNone(first_path)
        assert first_path is not None

        second_path = route_orthogonal_path(
            source,
            target,
            [],
            occupied_segments=path_segments(first_path),
            occupied_ports=[first_path[0], first_path[-1]],
        )

        self.assertIsNotNone(second_path)
        assert second_path is not None
        self.assertNotEqual(
            (second_path[0].x(), second_path[0].y()),
            (first_path[0].x(), first_path[0].y()),
        )
        total_overlap = sum(
            segment_overlap_length(
                (start.x(), start.y()),
                (end.x(), end.y()),
                (used_start.x(), used_start.y()),
                (used_end.x(), used_end.y()),
            )
            for start, end in path_segments(second_path)
            for used_start, used_end in path_segments(first_path)
        )
        self.assertEqual(total_overlap, 0)

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
