# Model Structure

This document describes the JSON save-file format used by C4 Modeller and how
the stored data maps to C4 modelling concepts.

The important design point is that the save file separates the model from the
diagram. The model stores elements, hierarchy, and relationships. The diagram
stores how those elements are drawn in each view.

## Top-Level Workspace

A save file is a JSON object with this top-level structure:

```json
{
  "version": 3,
  "name": "Untitled C4 Model",
  "active_model_id": "model_abc123",
  "models": []
}
```

Fields:

- `version`: save-file format version. The current writer uses version `3`.
- `name`: workspace name shown in the application title.
- `active_model_id`: the model selected when the file was saved.
- `models`: independent C4 models stored in the same save file.

Older single-model files are migrated when opened. Their top-level `model` and
`diagram` objects are wrapped into one model.

## Model Object

Each item in `models` is independent from the others:

```json
{
  "id": "model_abc123",
  "name": "Model 1",
  "model": {
    "elements": [],
    "relationships": []
  },
  "diagram": {
    "layouts": {},
    "views": [],
    "active_view_id": "view_def456"
  }
}
```

Fields:

- `id`: stable model identifier used by `active_model_id`.
- `name`: model tab label.
- `model`: semantic C4 model data.
- `diagram`: layout and view data for this model.

Copying a model duplicates this whole object into a new model with a new model
ID and name. The copied model is independent after creation.

## Elements

Elements are stored in `model.elements`.

```json
{
  "id": "el_123abc",
  "name": "Payments",
  "type": "software_system",
  "parent_id": null,
  "description": "Handles payment flows",
  "subtype": "",
  "technology": "",
  "tags": []
}
```

Fields:

- `id`: stable element identifier.
- `name`: display name.
- `type`: element kind.
- `parent_id`: parent element ID, or `null` for a top-level element.
- `description`: text shown for supported element types.
- `subtype`: type refinement used by containers, components, deployment nodes,
  and infrastructure nodes.
- `technology`: reserved model field. It is currently not edited by the GUI for
  most element types.
- `tags`: reserved list for classification or filtering.

## Element Types

The `type` field uses these values:

- `person`: a human actor or role.
- `organizational_boundary`: a name-only grouping boundary for software
  systems.
- `software_system`: a C4 software system.
- `container`: a C4 container inside a software system or deployment node.
- `component`: a C4 component inside a container.
- `deployment_node`: a deployment environment or runtime grouping.
- `infrastructure_node`: an infrastructure dependency inside a deployment node.

## Parent Rules

The hierarchy is represented by `parent_id`. The application validates these
rules:

- Organizational boundaries are top-level only.
- People are top-level only.
- Software systems can be top-level, inside an organizational boundary, or
  inside a deployment node.
- Containers must be inside a software system or deployment node.
- Components must be inside a container.
- Deployment nodes can be top-level or inside another deployment node.
- Infrastructure nodes must be inside a deployment node and cannot have
  children.

Deleting an element deletes its normal descendants and removes relationships
that pointed to any deleted element.

## Element Metadata By Type

The GUI intentionally uses only some fields for each type:

| Type | Name | Description | Subtype | Collapsible |
| --- | --- | --- | --- | --- |
| `person` | yes | yes | no | no |
| `organizational_boundary` | yes | no | no | no |
| `software_system` | yes | yes | no | yes |
| `container` | yes | yes | yes | yes |
| `component` | yes | yes | yes | no |
| `deployment_node` | yes | no | yes | yes |
| `infrastructure_node` | yes | no | yes | no |

On load, unsupported fields are ignored for some types. For example,
organizational boundaries do not keep descriptions or subtypes.

## Relationships

Relationships are stored in `model.relationships`.

```json
{
  "id": "rel_789abc",
  "source_id": "el_source",
  "target_id": "el_target",
  "description": "calls",
  "technology": "",
  "tags": []
}
```

Fields:

- `id`: stable relationship identifier.
- `source_id`: source element ID.
- `target_id`: target element ID.
- `description`: label shown on the diagram.
- `technology`: reserved relationship field.
- `tags`: reserved list for classification or filtering.

Relationships are stored between real model elements, not between visual boxes.
When a parent is collapsed in a view, the renderer maps hidden endpoints to the
nearest visible parent. If both endpoints resolve to the same visible element,
the relationship is hidden in that view.

Organizational boundaries cannot be relationship endpoints.

## Diagram State

The `diagram` object stores drawing information for a model:

```json
{
  "layouts": {
    "el_123abc": {
      "x": 40.0,
      "y": 40.0,
      "width": 360.0,
      "height": 240.0
    }
  },
  "views": [],
  "active_view_id": "view_def456"
}
```

Fields:

- `layouts`: element ID to layout rectangle.
- `views`: view-specific state.
- `active_view_id`: selected view when the file was saved.

Layouts are shared by all views in the same model. This means moving or resizing
an element changes its position or size for every view of that model.

## Layouts

Each layout object stores the element bounds in scene coordinates:

```json
{
  "x": 40.0,
  "y": 40.0,
  "width": 220.0,
  "height": 120.0
}
```

Fields:

- `x`, `y`: top-left scene position.
- `width`, `height`: stored expanded size for the element.

Collapsed systems, containers, and deployment nodes can also have view-specific
collapsed sizes. These are not stored in `layouts`; they are stored in the view.

## Views

Each view stores the presentation choices for the same underlying model:

```json
{
  "id": "view_def456",
  "name": "Default View",
  "expanded": {
    "el_123abc": false
  },
  "collapsed_sizes": {
    "el_123abc": {
      "width": 220.0,
      "height": 90.0
    }
  }
}
```

Fields:

- `id`: stable view identifier.
- `name`: view tab label.
- `expanded`: element ID to expansion state.
- `collapsed_sizes`: element ID to view-specific collapsed bounds.

Views do not own elements or relationships. They only describe how the active
model should be presented.

## Example Skeleton

This abbreviated example shows one workspace with one model, one view, two
elements, and one relationship:

```json
{
  "version": 3,
  "name": "Example Workspace",
  "active_model_id": "model_main",
  "models": [
    {
      "id": "model_main",
      "name": "Current Architecture",
      "model": {
        "elements": [
          {
            "id": "el_customer",
            "name": "Customer",
            "type": "person",
            "parent_id": null,
            "description": "Places orders.",
            "subtype": "",
            "technology": "",
            "tags": []
          },
          {
            "id": "el_shop",
            "name": "Online Shop",
            "type": "software_system",
            "parent_id": null,
            "description": "Allows customers to buy products.",
            "subtype": "",
            "technology": "",
            "tags": []
          }
        ],
        "relationships": [
          {
            "id": "rel_uses",
            "source_id": "el_customer",
            "target_id": "el_shop",
            "description": "uses",
            "technology": "",
            "tags": []
          }
        ]
      },
      "diagram": {
        "layouts": {
          "el_customer": {
            "x": 40,
            "y": 40,
            "width": 220,
            "height": 90
          },
          "el_shop": {
            "x": 340,
            "y": 40,
            "width": 360,
            "height": 240
          }
        },
        "views": [
          {
            "id": "view_default",
            "name": "Default View",
            "expanded": {
              "el_shop": false
            },
            "collapsed_sizes": {}
          }
        ],
        "active_view_id": "view_default"
      }
    }
  ]
}
```

## ID Prefixes

The application currently generates IDs with readable prefixes:

- `model_...` for models.
- `view_...` for views.
- `el_...` for elements.
- `rel_...` for relationships.

These prefixes are convenient but should not be used as the only way to infer
object type. Use the containing JSON field and the element `type` field.
