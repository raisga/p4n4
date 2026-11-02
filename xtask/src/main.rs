//! Workspace automation, run as `cargo xtask <command>` (RUST_REWRITE_PLAN.md §8).
//!
//! P0 has only `golden`. P1 adds `layering`, `assets` and `convert`.

mod golden;

use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};

#[derive(Debug, Parser)]
#[command(name = "cargo xtask", about = "p4n4 workspace automation")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Golden fixtures captured from v0.4.2 (RUST_REWRITE_PLAN.md §10)
    Golden {
        #[command(subcommand)]
        command: golden::Command,
    },
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    let root = workspace_root()?;
    match cli.command {
        Command::Golden { command } => golden::run(&root, command),
    }
}

/// The workspace root, one directory above this crate.
fn workspace_root() -> Result<PathBuf> {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .map(Path::to_path_buf)
        .context("xtask is not inside the workspace")
}
