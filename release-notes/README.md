# Release notes

Bodies for GitHub releases, one file per release, passed to
`gh release create --notes-file`. This folder is untracked on purpose, like
`COMMIT.md` and `PRE_RELEASE.md`. This README isn't a release body.

## v0.2.0 release set (2026-10)

Publish in this order. Each step needs the one before it ([`PRE_RELEASE.md`](../PRE_RELEASE.md) R3–R5):

| # | Release | Repo | Ships as | Notes |
|---|---|---|---|---|
| 1 | p4n4-lib **0.2.0** | `core/lib` | PyPI `p4n4-lib` | [p4n4-lib-v0.2.0.md](p4n4-lib-v0.2.0.md) |
| 2 | p4n4-api **0.1.0** | `clients/api` | `ghcr.io/raisga/p4n4-api` (installs p4n4-lib from PyPI) | [p4n4-api-v0.1.0.md](p4n4-api-v0.1.0.md) |
| 2 | p4n4-dashboard **1.1.0** | `clients/dashboard` | `ghcr.io/raisga/p4n4-dashboard` | [p4n4-dashboard-v1.1.0.md](p4n4-dashboard-v1.1.0.md) |
| 3 | p4n4 (CLI) **0.2.0** | `clients/cli` | PyPI `p4n4` | [p4n4-cli-v0.2.0.md](p4n4-cli-v0.2.0.md) |

Release the two images together. The other repos (stacks, templates, emu, hw, docs) keep
their own version lines and get no release in this set.

```bash
gh release create v0.2.0 --repo raisga/p4n4-lib       --title v0.2.0 --notes-file release-notes/p4n4-lib-v0.2.0.md
gh release create v0.1.0 --repo raisga/p4n4-api       --title v0.1.0 --notes-file release-notes/p4n4-api-v0.1.0.md
gh release create v1.1.0 --repo raisga/p4n4-dashboard --title v1.1.0 --notes-file release-notes/p4n4-dashboard-v1.1.0.md
gh release create v0.2.0 --repo raisga/p4n4-cli       --title v0.2.0 --notes-file release-notes/p4n4-cli-v0.2.0.md
```

### How they fit together

| | needs | used by |
|---|---|---|
| p4n4-lib 0.2.0 | — | CLI 0.2.0, api 0.1.0 (`p4n4-lib>=0.2.0`) |
| p4n4-api 0.1.0 | p4n4-lib 0.2.0 | dashboard 1.1.0 (sign-in, `normie` role) |
| p4n4-dashboard 1.1.0 | p4n4-api 0.1.0 | CLI 0.2.0 (`--layer dashboard` pins it) |
| p4n4 (CLI) 0.2.0 | p4n4-lib 0.2.0 | — |

## Writing a release body

Every file follows the same structure, so the set reads as one release:

1. **One sentence**: what the release is (first release) or what it changes. Don't start
   with a heading: `gh` shows `--title` above the body.
2. **Install**: one code block (`pip`/`pipx` or `docker pull`, with Python or platforms).
3. **Trust callout** (`> **Trusted networks only.** …`) for anything that runs services.
4. **`## What's in it`** for a first release, **`## Highlights`** for later ones.
5. **`## Compatibility`**: the versions it needs and pairs with, from the table above.
6. **`## Upgrading from x.y`** and/or **`## Limitations`**, when there are any.
7. **`Full list: [CHANGELOG.md](…)`** for repos that keep a changelog (lib, CLI).

Name new files `<repo>-v<version>.md`, and add a row to the set table above.
