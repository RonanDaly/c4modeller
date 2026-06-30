from __future__ import annotations

import math
from heapq import heappop, heappush
from itertools import count
from pathlib import Path

from PySide6.QtCore import QLineF, QMarginsF, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QPageLayout,
    QPageSize,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPdfWriter,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabBar,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .model import C4Element, ElementLayout, ElementType, Workspace
from .storage import load_workspace, save_workspace


TYPE_COLORS = {
    ElementType.ORGANIZATIONAL_BOUNDARY: QColor("#546a7b"),
    ElementType.PERSON: QColor("#f4a261"),
    ElementType.SOFTWARE_SYSTEM: QColor("#2a9d8f"),
    ElementType.CONTAINER: QColor("#457b9d"),
    ElementType.COMPONENT: QColor("#6d597a"),
    ElementType.DEPLOYMENT_NODE: QColor("#6a4c93"),
    ElementType.INFRASTRUCTURE_NODE: QColor("#8d6e63"),
}

BOUNDARY_TYPES = {
    ElementType.ORGANIZATIONAL_BOUNDARY,
    ElementType.PERSON,
    ElementType.SOFTWARE_SYSTEM,
    ElementType.CONTAINER,
    ElementType.COMPONENT,
    ElementType.DEPLOYMENT_NODE,
    ElementType.INFRASTRUCTURE_NODE,
}
COLLAPSIBLE_TYPES = {
    ElementType.SOFTWARE_SYSTEM,
    ElementType.CONTAINER,
    ElementType.DEPLOYMENT_NODE,
}
DESCRIPTION_TYPES = {
    ElementType.PERSON,
    ElementType.SOFTWARE_SYSTEM,
    ElementType.CONTAINER,
    ElementType.COMPONENT,
}
SUBTYPE_TYPES = {
    ElementType.CONTAINER,
    ElementType.COMPONENT,
    ElementType.DEPLOYMENT_NODE,
    ElementType.INFRASTRUCTURE_NODE,
}
LEAF_SUMMARY_TYPES = {
    ElementType.PERSON,
    ElementType.INFRASTRUCTURE_NODE,
}
CONTAINMENT_MARGIN = 18.0
CONTAINMENT_TOP_MARGIN = 54.0
ROUTE_MARGIN = 24.0
ROUTE_OUTLET = 18.0
ROUTE_BEND_PENALTY = 30.0


class ElementItem(QGraphicsRectItem):
    HANDLE_SIZE = 12.0
    HIT_TOLERANCE = 8.0
    MIN_WIDTH = 120.0
    MIN_HEIGHT = 70.0
    COLLAPSED_MIN_WIDTH = 180.0
    COLLAPSED_MAX_WIDTH = 380.0
    COLLAPSED_PADDING = 14.0

    def __init__(
        self,
        element: C4Element,
        layout: ElementLayout,
        main_window: MainWindow,
    ) -> None:
        super().__init__(0, 0, layout.width, layout.height)
        self.element = element
        self.layout = layout
        self.main_window = main_window
        self.resizing = False
        self.setPos(layout.x, layout.y)
        color = TYPE_COLORS[element.type]
        if self.is_filled_box():
            self.setBrush(QBrush(QColor("#ffffff")))
            self.setPen(QPen(color, 3))
        elif element.type in BOUNDARY_TYPES:
            self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            self.setPen(QPen(color, 3))
        else:
            self.setBrush(QBrush(color))
            self.setPen(QPen(QColor("#263238"), 2))
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(10 + main_window.element_depth(element.id) * 10)

        self.title = QGraphicsTextItem(element.name, self)
        self.title.setAcceptedMouseButtons(Qt.NoButton)
        label_color = QColor("#263238") if element.type in BOUNDARY_TYPES else QColor("#ffffff")
        self.title.setDefaultTextColor(label_color)
        self.title.setFont(self.title_font())

        self.subtitle = QGraphicsTextItem(self._subtitle_text(), self)
        self.subtitle.setAcceptedMouseButtons(Qt.NoButton)
        self.subtitle.setDefaultTextColor(
            QColor("#455a64") if element.type in BOUNDARY_TYPES else QColor("#eef6f6")
        )
        self.subtitle.setFont(self.subtitle_font())

        self.description = QGraphicsTextItem(element.description, self)
        self.description.setAcceptedMouseButtons(Qt.NoButton)
        self.description.setDefaultTextColor(QColor("#263238"))
        self.description.setFont(self.description_font())
        if self.is_collapsed():
            width, height = main_window.visible_size_for(element.id)
            self.setRect(0, 0, width, height)
        self._position_labels()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        super().paint(painter, option, widget)
        rect = self.rect()
        if self.can_resize():
            painter.setPen(QPen(QColor("#455a64"), 1))
            painter.setBrush(QBrush(QColor(255, 255, 255, 140)))
            painter.drawRect(self._handle_rect())
        if (
            self.element.type in COLLAPSIBLE_TYPES
            and not self.main_window.workspace.is_expanded(self.element.id)
        ):
            painter.setPen(QPen(QColor("#263238"), 1))
            painter.setFont(QFont("Arial", 10, QFont.Bold))
            painter.drawText(rect.adjusted(8, 8, -8, -8), Qt.AlignRight | Qt.AlignTop, "+")

    def shape(self) -> QPainterPath:
        outline = QPainterPath()
        outline.addRect(self.rect())
        if self.is_filled_box():
            return outline
        stroker = QPainterPathStroker()
        stroker.setWidth(self.HIT_TOLERANCE * 2 + max(1, self.pen().width()))
        shape = stroker.createStroke(outline)
        if self.can_resize():
            shape.addRect(self._handle_rect().adjusted(
                -self.HIT_TOLERANCE,
                -self.HIT_TOLERANCE,
                self.HIT_TOLERANCE,
                self.HIT_TOLERANCE,
            ))
        return shape

    def itemChange(self, change, value):
        if (
            change == QGraphicsItem.ItemPositionChange
            and not self.main_window.syncing_layout
        ):
            return self.main_window.constrained_position(self, value)
        if change == QGraphicsItem.ItemPositionHasChanged:
            old_position = QPointF(self.layout.x, self.layout.y)
            delta = self.pos() - old_position
            self.layout.x = self.pos().x()
            self.layout.y = self.pos().y()
            if (
                not self.main_window.syncing_layout
                and (delta.x() or delta.y())
            ):
                self.main_window.move_descendants(self.element.id, delta)
            self.main_window.refresh_edges()
        return super().itemChange(change, value)

    def mousePressEvent(self, event) -> None:
        if self.can_resize() and self._handle_rect().contains(event.pos()):
            self.resizing = True
            event.accept()
            return
        if self.main_window.connect_mode:
            self.main_window.handle_connect_click(self.element.id)
            event.accept()
            return
        if self.main_window.move_mode:
            self.main_window.handle_move_click(self.element.id)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self.resizing:
            width, height = self.main_window.constrained_size(
                self,
                max(self.MIN_WIDTH, event.pos().x()),
                max(self.MIN_HEIGHT, event.pos().y()),
            )
            self.prepareGeometryChange()
            self.setRect(0, 0, width, height)
            self.main_window.set_visible_size_for(self.element.id, width, height)
            self._position_labels()
            self.main_window.refresh_edges()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self.resizing:
            self.resizing = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def hoverMoveEvent(self, event) -> None:
        if self.can_resize() and self._handle_rect().contains(event.pos()):
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def _handle_rect(self) -> QRectF:
        rect = self.rect()
        return QRectF(
            rect.right() - self.HANDLE_SIZE,
            rect.bottom() - self.HANDLE_SIZE,
            self.HANDLE_SIZE,
            self.HANDLE_SIZE,
        )

    def _position_labels(self) -> None:
        rect = self.rect()
        if self.element.type == ElementType.ORGANIZATIONAL_BOUNDARY:
            self.title.setTextWidth(max(40, rect.width() - 20))
            self.title.setPos(10, 12)
            self.subtitle.setVisible(False)
            self.description.setVisible(False)
            return
        summary_layout = self.is_collapsed() or self.element.type in LEAF_SUMMARY_TYPES
        self.title.setTextWidth(max(40, rect.width() - 20))
        self.title.setPos(10, 12)
        self.subtitle.setVisible(True)
        self.subtitle.setTextWidth(max(40, rect.width() - 20))
        self.subtitle.setPos(10, 34 if summary_layout else min(rect.height() - 32, 42))
        self.description.setTextWidth(max(40, rect.width() - 20))
        self.description.setPos(10, 58 if summary_layout else 68)
        self.description.setVisible(
            bool(self.element.description.strip())
            and (
                self.element.type == ElementType.PERSON
                or (
                    self.element.type in COLLAPSIBLE_TYPES
                    and not self.main_window.workspace.is_expanded(self.element.id)
                )
            )
        )

    def is_collapsed(self) -> bool:
        return (
            self.element.type in COLLAPSIBLE_TYPES
            and not self.main_window.workspace.is_expanded(self.element.id)
        )

    def can_resize(self) -> bool:
        return True

    def is_filled_box(self) -> bool:
        return (
            self.element.type
            in {
                ElementType.PERSON,
                ElementType.COMPONENT,
                ElementType.INFRASTRUCTURE_NODE,
            }
            or self.is_collapsed()
        )

    def _collapsed_size(self) -> tuple[float, float]:
        return self.preferred_summary_size(self.element)

    @classmethod
    def preferred_summary_size(cls, element: C4Element) -> tuple[float, float]:
        title_metrics = QFontMetrics(cls.title_font())
        subtitle_metrics = QFontMetrics(cls.subtitle_font())
        description_metrics = QFontMetrics(cls.description_font())
        description = element.description.strip()
        title_width = title_metrics.horizontalAdvance(element.name)
        subtitle_width = subtitle_metrics.horizontalAdvance(subtitle_text_for(element))
        description_width = max(
            [description_metrics.horizontalAdvance(line) for line in description.splitlines()]
            or [0]
        )
        width = max(
            cls.COLLAPSED_MIN_WIDTH,
            min(
                cls.COLLAPSED_MAX_WIDTH,
                max(
                    title_width,
                    subtitle_width,
                    min(description_width, cls.COLLAPSED_MAX_WIDTH - 40),
                )
                + cls.COLLAPSED_PADDING * 2,
            ),
        )
        description_width_for_wrap = max(60.0, width - cls.COLLAPSED_PADDING * 2)
        description_rect = description_metrics.boundingRect(
            QRectF(0, 0, description_width_for_wrap, 1000).toRect(),
            Qt.TextWordWrap,
            description,
        )
        description_height = description_rect.height() if description else 0
        height = max(
            cls.MIN_HEIGHT,
            60 + description_height + cls.COLLAPSED_PADDING,
        )
        return width, height

    @staticmethod
    def title_font() -> QFont:
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        return font

    @staticmethod
    def subtitle_font() -> QFont:
        font = QFont()
        font.setPointSize(8)
        return font

    @staticmethod
    def description_font() -> QFont:
        font = QFont()
        font.setPointSize(9)
        return font

    def _subtitle_text(self) -> str:
        return subtitle_text_for(self.element)


class RelationshipPathItem(QGraphicsPathItem):
    HIT_TOLERANCE = 10.0

    def shape(self) -> QPainterPath:
        stroker = QPainterPathStroker()
        stroker.setWidth(self.HIT_TOLERANCE)
        return stroker.createStroke(self.path())


class RelationshipItem:
    def __init__(
        self,
        source: ElementItem,
        target: ElementItem,
        relationship_id: str,
        label: str,
        obstacles: list[QRectF] | None = None,
    ) -> None:
        self.relationship_id = relationship_id
        self.path_item = RelationshipPathItem()
        self.path_item.setPen(QPen(QColor("#37474f"), 2, Qt.SolidLine, Qt.RoundCap))
        self.path_item.setZValue(1)
        self.arrow_item = QGraphicsPolygonItem()
        self.arrow_item.setBrush(QBrush(QColor("#37474f")))
        self.arrow_item.setPen(QPen(QColor("#37474f")))
        self.arrow_item.setZValue(2)
        self.label_item = QGraphicsTextItem(label)
        self.label_item.setDefaultTextColor(QColor("#263238"))
        self.label_item.setFont(QFont("Arial", 8))
        self.label_item.setZValue(3)
        for item in [self.path_item, self.arrow_item, self.label_item]:
            item.setFlag(QGraphicsItem.ItemIsSelectable, True)
            item.setData(0, "relationship")
            item.setData(1, relationship_id)
        self.update(source, target, obstacles or [])

    def add_to_scene(self, scene: QGraphicsScene) -> None:
        scene.addItem(self.path_item)
        scene.addItem(self.arrow_item)
        if self.label_item.toPlainText():
            scene.addItem(self.label_item)

    def remove_from_scene(self, scene: QGraphicsScene) -> None:
        for item in [self.path_item, self.arrow_item, self.label_item]:
            if item.scene() is scene:
                scene.removeItem(item)

    def update(
        self,
        source: ElementItem,
        target: ElementItem,
        obstacles: list[QRectF] | None = None,
    ) -> None:
        source_rect = source.mapRectToScene(source.rect())
        target_rect = target.mapRectToScene(target.rect())
        points = route_orthogonal_path(source_rect, target_rect, obstacles or [])
        if points is None:
            points = fallback_route_points(source_rect, target_rect)
        end = points[-1]
        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)
        before_end = points[-2] if len(points) > 1 else points[0]
        label_position = label_position_for_path(points)
        self.path_item.setPath(path)
        self.arrow_item.setPolygon(arrow_head(start=before_end, end=end))
        self.label_item.setPos(label_position)


class GridScene(QGraphicsScene):
    MINOR_GRID_SIZE = 20
    MAJOR_GRID_SIZE = 100

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.show_grid = True

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.fillRect(rect, QColor("#f7f9fa") if self.show_grid else QColor("#ffffff"))
        if not self.show_grid:
            return
        self._draw_grid(
            painter,
            rect,
            self.MINOR_GRID_SIZE,
            QColor("#e3e8eb"),
            1,
        )
        self._draw_grid(
            painter,
            rect,
            self.MAJOR_GRID_SIZE,
            QColor("#ccd6dc"),
            1,
        )

    def _draw_grid(
        self,
        painter: QPainter,
        rect: QRectF,
        grid_size: int,
        color: QColor,
        width: int,
    ) -> None:
        left = math.floor(rect.left() / grid_size) * grid_size
        top = math.floor(rect.top() / grid_size) * grid_size
        lines: list[QLineF] = []
        x = left
        while x < rect.right():
            lines.append(QLineF(x, rect.top(), x, rect.bottom()))
            x += grid_size
        y = top
        while y < rect.bottom():
            lines.append(QLineF(rect.left(), y, rect.right(), y))
            y += grid_size
        painter.setPen(QPen(color, width))
        painter.drawLines(lines)


class DiagramView(QGraphicsView):
    def __init__(self, scene: QGraphicsScene) -> None:
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self._panning = False
        self._last_pan_point = QPointF()

    def wheelEvent(self, event) -> None:
        factor = 1.05 if event.angleDelta().y() > 0 else 1 / 1.05
        self.scale(factor, factor)

    def mousePressEvent(self, event) -> None:
        if (
            event.button() == Qt.LeftButton
            and self._interactive_item_at(event.pos()) is None
        ):
            self._panning = True
            self._last_pan_point = event.position()
            self.viewport().setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            delta = event.position() - self._last_pan_point
            self._last_pan_point = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._panning and event.button() == Qt.LeftButton:
            self._panning = False
            self.viewport().setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _interactive_item_at(self, position) -> QGraphicsItem | None:
        scene_position = self.mapToScene(position)
        for item in self.items(position):
            if item.data(0) == "relationship":
                return item
            if isinstance(item, ElementItem):
                return item
            parent = item.parentItem()
            if isinstance(parent, ElementItem):
                parent_position = parent.mapFromScene(scene_position)
                if parent.shape().contains(parent_position):
                    return parent
        return None


class ElementDetailsDialog(QDialog):
    def __init__(
        self,
        type: ElementType,
        parent: QWidget | None = None,
        name: str = "",
        description: str = "",
        subtype: str = "",
        title: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title or f"Add {element_type_label(type)}")
        self.type = type
        self.name_input = QLineEdit(self)
        self.name_input.setText(name)
        self.subtype_input: QLineEdit | None = None
        self.description_input: QTextEdit | None = None

        form = QFormLayout(self)
        form.addRow("Name:", self.name_input)
        if type in SUBTYPE_TYPES:
            self.subtype_input = QLineEdit(self)
            self.subtype_input.setText(subtype)
            form.addRow("Subtype:", self.subtype_input)
        if type in DESCRIPTION_TYPES:
            self.description_input = QTextEdit(self)
            self.description_input.setFixedHeight(90)
            self.description_input.setPlainText(description)
            form.addRow("Description:", self.description_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def details(self) -> tuple[str, str, str]:
        return (
            self.name_input.text().strip(),
            self.subtype_input.text().strip() if self.subtype_input else "",
            self.description_input.toPlainText().strip()
            if self.description_input
            else "",
        )


class RelationshipDetailsDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        description: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Relationship")
        self.description_input = QTextEdit(self)
        self.description_input.setFixedHeight(90)
        self.description_input.setPlainText(description)

        form = QFormLayout(self)
        form.addRow("Description:", self.description_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def description(self) -> str:
        return self.description_input.toPlainText().strip()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.workspace = Workspace()
        self.current_file: Path | None = None
        self.scene = GridScene(self)
        self.scene.setSceneRect(-3000, -3000, 6000, 6000)
        self.view = DiagramView(self.scene)
        self.model_tabs = QTabBar(self)
        self.model_tabs.setExpanding(False)
        self.model_tabs.currentChanged.connect(self.switch_model)
        self.model_tabs.tabBarDoubleClicked.connect(self.edit_model_at_index)
        self.tabs = QTabBar(self)
        self.tabs.setExpanding(False)
        self.tabs.currentChanged.connect(self.switch_view)
        self.tabs.tabBarDoubleClicked.connect(self.edit_view_at_index)
        self.model_tree = QTreeWidget(self)
        self.model_tree.setHeaderLabel("Model Elements")
        self.model_tree.setMinimumWidth(260)
        self.model_tree.itemChanged.connect(self.handle_model_tree_item_changed)
        self.model_tree.itemExpanded.connect(self.handle_model_tree_item_expanded)
        self.model_tree.itemCollapsed.connect(self.handle_model_tree_item_collapsed)
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.addWidget(self.model_tree)
        splitter.addWidget(self.view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.model_tabs)
        layout.addWidget(self.tabs)
        layout.addWidget(splitter)
        self.setCentralWidget(central)
        self.element_items: dict[str, ElementItem] = {}
        self.relationship_items: list[RelationshipItem] = []
        self.connect_mode = False
        self.connect_source_id: str | None = None
        self.connect_action: QAction | None = None
        self.move_mode = False
        self.move_source_id: str | None = None
        self.move_action: QAction | None = None
        self.syncing_layout = False
        self.syncing_model_tree = False
        self._build_toolbar()
        self._seed_example()
        self.refresh_scene()

    def refresh_scene(self) -> None:
        self.enforce_containment()
        self.refresh_model_tabs()
        self.refresh_tabs()
        self.refresh_model_tree()
        self.scene.clear()
        self.element_items.clear()
        self.relationship_items.clear()
        for element in sorted(
            self.workspace.visible_elements(),
            key=lambda item: self.element_depth(item.id),
        ):
            item = ElementItem(
                element=element,
                layout=self.workspace.layout_for(element.id),
                main_window=self,
            )
            self.scene.addItem(item)
            self.element_items[element.id] = item
        self.refresh_edges()
        self._update_title()

    def refresh_edges(self) -> None:
        for relationship_item in self.relationship_items:
            relationship_item.remove_from_scene(self.scene)
        self.relationship_items = []
        for relationship in self.workspace.visible_relationships():
            source = self.element_items.get(relationship.source_id)
            target = self.element_items.get(relationship.target_id)
            if not source or not target:
                continue
            obstacles = [
                item.mapRectToScene(item.rect())
                for element_id, item in self.element_items.items()
                if element_id
                in relationship_obstacle_ids(
                    self.workspace,
                    relationship.source_id,
                    relationship.target_id,
                )
            ]
            item = RelationshipItem(
                source,
                target,
                relationship.id,
                relationship.description,
                obstacles,
            )
            item.add_to_scene(self.scene)
            self.relationship_items.append(item)

    def handle_connect_click(self, element_id: str) -> None:
        if self.connect_source_id is None:
            self.connect_source_id = element_id
            self.statusBar().showMessage("Select the target element")
            return
        if self.connect_source_id == element_id:
            self.statusBar().showMessage("Select a different target element")
            return
        description, ok = QInputDialog.getText(
            self,
            "Relationship",
            "Description:",
            text="uses",
        )
        if ok:
            try:
                self.workspace.add_relationship(
                    self.connect_source_id,
                    element_id,
                    description=description,
                )
            except (KeyError, ValueError) as error:
                QMessageBox.information(self, "Connect Objects", str(error))
            else:
                self.refresh_edges()
        self.connect_source_id = None
        self._set_connect_mode(False)

    def handle_move_click(self, element_id: str) -> None:
        if self.move_source_id is None:
            self.move_source_id = element_id
            self.statusBar().showMessage("Select the new parent element")
            return
        source_id = self.move_source_id
        if source_id == element_id:
            self.statusBar().showMessage("Select a different parent element")
            return

        source_layout = self.workspace.layout_for(source_id)
        old_position = QPointF(source_layout.x, source_layout.y)
        try:
            self.workspace.move_element(source_id, element_id)
        except (KeyError, ValueError) as error:
            QMessageBox.information(self, "Move Object", str(error))
            self.move_source_id = None
            self._set_move_mode(False)
            return

        if not self.workspace.is_expanded(element_id):
            self.workspace.set_expanded(element_id, True)
        self.ensure_layout_inside_parent(source_id)
        new_position = QPointF(source_layout.x, source_layout.y)
        delta = new_position - old_position
        if delta.x() or delta.y():
            self.move_descendants(source_id, delta)
        self.move_source_id = None
        self._set_move_mode(False)
        self.refresh_scene()
        self._select_element(source_id, center=False)

    def add_element(self, type: ElementType) -> None:
        parent_id = self._selected_element_id()
        if type in {ElementType.ORGANIZATIONAL_BOUNDARY, ElementType.PERSON}:
            parent_id = None
        elif type == ElementType.SOFTWARE_SYSTEM:
            if (
                parent_id is None
                or self.workspace.elements[parent_id].type not in {
                    ElementType.ORGANIZATIONAL_BOUNDARY,
                    ElementType.DEPLOYMENT_NODE,
                }
            ):
                parent_id = None
        elif type == ElementType.CONTAINER:
            parent_id = self._require_selected_parent(
                {ElementType.SOFTWARE_SYSTEM, ElementType.DEPLOYMENT_NODE}
            )
        elif type == ElementType.COMPONENT:
            parent_id = self._require_selected_parent({ElementType.CONTAINER})
        elif type == ElementType.DEPLOYMENT_NODE:
            if (
                parent_id is None
                or self.workspace.elements[parent_id].type
                != ElementType.DEPLOYMENT_NODE
            ):
                parent_id = None
        elif type == ElementType.INFRASTRUCTURE_NODE:
            parent_id = self._require_selected_parent({ElementType.DEPLOYMENT_NODE})
        if (
            type
            in {
                ElementType.CONTAINER,
                ElementType.COMPONENT,
                ElementType.INFRASTRUCTURE_NODE,
            }
            and parent_id is None
        ):
            return
        details = self._prompt_element_details(type)
        if details is None:
            return
        name, subtype, description = details
        if parent_id:
            inner_bounds = self.inner_bounds(parent_id)
            x = inner_bounds.left() + CONTAINMENT_MARGIN
            y = inner_bounds.top() + CONTAINMENT_MARGIN
        else:
            center = self.view.mapToScene(self.view.viewport().rect().center())
            x = center.x() - 110
            y = center.y() - 60
        element = self.workspace.add_element(
            name.strip(),
            type,
            parent_id=parent_id,
            x=x,
            y=y,
            description=description,
            subtype=subtype,
        )
        layout = self.workspace.layout_for(element.id)
        if type in LEAF_SUMMARY_TYPES:
            layout.width, layout.height = ElementItem.preferred_summary_size(element)
        elif type in BOUNDARY_TYPES:
            layout.width = 360
            layout.height = 240
        if parent_id:
            if not self.workspace.is_expanded(parent_id):
                self.workspace.set_expanded(parent_id, True)
            self.ensure_layout_inside_parent(element.id)
        self.refresh_scene()
        self._select_element(element.id, center=True)

    def _prompt_element_details(self, type: ElementType) -> tuple[str, str, str] | None:
        if type in {
            ElementType.PERSON,
            ElementType.ORGANIZATIONAL_BOUNDARY,
            ElementType.SOFTWARE_SYSTEM,
            ElementType.CONTAINER,
            ElementType.COMPONENT,
            ElementType.DEPLOYMENT_NODE,
            ElementType.INFRASTRUCTURE_NODE,
        }:
            dialog = ElementDetailsDialog(type, self)
            if dialog.exec() != QDialog.Accepted:
                return None
            name, subtype, description = dialog.details()
            if not name:
                return None
            return name, subtype, description

        name, ok = QInputDialog.getText(
            self,
            f"Add {element_type_label(type)}",
            "Name:",
        )
        if not ok or not name.strip():
            return None
        return name.strip(), "", ""

    def toggle_selected_expansion(self) -> None:
        element_id = self._selected_element_id()
        if element_id is None:
            return
        element = self.workspace.elements[element_id]
        if element.type not in COLLAPSIBLE_TYPES:
            return
        self.workspace.toggle_expanded(element_id)
        self.refresh_scene()
        self._select_element(element_id, center=False)

    def edit_selected_object(self) -> None:
        element_id = self._selected_element_id()
        if element_id is not None:
            self.edit_element(element_id)
            return
        relationship_id = self._selected_relationship_id()
        if relationship_id is not None:
            self.edit_relationship(relationship_id)

    def edit_element(self, element_id: str) -> None:
        element = self.workspace.elements[element_id]
        dialog = ElementDetailsDialog(
            element.type,
            self,
            name=element.name,
            description=element.description,
            subtype=element.subtype,
            title=f"Edit {element_type_label(element.type)}",
        )
        if dialog.exec() != QDialog.Accepted:
            return
        name, subtype, description = dialog.details()
        if not name:
            return
        element.name = name
        element.subtype = subtype
        element.description = description
        self.refresh_scene()
        self._select_element(element_id, center=False)

    def edit_relationship(self, relationship_id: str) -> None:
        relationship = self.workspace.relationships.get(relationship_id)
        if relationship is None:
            return
        dialog = RelationshipDetailsDialog(self, description=relationship.description)
        if dialog.exec() != QDialog.Accepted:
            return
        relationship.description = dialog.description()
        self.refresh_edges()

    def delete_selected(self) -> None:
        element_id = self._selected_element_id()
        if element_id is None:
            return
        element = self.workspace.elements[element_id]
        answer = QMessageBox.question(
            self,
            "Delete Element",
            f"Delete '{element.name}' and its nested elements?",
        )
        if answer != QMessageBox.Yes:
            return
        self.workspace.remove_element(element_id)
        self.refresh_scene()

    def new_workspace(self) -> None:
        self.workspace = Workspace()
        self.current_file = None
        self.refresh_scene()

    def open_workspace(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Workspace",
            "",
            "C4 Workspace (*.json);;All Files (*)",
        )
        if not path:
            return
        self.workspace = load_workspace(path)
        self.current_file = Path(path)
        self.refresh_scene()

    def save_workspace(self) -> None:
        if self.current_file is None:
            self.save_workspace_as()
            return
        save_workspace(self.workspace, self.current_file)
        self.statusBar().showMessage(f"Saved {self.current_file}", 3000)

    def save_workspace_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Workspace",
            "c4-workspace.json",
            "C4 Workspace (*.json);;All Files (*)",
        )
        if not path:
            return
        self.current_file = Path(path)
        self.save_workspace()

    def export_active_view_pdf(self) -> None:
        default_name = f"{self.workspace.active_view().name}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Active View as PDF",
            default_name,
            "PDF Files (*.pdf);;All Files (*)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        self.export_active_view_to_pdf(Path(path))
        self.statusBar().showMessage(f"Exported {path}", 3000)

    def export_active_view_to_pdf(self, path: Path) -> None:
        self.refresh_edges()
        source_rect = self.scene.itemsBoundingRect().adjusted(-80, -80, 80, 80)
        if source_rect.isNull() or source_rect.isEmpty():
            source_rect = QRectF(0, 0, 1000, 700)

        writer = QPdfWriter(str(path))
        writer.setResolution(300)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setPageOrientation(
            QPageLayout.Orientation.Landscape
            if source_rect.width() >= source_rect.height()
            else QPageLayout.Orientation.Portrait
        )
        writer.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)

        painter = QPainter(writer)
        painter.setRenderHint(QPainter.Antialiasing)
        target_rect = QRectF(0, 0, writer.width(), writer.height())
        self.scene.show_grid = False
        try:
            self.scene.render(painter, target_rect, source_rect, Qt.AspectRatioMode.KeepAspectRatio)
        finally:
            self.scene.show_grid = True
        painter.end()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Tools", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        actions = [
            ("New", self.new_workspace),
            ("Open", self.open_workspace),
            ("Save", self.save_workspace),
            ("Save As", self.save_workspace_as),
            ("Export PDF", self.export_active_view_pdf),
            ("Copy Model", self.copy_model),
            ("Edit Model", self.edit_active_model_name),
            ("New View", self.new_view),
            ("Edit View", self.edit_active_view_name),
            ("Delete View", self.delete_view),
            ("Add Person", lambda: self.add_element(ElementType.PERSON)),
            (
                "Add Boundary",
                lambda: self.add_element(ElementType.ORGANIZATIONAL_BOUNDARY),
            ),
            ("Add System", lambda: self.add_element(ElementType.SOFTWARE_SYSTEM)),
            ("Add Container", lambda: self.add_element(ElementType.CONTAINER)),
            ("Add Component", lambda: self.add_element(ElementType.COMPONENT)),
            (
                "Add Deployment",
                lambda: self.add_element(ElementType.DEPLOYMENT_NODE),
            ),
            (
                "Add Infrastructure",
                lambda: self.add_element(ElementType.INFRASTRUCTURE_NODE),
            ),
            ("Expand/Collapse", self.toggle_selected_expansion),
            ("Edit Object", self.edit_selected_object),
            ("Delete", self.delete_selected),
        ]
        for label, callback in actions:
            action = QAction(label, self)
            action.triggered.connect(callback)
            toolbar.addAction(action)
        self.connect_action = QAction("Connect", self)
        self.connect_action.setCheckable(True)
        self.connect_action.triggered.connect(self._set_connect_mode)
        toolbar.addAction(self.connect_action)
        self.move_action = QAction("Move", self)
        self.move_action.setCheckable(True)
        self.move_action.triggered.connect(self._set_move_mode)
        toolbar.addAction(self.move_action)

    def refresh_model_tabs(self) -> None:
        self.model_tabs.blockSignals(True)
        try:
            while self.model_tabs.count():
                self.model_tabs.removeTab(0)
            for model in self.workspace.models:
                self.model_tabs.addTab(f"Model: {model.name}")
            self.model_tabs.setCurrentIndex(self.workspace.model_index())
        finally:
            self.model_tabs.blockSignals(False)

    def switch_model(self, index: int) -> None:
        if index < 0 or index >= len(self.workspace.models):
            return
        self.workspace.set_active_model(self.workspace.models[index].id)
        self.refresh_scene()

    def edit_model_at_index(self, index: int) -> None:
        if index < 0 or index >= len(self.workspace.models):
            return
        self.workspace.set_active_model(self.workspace.models[index].id)
        self.edit_active_model_name()

    def copy_model(self) -> None:
        copied = self.workspace.copy_active_model()
        self.refresh_scene()
        self.statusBar().showMessage(f"Copied model to {copied.name}", 3000)

    def edit_active_model_name(self) -> None:
        model = self.workspace.current_model()
        name, ok = QInputDialog.getText(
            self,
            "Edit Model",
            "Name:",
            text=model.name,
        )
        if not ok or not name.strip():
            return
        self.workspace.rename_active_model(name)
        self.refresh_scene()

    def refresh_model_tree(self) -> None:
        self.syncing_model_tree = True
        self.model_tree.blockSignals(True)
        try:
            self.model_tree.clear()
            for element in self._sorted_children(None):
                self._add_model_tree_item(None, element)
        finally:
            self.model_tree.blockSignals(False)
            self.syncing_model_tree = False

    def _add_model_tree_item(
        self,
        parent_item: QTreeWidgetItem | None,
        element: C4Element,
    ) -> QTreeWidgetItem:
        item = QTreeWidgetItem(parent_item or self.model_tree)
        item.setText(0, tree_text_for(element))
        item.setData(0, Qt.UserRole, element.id)
        item.setFlags(
            item.flags()
            | Qt.ItemIsUserCheckable
            | Qt.ItemIsEnabled
            | Qt.ItemIsSelectable
        )
        item.setCheckState(
            0,
            Qt.Checked if self.workspace.is_element_checked(element.id) else Qt.Unchecked,
        )
        for child in self._sorted_children(element.id):
            self._add_model_tree_item(item, child)
        item.setExpanded(self.workspace.is_tree_expanded(element.id))
        return item

    def _sorted_children(self, parent_id: str | None) -> list[C4Element]:
        return sorted(
            self.workspace.children_of(parent_id),
            key=lambda element: (element.name.lower(), element.type.value),
        )

    def handle_model_tree_item_changed(
        self,
        item: QTreeWidgetItem,
        column: int,
    ) -> None:
        if self.syncing_model_tree or column != 0:
            return
        element_id = item.data(0, Qt.UserRole)
        if not element_id:
            return
        self.workspace.set_element_checked(
            element_id,
            item.checkState(0) == Qt.Checked,
        )
        self.refresh_scene()

    def handle_model_tree_item_expanded(self, item: QTreeWidgetItem) -> None:
        self._set_model_tree_item_expanded(item, True)

    def handle_model_tree_item_collapsed(self, item: QTreeWidgetItem) -> None:
        self._set_model_tree_item_expanded(item, False)

    def _set_model_tree_item_expanded(
        self,
        item: QTreeWidgetItem,
        expanded: bool,
    ) -> None:
        if self.syncing_model_tree:
            return
        element_id = item.data(0, Qt.UserRole)
        if element_id:
            self.workspace.set_tree_expanded(element_id, expanded)

    def refresh_tabs(self) -> None:
        self.tabs.blockSignals(True)
        try:
            while self.tabs.count():
                self.tabs.removeTab(0)
            for view in self.workspace.diagram.views:
                self.tabs.addTab(f"View: {view.name}")
            self.tabs.setCurrentIndex(self.workspace.view_index())
        finally:
            self.tabs.blockSignals(False)

    def switch_view(self, index: int) -> None:
        if index < 0 or index >= len(self.workspace.diagram.views):
            return
        self.workspace.set_active_view(self.workspace.diagram.views[index].id)
        self.refresh_scene()

    def edit_view_at_index(self, index: int) -> None:
        if index < 0 or index >= len(self.workspace.diagram.views):
            return
        self.workspace.set_active_view(self.workspace.diagram.views[index].id)
        self.edit_active_view_name()

    def new_view(self) -> None:
        default_name = f"View {len(self.workspace.diagram.views) + 1}"
        name, ok = QInputDialog.getText(
            self,
            "New View",
            "Name:",
            text=default_name,
        )
        if not ok or not name.strip():
            return
        self.workspace.add_view(name.strip())
        self.refresh_scene()

    def edit_active_view_name(self) -> None:
        view = self.workspace.active_view()
        name, ok = QInputDialog.getText(
            self,
            "Edit View",
            "Name:",
            text=view.name,
        )
        if not ok or not name.strip():
            return
        self.workspace.rename_active_view(name)
        self.refresh_scene()

    def delete_view(self) -> None:
        if len(self.workspace.diagram.views) == 1:
            QMessageBox.information(
                self,
                "Delete View",
                "A workspace must keep at least one view.",
            )
            return
        view = self.workspace.active_view()
        answer = QMessageBox.question(
            self,
            "Delete View",
            f"Delete view '{view.name}'?",
        )
        if answer != QMessageBox.Yes:
            return
        self.workspace.delete_active_view()
        self.refresh_scene()

    def _set_connect_mode(self, enabled: bool) -> None:
        self.connect_mode = enabled
        self.connect_source_id = None
        if enabled:
            self._set_move_mode(False)
        if self.connect_action:
            self.connect_action.setChecked(enabled)
        message = "Select the source element" if enabled else ""
        self.statusBar().showMessage(message)

    def _set_move_mode(self, enabled: bool) -> None:
        self.move_mode = enabled
        self.move_source_id = None
        if enabled:
            self._set_connect_mode(False)
        if self.move_action:
            self.move_action.setChecked(enabled)
        message = "Select the object to move" if enabled else ""
        self.statusBar().showMessage(message)

    def _selected_element_id(self) -> str | None:
        for item in self.scene.selectedItems():
            if isinstance(item, ElementItem):
                return item.element.id
        return None

    def _selected_relationship_id(self) -> str | None:
        for item in self.scene.selectedItems():
            if item.data(0) == "relationship":
                relationship_id = item.data(1)
                if relationship_id in self.workspace.relationships:
                    return relationship_id
        return None

    def element_depth(self, element_id: str) -> int:
        return len(self.workspace.ancestors_of(element_id))

    def descendants_of(self, element_id: str) -> list[C4Element]:
        descendants: list[C4Element] = []
        pending = [element_id]
        while pending:
            parent_id = pending.pop()
            children = self.workspace.children_of(parent_id)
            descendants.extend(children)
            pending.extend(child.id for child in children)
        return descendants

    def inner_bounds(self, parent_id: str) -> QRectF:
        parent_layout = self.workspace.layout_for(parent_id)
        return QRectF(
            parent_layout.x + CONTAINMENT_MARGIN,
            parent_layout.y + CONTAINMENT_TOP_MARGIN,
            max(1.0, parent_layout.width - (CONTAINMENT_MARGIN * 2)),
            max(1.0, parent_layout.height - CONTAINMENT_TOP_MARGIN - CONTAINMENT_MARGIN),
        )

    def constrained_position(self, item: ElementItem, position: QPointF) -> QPointF:
        parent_id = item.element.parent_id
        if parent_id is None:
            return position
        bounds = self.inner_bounds(parent_id)
        rect = item.rect()
        max_x = max(bounds.left(), bounds.right() - rect.width())
        max_y = max(bounds.top(), bounds.bottom() - rect.height())
        return QPointF(
            clamp(position.x(), bounds.left(), max_x),
            clamp(position.y(), bounds.top(), max_y),
        )

    def constrained_size(self, item: ElementItem, width: float, height: float) -> tuple[float, float]:
        if item.is_collapsed() or item.element.type == ElementType.PERSON:
            min_width, min_height = ElementItem.preferred_summary_size(item.element)
        else:
            min_width, min_height = self.minimum_size_for_children(item.element.id)
        width = max(width, min_width)
        height = max(height, min_height)
        if item.element.parent_id:
            bounds = self.inner_bounds(item.element.parent_id)
            width = min(width, max(item.MIN_WIDTH, bounds.right() - item.pos().x()))
            height = min(height, max(item.MIN_HEIGHT, bounds.bottom() - item.pos().y()))
        return width, height

    def minimum_size_for_children(self, element_id: str) -> tuple[float, float]:
        item = self.element_items.get(element_id)
        min_width = item.MIN_WIDTH if item else ElementItem.MIN_WIDTH
        min_height = item.MIN_HEIGHT if item else ElementItem.MIN_HEIGHT
        parent_layout = self.workspace.layout_for(element_id)
        for child in self.workspace.children_of(element_id):
            child_layout = self.workspace.layout_for(child.id)
            child_width, child_height = self.visible_size_for(child.id)
            min_width = max(
                min_width,
                child_layout.x - parent_layout.x
                + child_width
                + CONTAINMENT_MARGIN,
            )
            min_height = max(
                min_height,
                child_layout.y - parent_layout.y
                + child_height
                + CONTAINMENT_MARGIN,
            )
        return min_width, min_height

    def ensure_layout_inside_parent(self, element_id: str) -> None:
        element = self.workspace.elements[element_id]
        if element.parent_id is None:
            return
        layout = self.workspace.layout_for(element_id)
        bounds = self.inner_bounds(element.parent_id)
        visible_width, visible_height = self.visible_size_for(element_id)
        max_x = max(bounds.left(), bounds.right() - visible_width)
        max_y = max(bounds.top(), bounds.bottom() - visible_height)
        layout.x = clamp(layout.x, bounds.left(), max_x)
        layout.y = clamp(layout.y, bounds.top(), max_y)

    def visible_size_for(self, element_id: str) -> tuple[float, float]:
        element = self.workspace.elements[element_id]
        if element.type in COLLAPSIBLE_TYPES and not self.workspace.is_expanded(element.id):
            return (
                self.workspace.collapsed_size_for(element_id)
                or ElementItem.preferred_summary_size(element)
            )
        layout = self.workspace.layout_for(element_id)
        return layout.width, layout.height

    def set_visible_size_for(self, element_id: str, width: float, height: float) -> None:
        element = self.workspace.elements[element_id]
        if element.type in COLLAPSIBLE_TYPES and not self.workspace.is_expanded(element_id):
            self.workspace.set_collapsed_size(element_id, width, height)
            return
        layout = self.workspace.layout_for(element_id)
        layout.width = width
        layout.height = height

    def enforce_containment(self) -> None:
        for element in sorted(
            self.workspace.elements.values(),
            key=lambda item: self.element_depth(item.id),
            reverse=True,
        ):
            min_width, min_height = self.minimum_size_for_children(element.id)
            layout = self.workspace.layout_for(element.id)
            layout.width = max(layout.width, min_width)
            layout.height = max(layout.height, min_height)
        for element in sorted(
            self.workspace.elements.values(),
            key=lambda item: self.element_depth(item.id),
        ):
            self.ensure_layout_inside_parent(element.id)

    def move_descendants(self, element_id: str, delta: QPointF) -> None:
        descendants = self.descendants_of(element_id)
        if not descendants:
            return
        self.syncing_layout = True
        try:
            for descendant in descendants:
                layout = self.workspace.layout_for(descendant.id)
                layout.x += delta.x()
                layout.y += delta.y()
                item = self.element_items.get(descendant.id)
                if item:
                    item.setPos(layout.x, layout.y)
        finally:
            self.syncing_layout = False

    def _require_selected_parent(self, required_types: set[ElementType]) -> str | None:
        required_labels = ", ".join(
            element_type_label(type).lower()
            for type in sorted(required_types, key=lambda item: item.value)
        )
        element_id = self._selected_element_id()
        if element_id is None:
            QMessageBox.information(
                self,
                "Select Parent",
                f"Select a {required_labels} first.",
            )
            return None
        element = self.workspace.elements[element_id]
        if element.type not in required_types:
            QMessageBox.information(
                self,
                "Select Parent",
                f"Selected element must be a {required_labels}.",
            )
            return None
        return element_id

    def _select_element(self, element_id: str, center: bool = False) -> None:
        item = self.element_items.get(element_id)
        if item:
            item.setSelected(True)
            if center:
                self.view.centerOn(item)

    def _update_title(self) -> None:
        suffix = f" - {self.current_file}" if self.current_file else ""
        self.setWindowTitle(
            f"C4 Modeller - {self.workspace.name} - "
            f"{self.workspace.current_model().name}{suffix}"
        )

    def _seed_example(self) -> None:
        system = self.workspace.add_element(
            "Online Shop",
            ElementType.SOFTWARE_SYSTEM,
            x=40,
            y=40,
            description="Customer-facing system for browsing products and placing orders.",
        )
        web = self.workspace.add_element(
            "Web Application",
            ElementType.CONTAINER,
            parent_id=system.id,
            x=90,
            y=210,
            description="Serves the browser UI and handles customer sessions.",
            subtype="Web Application",
        )
        api = self.workspace.add_element(
            "API Application",
            ElementType.CONTAINER,
            parent_id=system.id,
            x=390,
            y=210,
            description="Provides order, catalogue, and checkout APIs.",
            subtype="API Application",
        )
        database = self.workspace.add_element(
            "Database",
            ElementType.CONTAINER,
            parent_id=system.id,
            x=690,
            y=210,
            description="Stores product, customer, and order data.",
            subtype="Database",
        )
        controller = self.workspace.add_element(
            "Order Controller",
            ElementType.COMPONENT,
            parent_id=api.id,
            x=390,
            y=420,
            subtype="Controller",
        )
        service = self.workspace.add_element(
            "Order Service",
            ElementType.COMPONENT,
            parent_id=api.id,
            x=690,
            y=420,
            subtype="Service",
        )
        self.workspace.add_relationship(web.id, api.id, "calls")
        self.workspace.add_relationship(controller.id, service.id, "delegates")
        self.workspace.add_relationship(service.id, database.id, "reads/writes")


def connection_points(source: QRectF, target: QRectF) -> tuple[QPointF, QPointF, str]:
    source_center = source.center()
    target_center = target.center()
    dx = target_center.x() - source_center.x()
    dy = target_center.y() - source_center.y()
    if abs(dx) > abs(dy):
        orientation = "horizontal"
        source_point = QPointF(
            source.right() if dx > 0 else source.left(),
            source_center.y(),
        )
        target_point = QPointF(
            target.left() if dx > 0 else target.right(),
            target_center.y(),
        )
    else:
        orientation = "vertical"
        source_point = QPointF(
            source_center.x(),
            source.bottom() if dy > 0 else source.top(),
        )
        target_point = QPointF(
            target_center.x(),
            target.top() if dy > 0 else target.bottom(),
        )
    return source_point, target_point, orientation


def relationship_obstacle_ids(
    workspace: Workspace,
    source_id: str,
    target_id: str,
) -> set[str]:
    excluded = {source_id, target_id}
    excluded.update(ancestor.id for ancestor in workspace.ancestors_of(source_id))
    excluded.update(ancestor.id for ancestor in workspace.ancestors_of(target_id))
    return {
        element.id
        for element in workspace.visible_elements()
        if element.id not in excluded
    }


def route_orthogonal_path(
    source: QRectF,
    target: QRectF,
    obstacles: list[QRectF],
) -> list[QPointF] | None:
    keepouts = [
        source.adjusted(-1, -1, 1, 1),
        target.adjusted(-1, -1, 1, 1),
    ]
    keepouts.extend(
        obstacle.adjusted(-ROUTE_MARGIN, -ROUTE_MARGIN, ROUTE_MARGIN, ROUTE_MARGIN)
        for obstacle in obstacles
    )
    best_path: list[QPointF] | None = None
    best_score = math.inf
    for source_side in ["left", "right", "top", "bottom"]:
        source_anchor, source_outlet = side_anchor_and_outlet(source, source_side)
        for target_side in ["left", "right", "top", "bottom"]:
            target_anchor, target_outlet = side_anchor_and_outlet(target, target_side)
            routed = orthogonal_grid_route(source_outlet, target_outlet, keepouts)
            if routed is None:
                continue
            path = simplify_path([source_anchor, *routed, target_anchor])
            score = route_score(path)
            if score < best_score:
                best_score = score
                best_path = path
    return best_path


def side_anchor_and_outlet(rect: QRectF, side: str) -> tuple[QPointF, QPointF]:
    center = rect.center()
    if side == "left":
        anchor = QPointF(rect.left(), center.y())
        outlet = QPointF(rect.left() - ROUTE_OUTLET, center.y())
    elif side == "right":
        anchor = QPointF(rect.right(), center.y())
        outlet = QPointF(rect.right() + ROUTE_OUTLET, center.y())
    elif side == "top":
        anchor = QPointF(center.x(), rect.top())
        outlet = QPointF(center.x(), rect.top() - ROUTE_OUTLET)
    else:
        anchor = QPointF(center.x(), rect.bottom())
        outlet = QPointF(center.x(), rect.bottom() + ROUTE_OUTLET)
    return anchor, outlet


def orthogonal_grid_route(
    start: QPointF,
    end: QPointF,
    keepouts: list[QRectF],
) -> list[QPointF] | None:
    if point_inside_any_keepout(start, keepouts) or point_inside_any_keepout(end, keepouts):
        return None
    x_values = {start.x(), end.x()}
    y_values = {start.y(), end.y()}
    for rect in keepouts:
        x_values.update([rect.left(), rect.right()])
        y_values.update([rect.top(), rect.bottom()])
    xs = sorted(x_values)
    ys = sorted(y_values)
    valid_nodes = {
        (x, y)
        for x in xs
        for y in ys
        if not point_inside_any_keepout(QPointF(x, y), keepouts)
    }
    start_key = (start.x(), start.y())
    end_key = (end.x(), end.y())
    valid_nodes.update([start_key, end_key])

    distances: dict[tuple[tuple[float, float], str | None], float] = {
        (start_key, None): 0.0
    }
    paths: dict[tuple[tuple[float, float], str | None], list[tuple[float, float]]] = {
        (start_key, None): [start_key]
    }
    tie_breaker = count()
    queue: list[tuple[float, int, tuple[float, float], str | None]] = [
        (0.0, next(tie_breaker), start_key, None)
    ]
    while queue:
        cost, _, node, previous_direction = heappop(queue)
        state = (node, previous_direction)
        if cost > distances.get(state, math.inf):
            continue
        if node == end_key:
            return [QPointF(x, y) for x, y in simplify_point_keys(paths[state])]
        for neighbour, direction in grid_neighbours(node, xs, ys, valid_nodes, keepouts):
            move_cost = abs(neighbour[0] - node[0]) + abs(neighbour[1] - node[1])
            bend_cost = (
                ROUTE_BEND_PENALTY
                if previous_direction and previous_direction != direction
                else 0.0
            )
            next_cost = cost + move_cost + bend_cost
            next_state = (neighbour, direction)
            if next_cost >= distances.get(next_state, math.inf):
                continue
            distances[next_state] = next_cost
            paths[next_state] = [*paths[state], neighbour]
            heappush(queue, (next_cost, next(tie_breaker), neighbour, direction))
    return None


def grid_neighbours(
    node: tuple[float, float],
    xs: list[float],
    ys: list[float],
    valid_nodes: set[tuple[float, float]],
    keepouts: list[QRectF],
) -> list[tuple[tuple[float, float], str]]:
    x, y = node
    neighbours: list[tuple[tuple[float, float], str]] = []
    x_index = xs.index(x)
    y_index = ys.index(y)
    for next_x in [xs[index] for index in [x_index - 1, x_index + 1] if 0 <= index < len(xs)]:
        candidate = (next_x, y)
        if candidate in valid_nodes and not segment_crosses_any_keepout(node, candidate, keepouts):
            neighbours.append((candidate, "horizontal"))
    for next_y in [ys[index] for index in [y_index - 1, y_index + 1] if 0 <= index < len(ys)]:
        candidate = (x, next_y)
        if candidate in valid_nodes and not segment_crosses_any_keepout(node, candidate, keepouts):
            neighbours.append((candidate, "vertical"))
    return neighbours


def point_inside_any_keepout(point: QPointF, keepouts: list[QRectF]) -> bool:
    return any(
        rect.left() < point.x() < rect.right()
        and rect.top() < point.y() < rect.bottom()
        for rect in keepouts
    )


def segment_crosses_any_keepout(
    start: tuple[float, float],
    end: tuple[float, float],
    keepouts: list[QRectF],
) -> bool:
    return any(segment_crosses_rect(start, end, rect) for rect in keepouts)


def segment_crosses_rect(
    start: tuple[float, float],
    end: tuple[float, float],
    rect: QRectF,
) -> bool:
    x1, y1 = start
    x2, y2 = end
    if x1 == x2 and y1 == y2:
        return False
    if y1 == y2:
        left = min(x1, x2)
        right = max(x1, x2)
        return rect.top() < y1 < rect.bottom() and left < rect.right() and right > rect.left()
    if x1 == x2:
        top = min(y1, y2)
        bottom = max(y1, y2)
        return rect.left() < x1 < rect.right() and top < rect.bottom() and bottom > rect.top()
    return False


def fallback_route_points(source: QRectF, target: QRectF) -> list[QPointF]:
    start, end, orientation = connection_points(source, target)
    if orientation == "horizontal":
        mid_x = (start.x() + end.x()) / 2
        points = [
            start,
            QPointF(mid_x, start.y()),
            QPointF(mid_x, end.y()),
            end,
        ]
    else:
        mid_y = (start.y() + end.y()) / 2
        points = [
            start,
            QPointF(start.x(), mid_y),
            QPointF(end.x(), mid_y),
            end,
        ]
    return simplify_path(points)


def simplify_path(points: list[QPointF]) -> list[QPointF]:
    keys = simplify_point_keys([(point.x(), point.y()) for point in points])
    return [QPointF(x, y) for x, y in keys]


def simplify_point_keys(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    deduped: list[tuple[float, float]] = []
    for point in points:
        if not deduped or point != deduped[-1]:
            deduped.append(point)
    if len(deduped) <= 2:
        return deduped
    simplified = [deduped[0]]
    for index in range(1, len(deduped) - 1):
        previous = simplified[-1]
        current = deduped[index]
        next_point = deduped[index + 1]
        if (
            previous[0] == current[0] == next_point[0]
            or previous[1] == current[1] == next_point[1]
        ):
            continue
        simplified.append(current)
    simplified.append(deduped[-1])
    return simplified


def route_score(points: list[QPointF]) -> float:
    length = 0.0
    bends = 0
    previous_direction: str | None = None
    for start, end in zip(points, points[1:]):
        length += abs(end.x() - start.x()) + abs(end.y() - start.y())
        direction = "horizontal" if start.y() == end.y() else "vertical"
        if previous_direction and previous_direction != direction:
            bends += 1
        previous_direction = direction
    return length + bends * ROUTE_BEND_PENALTY


def label_position_for_path(points: list[QPointF]) -> QPointF:
    if len(points) == 1:
        return QPointF(points[0].x() + 6, points[0].y() - 18)
    total_length = sum(
        abs(end.x() - start.x()) + abs(end.y() - start.y())
        for start, end in zip(points, points[1:])
    )
    halfway = total_length / 2
    travelled = 0.0
    for start, end in zip(points, points[1:]):
        segment_length = abs(end.x() - start.x()) + abs(end.y() - start.y())
        if travelled + segment_length >= halfway:
            if segment_length == 0:
                return QPointF(start.x() + 6, start.y() - 18)
            ratio = (halfway - travelled) / segment_length
            return QPointF(
                start.x() + (end.x() - start.x()) * ratio + 6,
                start.y() + (end.y() - start.y()) * ratio - 18,
            )
        travelled += segment_length
    return QPointF(points[-1].x() + 6, points[-1].y() - 18)


def arrow_head(start: QPointF, end: QPointF) -> QPolygonF:
    angle = math.atan2(end.y() - start.y(), end.x() - start.x())
    size = 10.0
    left = QPointF(
        end.x() - size * math.cos(angle - math.pi / 6),
        end.y() - size * math.sin(angle - math.pi / 6),
    )
    right = QPointF(
        end.x() - size * math.cos(angle + math.pi / 6),
        end.y() - size * math.sin(angle + math.pi / 6),
    )
    return QPolygonF([end, left, right])


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)


def element_type_label(type: ElementType) -> str:
    if type == ElementType.ORGANIZATIONAL_BOUNDARY:
        return "Organizational Boundary"
    if type == ElementType.SOFTWARE_SYSTEM:
        return "System"
    if type == ElementType.DEPLOYMENT_NODE:
        return "Deployment Node"
    if type == ElementType.INFRASTRUCTURE_NODE:
        return "Infrastructure Node"
    return type.value.replace("_", " ").title()


def subtitle_text_for(element: C4Element) -> str:
    text = element.type.value.replace("_", " ").title()
    if element.type in SUBTYPE_TYPES and element.subtype:
        text += f": {element.subtype}"
    return f"[{text}]"


def tree_text_for(element: C4Element) -> str:
    return f"{element.name} {subtitle_text_for(element)}"
