# Contributing to p4n4

Thank you for your interest in contributing to p4n4.

## Development setup

1. Fork the relevant repository and clone your fork.
2. Create a feature branch: `git checkout -b feat/my-change`
3. Make your changes, following the guidelines below.
4. Open a pull request against `main`.

## Branching model

| Branch | Purpose |
|--------|---------|
| `main` | Always deployable; protected |
| `feat/*` | New features |
| `fix/*` | Bug fixes |
| `docs/*` | Documentation only |
| `chore/*` | Maintenance, dependency updates |

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(cli): add `p4n4 validate` command
fix(iot): correct mosquitto ACL path
docs: update getting-started guide
```

## Stack-specific guidelines

### Docker Compose stacks (p4n4-iot, p4n4-ai, p4n4-edge)

- Run `docker compose config --quiet` before pushing.
- Update `.env.example` for every new environment variable.
- Keep healthchecks on every service.

### CLI (p4n4-cli)

- Follow [ruff](https://docs.astral.sh/ruff/) style (`ruff check .`).
- Write tests for every new command and scaffold path.
- Run `pytest tests/ -v` before pushing.

### Templates (p4n4-templates)

- Read `TEMPLATE_GUIDE.md` before adding a template.
- Ensure `p4n4-template.toml` is valid before opening a PR.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
By participating you agree to abide by its terms.
