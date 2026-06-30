import unittest

from c4modeller.model import ElementType, Workspace


class WorkspaceVisibilityTests(unittest.TestCase):
    def test_collapsed_parent_becomes_relationship_endpoint(self) -> None:
        workspace = Workspace()
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)
        api = workspace.add_element("API", ElementType.CONTAINER, parent_id=system.id)
        db = workspace.add_element("DB", ElementType.CONTAINER, parent_id=system.id)
        worker = workspace.add_element("Worker", ElementType.COMPONENT, parent_id=api.id)

        workspace.set_expanded(system.id, True)
        workspace.add_relationship(worker.id, db.id, "writes to")
        workspace.set_expanded(api.id, False)

        visible_relationships = workspace.visible_relationships()

        self.assertEqual(len(visible_relationships), 1)
        self.assertEqual(visible_relationships[0].source_id, api.id)
        self.assertEqual(visible_relationships[0].target_id, db.id)

    def test_relationship_inside_collapsed_parent_is_hidden(self) -> None:
        workspace = Workspace()
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)
        api = workspace.add_element("API", ElementType.CONTAINER, parent_id=system.id)
        controller = workspace.add_element(
            "Controller",
            ElementType.COMPONENT,
            parent_id=api.id,
        )
        service = workspace.add_element("Service", ElementType.COMPONENT, parent_id=api.id)

        workspace.set_expanded(system.id, True)
        workspace.add_relationship(controller.id, service.id, "calls")
        workspace.set_expanded(api.id, False)

        self.assertEqual(workspace.visible_relationships(), [])

    def test_unchecked_elements_are_hidden_in_the_active_view(self) -> None:
        workspace = Workspace()
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)
        api = workspace.add_element("API", ElementType.CONTAINER, parent_id=system.id)
        database = workspace.add_element("DB", ElementType.CONTAINER, parent_id=system.id)
        worker = workspace.add_element("Worker", ElementType.COMPONENT, parent_id=api.id)

        workspace.set_expanded(system.id, True)
        workspace.set_expanded(api.id, True)
        workspace.add_relationship(worker.id, database.id, "writes to")

        workspace.set_element_checked(worker.id, False)

        self.assertNotIn(worker.id, {element.id for element in workspace.visible_elements()})
        self.assertEqual(workspace.visible_relationships(), [])

    def test_unchecked_parent_hides_checked_descendants(self) -> None:
        workspace = Workspace()
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)
        api = workspace.add_element("API", ElementType.CONTAINER, parent_id=system.id)

        workspace.set_expanded(system.id, True)
        workspace.set_element_checked(system.id, False)

        self.assertTrue(workspace.is_element_checked(api.id))
        self.assertNotIn(system.id, {element.id for element in workspace.visible_elements()})
        self.assertNotIn(api.id, {element.id for element in workspace.visible_elements()})

    def test_json_round_trip_preserves_layout_and_view_state(self) -> None:
        workspace = Workspace(name="Example")
        system = workspace.add_element(
            "Payments",
            ElementType.SOFTWARE_SYSTEM,
            x=100,
            y=200,
            description="Handles payment flows",
        )
        workspace.set_expanded(system.id, False)
        workspace.set_element_checked(system.id, False)
        workspace.set_tree_expanded(system.id, False)

        restored = Workspace.from_json(workspace.to_json())

        self.assertEqual(restored.name, "Example")
        self.assertEqual(restored.elements[system.id].name, "Payments")
        self.assertEqual(
            restored.elements[system.id].description,
            "Handles payment flows",
        )
        self.assertEqual(restored.layout_for(system.id).x, 100)
        self.assertFalse(restored.is_expanded(system.id))
        self.assertFalse(restored.is_element_checked(system.id))
        self.assertFalse(restored.is_tree_expanded(system.id))

    def test_copy_active_model_creates_independent_model(self) -> None:
        workspace = Workspace(name="Example")
        original_model_id = workspace.current_model().id
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)
        workspace.layout_for(system.id).x = 100

        copied = workspace.copy_active_model()
        workspace.elements[system.id].name = "Payments Copy"
        workspace.layout_for(system.id).x = 400

        workspace.set_active_model(original_model_id)
        self.assertEqual(workspace.elements[system.id].name, "Payments")
        self.assertEqual(workspace.layout_for(system.id).x, 100)

        workspace.set_active_model(copied.id)
        self.assertEqual(workspace.elements[system.id].name, "Payments Copy")
        self.assertEqual(workspace.layout_for(system.id).x, 400)

    def test_json_round_trip_preserves_multiple_models_and_active_model(self) -> None:
        workspace = Workspace(name="Example")
        first_model_id = workspace.current_model().id
        first_system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)

        copied = workspace.copy_active_model()
        workspace.elements[first_system.id].name = "Payments Copy"

        restored = Workspace.from_json(workspace.to_json())

        self.assertEqual(len(restored.models), 2)
        self.assertEqual(restored.active_model_id, copied.id)
        self.assertEqual(restored.elements[first_system.id].name, "Payments Copy")

        restored.set_active_model(first_model_id)
        self.assertEqual(restored.elements[first_system.id].name, "Payments")

    def test_systems_and_containers_are_collapsed_by_default(self) -> None:
        workspace = Workspace()
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)
        self.assertFalse(workspace.is_expanded(system.id))

        workspace.set_expanded(system.id, True)
        api = workspace.add_element("API", ElementType.CONTAINER, parent_id=system.id)

        self.assertFalse(workspace.is_expanded(api.id))

    def test_organizational_boundaries_contain_systems_and_stay_expanded(self) -> None:
        workspace = Workspace()
        boundary = workspace.add_element(
            "Acme Corp",
            ElementType.ORGANIZATIONAL_BOUNDARY,
            description="Ignored",
            subtype="Ignored",
        )
        system = workspace.add_element(
            "Payments",
            ElementType.SOFTWARE_SYSTEM,
            parent_id=boundary.id,
        )

        self.assertEqual(workspace.elements[system.id].parent_id, boundary.id)
        self.assertTrue(workspace.is_expanded(boundary.id))
        self.assertEqual(workspace.elements[boundary.id].description, "")
        self.assertEqual(workspace.elements[boundary.id].subtype, "")

        workspace.set_expanded(boundary.id, False)
        self.assertTrue(workspace.is_expanded(boundary.id))

    def test_organizational_boundaries_reject_invalid_parenting(self) -> None:
        workspace = Workspace()
        boundary = workspace.add_element("Acme Corp", ElementType.ORGANIZATIONAL_BOUNDARY)
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)

        with self.assertRaises(ValueError):
            workspace.add_element(
                "Nested Boundary",
                ElementType.ORGANIZATIONAL_BOUNDARY,
                parent_id=boundary.id,
            )

        with self.assertRaises(ValueError):
            workspace.add_element(
                "Nested Person",
                ElementType.PERSON,
                parent_id=boundary.id,
            )

        with self.assertRaises(ValueError):
            workspace.add_element(
                "Nested Container",
                ElementType.CONTAINER,
                parent_id=boundary.id,
            )

        with self.assertRaises(ValueError):
            workspace.move_element(boundary.id, system.id)

    def test_can_move_system_to_organizational_boundary(self) -> None:
        workspace = Workspace()
        boundary = workspace.add_element("Acme Corp", ElementType.ORGANIZATIONAL_BOUNDARY)
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)

        workspace.move_element(system.id, boundary.id)

        self.assertEqual(workspace.elements[system.id].parent_id, boundary.id)

    def test_organizational_boundaries_cannot_have_relationships(self) -> None:
        workspace = Workspace()
        boundary = workspace.add_element("Acme Corp", ElementType.ORGANIZATIONAL_BOUNDARY)
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)

        with self.assertRaises(ValueError):
            workspace.add_relationship(boundary.id, system.id, "owns")

        with self.assertRaises(ValueError):
            workspace.add_relationship(system.id, boundary.id, "reports to")

    def test_people_can_store_descriptions(self) -> None:
        workspace = Workspace()
        person = workspace.add_element(
            "Customer",
            ElementType.PERSON,
            description="Places orders through the shop.",
        )

        self.assertEqual(
            workspace.elements[person.id].description,
            "Places orders through the shop.",
        )

    def test_containers_and_components_can_store_subtypes(self) -> None:
        workspace = Workspace()
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)
        container = workspace.add_element(
            "API",
            ElementType.CONTAINER,
            parent_id=system.id,
            subtype="REST API",
        )
        component = workspace.add_element(
            "Orders",
            ElementType.COMPONENT,
            parent_id=container.id,
            subtype="Service",
        )

        restored = Workspace.from_json(workspace.to_json())

        self.assertEqual(restored.elements[container.id].subtype, "REST API")
        self.assertEqual(restored.elements[component.id].subtype, "Service")

    def test_deployment_nodes_store_subtypes_and_can_contain_supported_nodes(self) -> None:
        workspace = Workspace()
        deployment = workspace.add_element(
            "Production",
            ElementType.DEPLOYMENT_NODE,
            subtype="Kubernetes Cluster",
            description="Ignored",
        )
        nested_deployment = workspace.add_element(
            "Namespace",
            ElementType.DEPLOYMENT_NODE,
            parent_id=deployment.id,
            subtype="Kubernetes Namespace",
        )
        system = workspace.add_element(
            "Payments",
            ElementType.SOFTWARE_SYSTEM,
            parent_id=deployment.id,
        )
        container = workspace.add_element(
            "API",
            ElementType.CONTAINER,
            parent_id=deployment.id,
            subtype="Container Image",
        )
        infrastructure = workspace.add_element(
            "Postgres",
            ElementType.INFRASTRUCTURE_NODE,
            parent_id=nested_deployment.id,
            subtype="Managed Database",
            description="Ignored",
        )

        self.assertFalse(workspace.is_expanded(deployment.id))
        self.assertEqual(workspace.elements[deployment.id].description, "")
        self.assertEqual(workspace.elements[deployment.id].subtype, "Kubernetes Cluster")
        self.assertEqual(workspace.elements[nested_deployment.id].parent_id, deployment.id)
        self.assertEqual(workspace.elements[system.id].parent_id, deployment.id)
        self.assertEqual(workspace.elements[container.id].parent_id, deployment.id)
        self.assertEqual(
            workspace.elements[infrastructure.id].parent_id,
            nested_deployment.id,
        )
        self.assertEqual(workspace.elements[infrastructure.id].description, "")
        self.assertEqual(workspace.elements[infrastructure.id].subtype, "Managed Database")

        restored = Workspace.from_json(workspace.to_json())
        self.assertEqual(
            restored.elements[deployment.id].subtype,
            "Kubernetes Cluster",
        )
        self.assertEqual(
            restored.elements[infrastructure.id].subtype,
            "Managed Database",
        )

    def test_infrastructure_nodes_are_leaf_nodes_and_stay_expanded(self) -> None:
        workspace = Workspace()
        deployment = workspace.add_element("Production", ElementType.DEPLOYMENT_NODE)
        infrastructure = workspace.add_element(
            "Postgres",
            ElementType.INFRASTRUCTURE_NODE,
            parent_id=deployment.id,
            subtype="Managed Database",
        )

        workspace.set_expanded(infrastructure.id, False)
        self.assertTrue(workspace.is_expanded(infrastructure.id))

        with self.assertRaises(ValueError):
            workspace.add_element("VM", ElementType.INFRASTRUCTURE_NODE)

        with self.assertRaises(ValueError):
            workspace.add_element(
                "Nested Deployment",
                ElementType.DEPLOYMENT_NODE,
                parent_id=infrastructure.id,
            )

        with self.assertRaises(ValueError):
            workspace.add_element(
                "Nested Container",
                ElementType.CONTAINER,
                parent_id=infrastructure.id,
            )

    def test_legacy_json_expanded_layout_migrates_to_default_view(self) -> None:
        restored = Workspace.from_json(
            {
                "version": 1,
                "name": "Legacy",
                "model": {
                    "elements": [
                        {
                            "id": "el_system",
                            "name": "Payments",
                            "type": "software_system",
                            "parent_id": None,
                        }
                    ],
                    "relationships": [],
                },
                "diagram": {
                    "layouts": {
                        "el_system": {
                            "x": 10,
                            "y": 20,
                            "width": 300,
                            "height": 200,
                            "expanded": False,
                        }
                    }
                },
            }
        )

        self.assertEqual(restored.layout_for("el_system").x, 10)
        self.assertEqual(len(restored.diagram.views), 1)
        self.assertFalse(restored.is_expanded("el_system"))

    def test_views_share_objects_and_layout_but_have_separate_expansion(self) -> None:
        workspace = Workspace()
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)
        api = workspace.add_element("API", ElementType.CONTAINER, parent_id=system.id)
        worker = workspace.add_element("Worker", ElementType.COMPONENT, parent_id=api.id)
        default_view_id = workspace.active_view().id

        workspace.set_expanded(api.id, False)
        workspace.add_view("Expanded")
        workspace.set_expanded(api.id, True)
        workspace.layout_for(api.id).x = 123

        workspace.set_active_view(default_view_id)
        self.assertFalse(workspace.is_expanded(api.id))
        self.assertEqual(workspace.layout_for(api.id).x, 123)
        self.assertEqual(set(workspace.elements), {system.id, api.id, worker.id})

        workspace.set_active_view(workspace.diagram.views[1].id)
        self.assertTrue(workspace.is_expanded(api.id))

    def test_views_have_separate_element_visibility_and_tree_state(self) -> None:
        workspace = Workspace()
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)
        first_view_id = workspace.active_view().id

        workspace.set_element_checked(system.id, False)
        workspace.set_tree_expanded(system.id, False)
        workspace.add_view("Other")
        workspace.set_element_checked(system.id, True)
        workspace.set_tree_expanded(system.id, True)

        workspace.set_active_view(first_view_id)
        self.assertFalse(workspace.is_element_checked(system.id))
        self.assertFalse(workspace.is_tree_expanded(system.id))

        workspace.set_active_view(workspace.diagram.views[1].id)
        self.assertTrue(workspace.is_element_checked(system.id))
        self.assertTrue(workspace.is_tree_expanded(system.id))

    def test_collapsed_sizes_are_view_specific(self) -> None:
        workspace = Workspace()
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)
        first_view_id = workspace.active_view().id
        workspace.set_collapsed_size(system.id, 240, 100)

        workspace.add_view("Other")
        workspace.set_collapsed_size(system.id, 320, 140)

        workspace.set_active_view(first_view_id)
        self.assertEqual(workspace.collapsed_size_for(system.id), (240.0, 100.0))

        restored = Workspace.from_json(workspace.to_json())
        self.assertEqual(restored.collapsed_size_for(system.id), (240.0, 100.0))

    def test_can_move_container_to_another_system(self) -> None:
        workspace = Workspace()
        source_system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)
        target_system = workspace.add_element("CRM", ElementType.SOFTWARE_SYSTEM)
        api = workspace.add_element("API", ElementType.CONTAINER, parent_id=source_system.id)

        workspace.move_element(api.id, target_system.id)

        self.assertEqual(workspace.elements[api.id].parent_id, target_system.id)

    def test_can_move_component_to_another_container(self) -> None:
        workspace = Workspace()
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)
        api = workspace.add_element("API", ElementType.CONTAINER, parent_id=system.id)
        worker_container = workspace.add_element(
            "Worker",
            ElementType.CONTAINER,
            parent_id=system.id,
        )
        component = workspace.add_element(
            "Orders",
            ElementType.COMPONENT,
            parent_id=api.id,
        )

        workspace.move_element(component.id, worker_container.id)

        self.assertEqual(workspace.elements[component.id].parent_id, worker_container.id)

    def test_rejects_inconsistent_moves(self) -> None:
        workspace = Workspace()
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)
        api = workspace.add_element("API", ElementType.CONTAINER, parent_id=system.id)
        component = workspace.add_element(
            "Orders",
            ElementType.COMPONENT,
            parent_id=api.id,
        )

        with self.assertRaises(ValueError):
            workspace.move_element(api.id, component.id)

        with self.assertRaises(ValueError):
            workspace.move_element(component.id, system.id)

    def test_remove_element_removes_descendants_and_relationships(self) -> None:
        workspace = Workspace()
        system = workspace.add_element("Payments", ElementType.SOFTWARE_SYSTEM)
        api = workspace.add_element("API", ElementType.CONTAINER, parent_id=system.id)
        worker = workspace.add_element("Worker", ElementType.COMPONENT, parent_id=api.id)
        external = workspace.add_element("CRM", ElementType.SOFTWARE_SYSTEM)
        workspace.add_relationship(worker.id, external.id, "updates")
        workspace.add_view("Second")
        workspace.set_expanded(api.id, False)

        workspace.remove_element(api.id)

        self.assertNotIn(api.id, workspace.elements)
        self.assertNotIn(worker.id, workspace.elements)
        self.assertEqual(workspace.relationships, {})
        for view in workspace.diagram.views:
            self.assertNotIn(api.id, view.expanded)


if __name__ == "__main__":
    unittest.main()
