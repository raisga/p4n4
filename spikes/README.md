# Spikes

Throwaway code for the P0 spikes in the [Rust rewrite plan](../RUST_REWRITE_PLAN.md#91-spikes-p0). Each spike answers its questions with a decision, written up in the docs submodule's [`decisions/spikes/`](../docs/decisions/spikes/README.md).

- **One directory per spike**, named like its note: `s1-compose/`, `s2-proxy/`, `s7-yaml/`, `s8-cross/`, `s9-desktop/`, and so on.
- **Outside the workspace.** A spike with Rust code is its own Cargo project: the root `Cargo.toml` excludes `spikes/`, and each spike's `Cargo.toml` has an empty `[workspace]` table, so it builds on its own. Nothing outside `spikes/` depends on it.
- **Answers, not products.** The code only has to answer the spike's questions; the note holds the results. Code worth keeping moves into a crate, with tests, in P1.
- **Deleted in P1.**
