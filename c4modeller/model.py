from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
from enum import StrEnum
from typing import Any
from uuid import uuid4


class ElementType(StrEnum):
    ORGANIZATIONAL_BOUNDARY = "organizational_boundary"
    PERSON = "person"
    SOFTWARE_SYSTEM = "software_system"
    CONTAINER = "container"
    COMPONENT = "component"
    DEPLOYMENT_NODE = "deployment_node"
    INFRASTRUCTURE_NODE = "infrastructure_node"


@dataclass(slots=True)
class C4Element:
    id: str
    name: str
    type: ElementType
    parent_id: str | None = None
    description: str = ""
    subtype: str = ""
    technology: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        name: str,
        type: ElementType,
        parent_id: str | None = None,
        description: str = "",
        subtype: str = "",
        technology: str = "",
    ) -> C4Element:
        return cls(
            id=f"el_{uuid4().hex[:12]}",
            name=name,
            type=type,
            parent_id=parent_id,
            description=description,
            subtype=subtype,
            technology=technology,
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "parent_id": self.parent_id,
            "description": self.description,
            "subtype": self.subtype,
            "technology": self.technology,
            "tags": self.tags,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> C4Element:
        type = ElementType(data["type"])
        return cls(
            id=data["id"],
            name=data["name"],
            type=type,
            parent_id=data.get("parent_id"),
            description=(
                ""
                if type
                in {
                    ElementType.ORGANIZATIONAL_BOUNDARY,
                    ElementType.DEPLOYMENT_NODE,
                    ElementType.INFRASTRUCTURE_NODE,
                }
                else data.get("description", "")
            ),
            subtype=(
                ""
                if type == ElementType.ORGANIZATIONAL_BOUNDARY
                else data.get("subtype", "")
            ),
            technology=(
                ""
                if type
                in {
                    ElementType.ORGANIZATIONAL_BOUNDARY,
                    ElementType.DEPLOYMENT_NODE,
                    ElementType.INFRASTRUCTURE_NODE,
                }
                else data.get("technology", "")
            ),
            tags=list(data.get("tags", [])),
        )


@dataclass(slots=True)
class Relationship:
    id: str
    source_id: str
    target_id: str
    description: str = ""
    technology: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        source_id: str,
        target_id: str,
        description: str = "",
        technology: str = "",
    ) -> Relationship:
        return cls(
            id=f"rel_{uuid4().hex[:12]}",
            source_id=source_id,
            target_id=target_id,
            description=description,
            technology=technology,
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "description": self.description,
            "technology": self.technology,
            "tags": self.tags,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Relationship:
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            description=data.get("description", ""),
            technology=data.get("technology", ""),
            tags=list(data.get("tags", [])),
        )


@dataclass(slots=True)
class ElementLayout:
    x: float = 40.0
    y: float = 40.0
    width: float = 220.0
    height: float = 120.0

    def to_json(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> ElementLayout:
        return cls(
            x=float(data.get("x", 40.0)),
            y=float(data.get("y", 40.0)),
            width=float(data.get("width", 220.0)),
            height=float(data.get("height", 120.0)),
        )


@dataclass(slots=True)
class ViewState:
    id: str
    name: str
    expanded: dict[str, bool] = field(default_factory=dict)
    collapsed_sizes: dict[str, dict[str, float]] = field(default_factory=dict)
    visible: dict[str, bool] = field(default_factory=dict)
    tree_expanded: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        name: str,
        expanded: dict[str, bool] | None = None,
        collapsed_sizes: dict[str, dict[str, float]] | None = None,
        visible: dict[str, bool] | None = None,
        tree_expanded: dict[str, bool] | None = None,
    ) -> ViewState:
        return cls(
            id=f"view_{uuid4().hex[:12]}",
            name=name,
            expanded=dict(expanded or {}),
            collapsed_sizes={
                element_id: dict(size)
                for element_id, size in (collapsed_sizes or {}).items()
            },
            visible=dict(visible or {}),
            tree_expanded=dict(tree_expanded or {}),
        )

    def is_expanded(self, element_id: str) -> bool:
        return self.expanded.get(element_id, True)

    def set_expanded(self, element_id: str, expanded: bool) -> None:
        self.expanded[element_id] = expanded

    def remove_element(self, element_id: str) -> None:
        self.expanded.pop(element_id, None)
        self.collapsed_sizes.pop(element_id, None)
        self.visible.pop(element_id, None)
        self.tree_expanded.pop(element_id, None)

    def is_element_visible(self, element_id: str) -> bool:
        return self.visible.get(element_id, True)

    def set_element_visible(self, element_id: str, visible: bool) -> None:
        self.visible[element_id] = visible

    def is_tree_expanded(self, element_id: str) -> bool:
        return self.tree_expanded.get(element_id, True)

    def set_tree_expanded(self, element_id: str, expanded: bool) -> None:
        self.tree_expanded[element_id] = expanded

    def collapsed_size_for(self, element_id: str) -> tuple[float, float] | None:
        size = self.collapsed_sizes.get(element_id)
        if not size:
            return None
        return float(size["width"]), float(size["height"])

    def set_collapsed_size(self, element_id: str, width: float, height: float) -> None:
        self.collapsed_sizes[element_id] = {
            "width": float(width),
            "height": float(height),
        }

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "expanded": self.expanded,
            "collapsed_sizes": self.collapsed_sizes,
            "visible": self.visible,
            "tree_expanded": self.tree_expanded,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> ViewState:
        return cls(
            id=data.get("id", f"view_{uuid4().hex[:12]}"),
            name=data.get("name", "View"),
            expanded={
                element_id: bool(expanded)
                for element_id, expanded in data.get("expanded", {}).items()
            },
            collapsed_sizes={
                element_id: {
                    "width": float(size.get("width", 0)),
                    "height": float(size.get("height", 0)),
                }
                for element_id, size in data.get("collapsed_sizes", {}).items()
            },
            visible={
                element_id: bool(visible)
                for element_id, visible in data.get("visible", {}).items()
            },
            tree_expanded={
                element_id: bool(expanded)
                for element_id, expanded in data.get("tree_expanded", {}).items()
            },
        )


@dataclass(slots=True)
class DiagramState:
    layouts: dict[str, ElementLayout] = field(default_factory=dict)
    views: list[ViewState] = field(default_factory=list)
    active_view_id: str | None = None

    def __post_init__(self) -> None:
        self.ensure_view()

    def layout_for(self, element_id: str) -> ElementLayout:
        if element_id not in self.layouts:
            self.layouts[element_id] = ElementLayout()
        return self.layouts[element_id]

    def ensure_view(self) -> ViewState:
        if not self.views:
            self.views.append(ViewState.create("Default View"))
        if self.active_view_id is None or not self.view_by_id(self.active_view_id):
            self.active_view_id = self.views[0].id
        return self.current_view()

    def current_view(self) -> ViewState:
        view = self.view_by_id(self.active_view_id)
        if view is None:
            view = self.ensure_view()
        return view

    def view_by_id(self, view_id: str | None) -> ViewState | None:
        if view_id is None:
            return None
        for view in self.views:
            if view.id == view_id:
                return view
        return None

    def add_view(
        self,
        name: str,
        copy_from_active: bool = True,
    ) -> ViewState:
        current = self.current_view()
        expanded = current.expanded if copy_from_active else {}
        collapsed_sizes = current.collapsed_sizes if copy_from_active else {}
        visible = current.visible if copy_from_active else {}
        tree_expanded = current.tree_expanded if copy_from_active else {}
        view = ViewState.create(
            name,
            expanded=expanded,
            collapsed_sizes=collapsed_sizes,
            visible=visible,
            tree_expanded=tree_expanded,
        )
        self.views.append(view)
        self.active_view_id = view.id
        return view

    def delete_view(self, view_id: str) -> None:
        if len(self.views) == 1:
            raise ValueError("At least one view is required")
        self.views = [view for view in self.views if view.id != view_id]
        if self.active_view_id == view_id:
            self.active_view_id = self.views[0].id

    def to_json(self) -> dict[str, Any]:
        return {
            "layouts": {
                element_id: layout.to_json()
                for element_id, layout in self.layouts.items()
            },
            "views": [view.to_json() for view in self.views],
            "active_view_id": self.active_view_id,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> DiagramState:
        legacy_expanded: dict[str, bool] = {}
        layouts: dict[str, ElementLayout] = {}
        for element_id, layout in data.get("layouts", {}).items():
            layouts[element_id] = ElementLayout.from_json(layout)
            if "expanded" in layout:
                legacy_expanded[element_id] = bool(layout["expanded"])

        views = [
            ViewState.from_json(view)
            for view in data.get("views", [])
        ]
        if not views:
            views = [ViewState.create("Default View", expanded=legacy_expanded)]
        return cls(
            layouts=layouts,
            views=views,
            active_view_id=data.get("active_view_id"),
        )

@dataclass
class C4Model:
    id: str
    elements: dict[str, C4Element] = field(default_factory=dict)
    relationships: dict[str, Relationship] = field(default_factory=dict)
    diagram: DiagramState = field(default_factory=DiagramState)
    name: str = "Model 1"

    @classmethod
    def create(cls, name: str = "Model 1") -> C4Model:
        return cls(id=f"model_{uuid4().hex[:12]}", name=name)

    def copy(self, name: str) -> C4Model:
        copied = C4Model.from_json(self.to_json())
        copied.id = f"model_{uuid4().hex[:12]}"
        copied.name = name
        return copied

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "model": {
                "elements": [
                    element.to_json()
                    for element in sorted(self.elements.values(), key=lambda item: item.id)
                ],
                "relationships": [
                    relationship.to_json()
                    for relationship in sorted(
                        self.relationships.values(), key=lambda item: item.id
                    )
                ],
            },
            "diagram": self.diagram.to_json(),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> C4Model:
        model = data.get("model", {})
        c4_model = cls(
            id=data.get("id", f"model_{uuid4().hex[:12]}"),
            name=data.get("name", "Model"),
            diagram=DiagramState.from_json(data.get("diagram", {})),
        )
        c4_model.elements = {
            element.id: element
            for element in (
                C4Element.from_json(item)
                for item in model.get("elements", [])
            )
        }
        c4_model.relationships = {
            relationship.id: relationship
            for relationship in (
                Relationship.from_json(item)
                for item in model.get("relationships", [])
            )
        }
        for element_id in c4_model.elements:
            c4_model.diagram.layout_for(element_id)
        c4_model.diagram.ensure_view()
        return c4_model


@dataclass
class Workspace:
    name: str = "Untitled C4 Model"
    models: list[C4Model] = field(default_factory=list)
    active_model_id: str | None = None

    def __post_init__(self) -> None:
        self.ensure_model()

    def ensure_model(self) -> C4Model:
        if not self.models:
            self.models.append(C4Model.create())
        if self.active_model_id is None or not self.model_by_id(self.active_model_id):
            self.active_model_id = self.models[0].id
        return self.current_model()

    def current_model(self) -> C4Model:
        model = self.model_by_id(self.active_model_id)
        if model is None:
            model = self.ensure_model()
        return model

    def model_by_id(self, model_id: str | None) -> C4Model | None:
        if model_id is None:
            return None
        for model in self.models:
            if model.id == model_id:
                return model
        return None

    @property
    def elements(self) -> dict[str, C4Element]:
        return self.current_model().elements

    @elements.setter
    def elements(self, value: dict[str, C4Element]) -> None:
        self.current_model().elements = value

    @property
    def relationships(self) -> dict[str, Relationship]:
        return self.current_model().relationships

    @relationships.setter
    def relationships(self, value: dict[str, Relationship]) -> None:
        self.current_model().relationships = value

    @property
    def diagram(self) -> DiagramState:
        return self.current_model().diagram

    @diagram.setter
    def diagram(self, value: DiagramState) -> None:
        self.current_model().diagram = value

    def model_index(self) -> int:
        active_id = self.active_model_id
        for index, model in enumerate(self.models):
            if model.id == active_id:
                return index
        return 0

    def set_active_model(self, model_id: str) -> None:
        if self.model_by_id(model_id) is None:
            raise KeyError(f"Unknown model: {model_id}")
        self.active_model_id = model_id

    def rename_active_model(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValueError("Model name cannot be empty")
        self.current_model().name = name

    def copy_active_model(self) -> C4Model:
        current = self.current_model()
        base_name = current.name
        existing_names = {model.name for model in self.models}
        copy_name = f"{base_name} Copy"
        suffix = 2
        while copy_name in existing_names:
            copy_name = f"{base_name} Copy {suffix}"
            suffix += 1
        copied = current.copy(copy_name)
        self.models.append(copied)
        self.active_model_id = copied.id
        return copied

    def layout_for(self, element_id: str) -> ElementLayout:
        return self.diagram.layout_for(element_id)

    def is_expanded(self, element_id: str) -> bool:
        element = self.elements.get(element_id)
        if element and element.type in {
            ElementType.ORGANIZATIONAL_BOUNDARY,
            ElementType.INFRASTRUCTURE_NODE,
        }:
            return True
        return self.diagram.current_view().is_expanded(element_id)

    def set_expanded(self, element_id: str, expanded: bool) -> None:
        element = self.elements.get(element_id)
        if element and element.type in {
            ElementType.ORGANIZATIONAL_BOUNDARY,
            ElementType.INFRASTRUCTURE_NODE,
        }:
            self.diagram.current_view().set_expanded(element_id, True)
            return
        self.diagram.current_view().set_expanded(element_id, expanded)

    def toggle_expanded(self, element_id: str) -> None:
        self.set_expanded(element_id, not self.is_expanded(element_id))

    def collapsed_size_for(self, element_id: str) -> tuple[float, float] | None:
        return self.diagram.current_view().collapsed_size_for(element_id)

    def set_collapsed_size(self, element_id: str, width: float, height: float) -> None:
        self.diagram.current_view().set_collapsed_size(element_id, width, height)

    def is_element_checked(self, element_id: str) -> bool:
        return self.diagram.current_view().is_element_visible(element_id)

    def set_element_checked(self, element_id: str, visible: bool) -> None:
        self.diagram.current_view().set_element_visible(element_id, visible)

    def is_tree_expanded(self, element_id: str) -> bool:
        return self.diagram.current_view().is_tree_expanded(element_id)

    def set_tree_expanded(self, element_id: str, expanded: bool) -> None:
        self.diagram.current_view().set_tree_expanded(element_id, expanded)

    def add_view(self, name: str) -> ViewState:
        return self.diagram.add_view(name)

    def delete_active_view(self) -> None:
        self.diagram.delete_view(self.diagram.current_view().id)

    def set_active_view(self, view_id: str) -> None:
        if self.diagram.view_by_id(view_id) is None:
            raise KeyError(f"Unknown view: {view_id}")
        self.diagram.active_view_id = view_id

    def active_view(self) -> ViewState:
        return self.diagram.current_view()

    def rename_active_view(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValueError("View name cannot be empty")
        self.active_view().name = name

    def view_index(self) -> int:
        active_id = self.diagram.active_view_id
        for index, view in enumerate(self.diagram.views):
            if view.id == active_id:
                return index
        return 0

    def view_ids(self) -> list[str]:
        return [view.id for view in self.diagram.views]

    def add_element(
        self,
        name: str,
        type: ElementType,
        parent_id: str | None = None,
        x: float | None = None,
        y: float | None = None,
        description: str = "",
        subtype: str = "",
    ) -> C4Element:
        self._validate_parent(type, parent_id)
        if type == ElementType.ORGANIZATIONAL_BOUNDARY:
            description = ""
            subtype = ""
        elif type in {ElementType.DEPLOYMENT_NODE, ElementType.INFRASTRUCTURE_NODE}:
            description = ""
        element = C4Element.create(
            name=name,
            type=type,
            parent_id=parent_id,
            description=description,
            subtype=subtype,
        )
        self.elements[element.id] = element
        layout = self.layout_for(element.id)
        if x is not None:
            layout.x = x
        if y is not None:
            layout.y = y
        if type in {
            ElementType.SOFTWARE_SYSTEM,
            ElementType.CONTAINER,
            ElementType.DEPLOYMENT_NODE,
        }:
            self.set_expanded(element.id, False)
        return element

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        description: str = "",
        technology: str = "",
    ) -> Relationship:
        if source_id not in self.elements:
            raise KeyError(f"Unknown source element: {source_id}")
        if target_id not in self.elements:
            raise KeyError(f"Unknown target element: {target_id}")
        if source_id == target_id:
            raise ValueError("A relationship must connect two different elements")
        boundary_type = ElementType.ORGANIZATIONAL_BOUNDARY
        if (
            self.elements[source_id].type == boundary_type
            or self.elements[target_id].type == boundary_type
        ):
            raise ValueError("Organizational boundaries cannot have relationships")
        relationship = Relationship.create(
            source_id=source_id,
            target_id=target_id,
            description=description,
            technology=technology,
        )
        self.relationships[relationship.id] = relationship
        return relationship

    def remove_element(self, element_id: str) -> None:
        if element_id not in self.elements:
            raise KeyError(f"Unknown element: {element_id}")
        element_ids = {element_id}
        changed = True
        while changed:
            changed = False
            for element in self.elements.values():
                if element.parent_id in element_ids and element.id not in element_ids:
                    element_ids.add(element.id)
                    changed = True

        self.elements = {
            id_: element
            for id_, element in self.elements.items()
            if id_ not in element_ids
        }
        self.diagram.layouts = {
            id_: layout
            for id_, layout in self.diagram.layouts.items()
            if id_ not in element_ids
        }
        for view in self.diagram.views:
            for id_ in element_ids:
                view.remove_element(id_)
        self.relationships = {
            id_: relationship
            for id_, relationship in self.relationships.items()
            if relationship.source_id not in element_ids
            and relationship.target_id not in element_ids
        }

    def move_element(self, element_id: str, new_parent_id: str | None) -> None:
        if element_id not in self.elements:
            raise KeyError(f"Unknown element: {element_id}")
        element = self.elements[element_id]
        if new_parent_id == element_id:
            raise ValueError("An element cannot be moved inside itself")
        if new_parent_id in {descendant.id for descendant in self.descendants_of(element_id)}:
            raise ValueError("An element cannot be moved inside one of its descendants")
        self._validate_parent(element.type, new_parent_id)
        element.parent_id = new_parent_id

    def children_of(self, parent_id: str | None) -> list[C4Element]:
        return [
            element
            for element in self.elements.values()
            if element.parent_id == parent_id
        ]

    def descendants_of(self, element_id: str) -> list[C4Element]:
        descendants: list[C4Element] = []
        pending = [element_id]
        while pending:
            parent_id = pending.pop()
            children = self.children_of(parent_id)
            descendants.extend(children)
            pending.extend(child.id for child in children)
        return descendants

    def ancestors_of(self, element_id: str) -> list[C4Element]:
        ancestors: list[C4Element] = []
        current = self.elements[element_id]
        while current.parent_id:
            current = self.elements[current.parent_id]
            ancestors.append(current)
        return ancestors

    def is_visible(self, element_id: str) -> bool:
        if not self.is_available_in_view(element_id):
            return False
        for ancestor in self.ancestors_of(element_id):
            if not self.is_expanded(ancestor.id):
                return False
        return True

    def is_available_in_view(self, element_id: str) -> bool:
        if not self.is_element_checked(element_id):
            return False
        return all(
            self.is_element_checked(ancestor.id)
            for ancestor in self.ancestors_of(element_id)
        )

    def visible_elements(self) -> list[C4Element]:
        return [
            element
            for element in self.elements.values()
            if self.is_visible(element.id)
        ]

    def visible_endpoint_for(self, element_id: str) -> str:
        current = self.elements[element_id]
        endpoint_id = element_id
        while current.parent_id:
            parent = self.elements[current.parent_id]
            if not self.is_expanded(parent.id):
                endpoint_id = parent.id
            current = parent
        return endpoint_id

    def visible_relationships(self) -> list[Relationship]:
        grouped: dict[tuple[str, str], Relationship] = {}
        for relationship in self.relationships.values():
            if (
                not self.is_available_in_view(relationship.source_id)
                or not self.is_available_in_view(relationship.target_id)
            ):
                continue
            source_id = self.visible_endpoint_for(relationship.source_id)
            target_id = self.visible_endpoint_for(relationship.target_id)
            if source_id == target_id:
                continue
            key = (source_id, target_id)
            if key in grouped:
                if relationship.description:
                    existing = grouped[key]
                    descriptions = set(existing.description.split("; "))
                    if relationship.description not in descriptions:
                        existing.description = "; ".join(
                            item
                            for item in [existing.description, relationship.description]
                            if item
                        )
                continue
            grouped[key] = Relationship(
                id=relationship.id,
                source_id=source_id,
                target_id=target_id,
                description=relationship.description,
                technology=relationship.technology,
                tags=list(relationship.tags),
            )
        return list(grouped.values())

    def to_json(self) -> dict[str, Any]:
        return {
            "version": 3,
            "name": self.name,
            "active_model_id": self.active_model_id,
            "models": [model.to_json() for model in self.models],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Workspace:
        if "models" in data:
            workspace = cls(
                name=data.get("name", "Untitled C4 Model"),
                models=[
                    C4Model.from_json(model_data)
                    for model_data in data.get("models", [])
                ],
                active_model_id=data.get("active_model_id"),
            )
            workspace.ensure_model()
            return workspace

        workspace = cls(
            name=data.get("name", "Untitled C4 Model"),
            models=[
                C4Model.from_json(
                    {
                        "id": data.get("model_id", f"model_{uuid4().hex[:12]}"),
                        "name": data.get("model_name", "Model 1"),
                        "model": deepcopy(data.get("model", {})),
                        "diagram": deepcopy(data.get("diagram", {})),
                    }
                )
            ],
        )
        workspace.active_model_id = workspace.models[0].id
        return workspace

    def _validate_parent(self, type: ElementType, parent_id: str | None) -> None:
        if parent_id is None:
            if type in {
                ElementType.CONTAINER,
                ElementType.COMPONENT,
                ElementType.INFRASTRUCTURE_NODE,
            }:
                raise ValueError(f"{type.value} elements need a parent")
            return
        if parent_id not in self.elements:
            raise KeyError(f"Unknown parent element: {parent_id}")
        parent = self.elements[parent_id]
        valid_parent_types = {
            ElementType.ORGANIZATIONAL_BOUNDARY: set(),
            ElementType.SOFTWARE_SYSTEM: {
                ElementType.ORGANIZATIONAL_BOUNDARY,
                ElementType.DEPLOYMENT_NODE,
            },
            ElementType.CONTAINER: {
                ElementType.SOFTWARE_SYSTEM,
                ElementType.DEPLOYMENT_NODE,
            },
            ElementType.COMPONENT: {ElementType.CONTAINER},
            ElementType.DEPLOYMENT_NODE: {ElementType.DEPLOYMENT_NODE},
            ElementType.INFRASTRUCTURE_NODE: {ElementType.DEPLOYMENT_NODE},
            ElementType.PERSON: set(),
        }
        if parent.type not in valid_parent_types[type]:
            raise ValueError(f"{type.value} cannot be nested inside {parent.type.value}")
