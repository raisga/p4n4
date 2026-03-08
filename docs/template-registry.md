# Template Registry

The community template registry lives at [raisga/p4n4-templates](https://github.com/raisga/p4n4-templates).

## Using templates

```bash
# Search available templates
p4n4 template search

# Filter by keyword
p4n4 template search manufacturing

# Install a template
p4n4 template install factory-baseline

# List installed templates
p4n4 template list
```

## Built-in templates

| Name | Stacks | Description |
|------|--------|-------------|
| `factory-baseline` | iot + ai + edge | Full stack for discrete manufacturing |
| `iot-minimal` | iot | Minimal IoT-only starter |

## Contributing a template

1. Create a Git repository containing your template files and a `p4n4-template.toml`.
2. Read the [TEMPLATE_GUIDE.md](https://github.com/raisga/p4n4-templates/blob/main/TEMPLATE_GUIDE.md).
3. Fork `raisga/p4n4-templates` and add your template to `index.json`.
4. Open a pull request — CI validates the index automatically.

## `p4n4-template.toml` quick reference

```toml
[template]
name = "my-template"
version = "0.1.0"
description = "One sentence description"
author = "Your Name"
tags = ["tag1", "tag2"]

[requires]
cli = ">=0.1.0"
stacks = ["iot"]
```
