# C4 Modeller

C4 Modeller is a local desktop diagramming tool for creating C4 architecture
models. It is built with Python and PySide6, stores its data as JSON, and runs
entirely on the local machine.

The application is designed around a real underlying model rather than only a
drawing. Elements know their type and parent, relationships are stored between
model elements, and diagram views decide how that model is presented. This is
what allows a container or system to be collapsed while relationships are still
routed to the nearest visible parent.

## C4 Modelling Overview

The C4 model describes software architecture at different levels of detail:

- Context: people and external/internal software systems.
- Container: the applications, databases, services, and other deployable units
  inside a software system.
- Component: the significant building blocks inside a container.
- Deployment: runtime environments, infrastructure, and where systems or
  containers are deployed.

This application implements these ideas as editable elements on a canvas. It
also includes supporting boundary types that help organize diagrams without
turning everything into a relationship endpoint.

## Supported Elements

- Person: a human actor or role. People have a name and description.
- Organizational Boundary: a name-only boundary for grouping software systems.
  It cannot be collapsed and cannot have relationships.
- Software System: a software system. Systems have a name and description, can
  contain containers, and can be collapsed.
- Container: an application, service, database, or similar deployable unit.
  Containers have a name, subtype, and description, can contain components, and
  can be collapsed.
- Component: a building block inside a container. Components have a name,
  subtype, and description.
- Deployment Node: an environment, machine, cluster, namespace, or other
  deployment grouping. Deployment nodes have a name and subtype, can contain
  systems, containers, other deployment nodes, and infrastructure nodes, and can
  be collapsed.
- Infrastructure Node: an infrastructure dependency inside a deployment node.
  Infrastructure nodes have a name and subtype, cannot contain children, and
  cannot be collapsed.

Relationships can be created between most elements. Organizational boundaries
cannot be relationship endpoints.

## Models And Views

A save file can contain multiple independent models. The model tabs at the top
of the window select which model is active. Each model has its own elements,
relationships, layouts, and views.

Each model can also have multiple views. Views share the same elements and
relationships within that model, but each view has its own expand/collapse
state, model-tree visibility checkboxes, tree branch expansion state, and
collapsed sizes. This allows the same model to be shown at different levels of
detail.

The Copy Model button duplicates the active model into a new independent model.
Changes made to the copy do not affect the original.

Model and view names can be edited with the toolbar buttons or by double-clicking
their tabs.

## Diagram Behaviour

- The left model tree shows the nested model structure for the active model.
- Each model tree item has a checkbox that controls whether that element is
  visible in the active view.
- Tree branches can be expanded or collapsed independently in each view.
- Elements can be moved and resized with the mouse.
- Nested elements are constrained to stay inside their parent.
- Parent boundaries grow as needed to keep their children contained.
- Systems, containers, and deployment nodes can be expanded or collapsed.
- When a parent is collapsed, hidden child relationships are routed to the
  visible parent.
- The canvas background is shown as a grid while editing.
- Exported PDFs omit the grid and render the active view as a single page.

## Storage

Workspaces are saved as JSON. The file contains:

- workspace metadata,
- one or more independent models,
- each model's elements and relationships,
- each model's diagram layouts and views.

See [model_structure.md](model_structure.md) for the save-file structure and how
it maps to C4 concepts.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run

```bash
python -m c4modeller
```

## Test

```bash
python -m unittest discover -s tests
```

## External Dependencies

- PySide6
