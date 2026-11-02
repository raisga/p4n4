//! `cargo xtask golden`: fixtures captured once from v0.4.2 wherever behaviour is meant to stay
//! the same, which the Rust crates are then compared against (RUST_REWRITE_PLAN.md §10).
//!
//! Each kind lives in `fixtures/golden/v0.4.2/<kind>/`, next to a `MANIFEST.toml` that records
//! the commits it was captured from.
//!
//! `emu-limits` and `sim-series` run v0.4.2's own Python through a helper in `xtask/golden/`.
//! `P4N4_GOLDEN_PYTHON` names the interpreter: Python 3.11 or later, with `lib` and
//! `tools/emu` installed from this checkout (`pip install -e lib -e tools/emu`).

use std::collections::BTreeMap;
use std::fmt;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command as Process, Stdio};

use anyhow::{Context, Result, bail};
use clap::{Args, Subcommand, ValueEnum};
use serde::{Deserialize, Serialize};

/// The release the fixtures come from.
const BASELINE: &str = "v0.4.2";

/// The submodules holding the v0.4.2 code. A capture runs only when each is at the commit the
/// superproject pins, and its manifest records those commits.
const BASELINE_SUBMODULES: &[&str] = &[
    "lib",
    "cli",
    "api",
    "tools/emu",
    "tools/templates",
    "stacks/iot",
    "stacks/ai",
    "stacks/extras",
];

const MANIFEST: &str = "MANIFEST.toml";

/// The environment variable naming the Python that runs the capture helpers.
const PYTHON: &str = "P4N4_GOLDEN_PYTHON";

#[derive(Debug, Subcommand)]
pub enum Command {
    /// List the fixture kinds: what each waits for, and what is captured
    List,
    /// Capture fixtures from the v0.4.2 code in the submodules
    Capture {
        #[command(flatten)]
        selection: Selection,
        /// Replace fixtures that are already captured
        #[arg(long)]
        force: bool,
    },
    /// Check that fixtures are captured. The comparison with Rust outputs comes with each crate
    Verify {
        #[command(flatten)]
        selection: Selection,
    },
}

#[derive(Debug, Args)]
pub struct Selection {
    /// Fixture kinds
    #[arg(value_enum, required_unless_present = "all")]
    kinds: Vec<Kind>,
    /// Every kind that is not waiting for a spike or hardware
    #[arg(long, conflicts_with = "kinds")]
    all: bool,
}

impl Selection {
    fn kinds(&self) -> Vec<Kind> {
        if self.all {
            Kind::value_variants()
                .iter()
                .copied()
                .filter(|kind| kind.blocked_by().is_none())
                .collect()
        } else {
            self.kinds.clone()
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, ValueEnum)]
pub enum Kind {
    /// Emulator limits for each profile and stack, compared by meaning rather than text
    EmuLimits,
    /// Simulator series for each scenario, compared statistically
    SimSeries,
    /// A backup taken with `make backup`, which `p4n4 restore` must accept
    Backup,
    /// Runner results for the example models
    Runner,
    /// System 1 decisions on the parity corpus
    #[value(name = "system1")]
    System1,
    /// obd2 MQTT output for the recorded ELM327 transcripts
    #[value(name = "obd2")]
    Obd2,
}

impl Kind {
    /// What the capture waits for, if it cannot run yet.
    fn blocked_by(self) -> Option<&'static str> {
        match self {
            Self::EmuLimits | Self::SimSeries | Self::Backup => None,
            Self::Runner => Some("the Pi 5, where P5 compares runner results"),
            Self::System1 => Some("spike S4, which builds the parity corpus"),
            Self::Obd2 => Some("spike S5, which records the ELM327 transcripts"),
        }
    }

    /// The phase that brings the Rust side of the comparison.
    fn compared_in(self) -> &'static str {
        match self {
            Self::Backup => "P2 (p4n4 restore)",
            Self::EmuLimits => "P4 (p4n4-emu)",
            Self::SimSeries => "P4 (p4n4-sim)",
            Self::Runner => "P5 (p4n4-runner)",
            Self::Obd2 => "P5 (p4n4-obd2)",
            Self::System1 => "P6 (p4n4-system1)",
        }
    }

    /// Writes the fixtures into `out`, and returns the inputs for the manifest.
    fn write_fixtures(self, root: &Path, out: &Path) -> Result<toml::Table> {
        match self {
            Self::EmuLimits => capture_emu_limits(root, out),
            Self::SimSeries => capture_sim_series(root, out),
            Self::Backup => capture_backup(root, out),
            Self::Runner | Self::System1 | Self::Obd2 => bail!("`{self}` cannot be captured yet"),
        }
    }
}

impl fmt::Display for Kind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let value = self.to_possible_value().ok_or(fmt::Error)?;
        f.pad(value.get_name())
    }
}

/// Where one kind's fixtures came from, written next to them.
#[derive(Debug, Serialize, Deserialize)]
struct Manifest {
    kind: String,
    baseline: String,
    /// The superproject commit the capture ran on
    superproject: String,
    /// The commit of each baseline submodule
    submodules: BTreeMap<String, String>,
    /// Kind-specific inputs, such as profiles, scenarios, seeds and sample counts
    #[serde(default)]
    inputs: toml::Table,
}

pub fn run(root: &Path, command: Command) -> Result<()> {
    match command {
        Command::List => list(root),
        Command::Capture { selection, force } => {
            if selection.all {
                for kind in Kind::value_variants() {
                    if let Some(blocker) = kind.blocked_by() {
                        println!("{kind}: skipped, needs {blocker}");
                    }
                }
            }
            for kind in selection.kinds() {
                capture(root, kind, force)?;
            }
            Ok(())
        }
        Command::Verify { selection } => verify(root, &selection.kinds()),
    }
}

fn list(root: &Path) -> Result<()> {
    for &kind in Kind::value_variants() {
        let state = match (read_manifest(root, kind)?, kind.blocked_by()) {
            (Some(manifest), _) => format!("captured at {}", short(&manifest.superproject)),
            (None, Some(blocker)) => format!("needs {blocker}"),
            (None, None) => "not captured".to_owned(),
        };
        println!("{kind:<10}  {state}; compared in {}", kind.compared_in());
    }
    Ok(())
}

fn capture(root: &Path, kind: Kind, force: bool) -> Result<()> {
    if let Some(blocker) = kind.blocked_by() {
        bail!("`{kind}` cannot be captured yet: it needs {blocker}");
    }
    let dir = fixture_dir(root, kind);
    if dir.join(MANIFEST).exists() && !force {
        bail!(
            "`{kind}` is already captured in {}; pass --force to replace it",
            dir.display()
        );
    }
    let submodules = baseline_submodules(root)?;
    let superproject = git(root, &["rev-parse", "HEAD"])?.trim().to_owned();

    // Capture next to the old fixtures and swap at the end, so a failed capture keeps them.
    let staging = dir.with_file_name(format!("{kind}.partial"));
    if staging.exists() {
        fs::remove_dir_all(&staging).with_context(|| format!("removing {}", staging.display()))?;
    }
    fs::create_dir_all(&staging).with_context(|| format!("creating {}", staging.display()))?;
    let inputs = kind
        .write_fixtures(root, &staging)
        .with_context(|| format!("capturing `{kind}`"))?;
    let manifest = Manifest {
        kind: kind.to_string(),
        baseline: BASELINE.to_owned(),
        superproject,
        submodules,
        inputs,
    };
    let text = format!(
        "# Written by `cargo xtask golden capture {kind}`. Do not edit.\n{}",
        toml::to_string_pretty(&manifest)?
    );
    fs::write(staging.join(MANIFEST), text)?;
    if dir.exists() {
        fs::remove_dir_all(&dir).with_context(|| format!("removing {}", dir.display()))?;
    }
    fs::rename(&staging, &dir)
        .with_context(|| format!("moving {} to {}", staging.display(), dir.display()))?;
    println!("{kind}: captured in {}", dir.display());
    Ok(())
}

fn verify(root: &Path, kinds: &[Kind]) -> Result<()> {
    let mut missing = Vec::new();
    for &kind in kinds {
        match read_manifest(root, kind)? {
            Some(manifest) => println!(
                "{kind}: captured at {}; the comparison with Rust arrives in {}",
                short(&manifest.superproject),
                kind.compared_in()
            ),
            None => missing.push(kind.to_string()),
        }
    }
    if !missing.is_empty() {
        bail!("not captured: {}", missing.join(", "));
    }
    Ok(())
}

fn fixture_dir(root: &Path, kind: Kind) -> PathBuf {
    root.join("fixtures")
        .join("golden")
        .join(BASELINE)
        .join(kind.to_string())
}

fn read_manifest(root: &Path, kind: Kind) -> Result<Option<Manifest>> {
    let path = fixture_dir(root, kind).join(MANIFEST);
    if !path.exists() {
        return Ok(None);
    }
    let text = fs::read_to_string(&path).with_context(|| format!("reading {}", path.display()))?;
    let manifest = toml::from_str(&text).with_context(|| format!("parsing {}", path.display()))?;
    Ok(Some(manifest))
}

fn short(commit: &str) -> &str {
    commit.get(..7).unwrap_or(commit)
}

fn baseline_submodules(root: &Path) -> Result<BTreeMap<String, String>> {
    let mut args = vec!["submodule", "status", "--"];
    args.extend_from_slice(BASELINE_SUBMODULES);
    parse_submodule_status(&git(root, &args)?)
}

/// Parses `git submodule status`, refusing any submodule that is not at its pinned commit.
fn parse_submodule_status(output: &str) -> Result<BTreeMap<String, String>> {
    let mut commits = BTreeMap::new();
    for line in output.lines().filter(|line| !line.trim().is_empty()) {
        let mut chars = line.chars();
        let state = chars.next();
        let (commit, rest) = chars
            .as_str()
            .split_once(' ')
            .with_context(|| format!("unexpected `git submodule status` line: {line}"))?;
        let path = rest.split_once(" (").map_or(rest, |(path, _)| path);
        match state {
            Some(' ') => {}
            Some('+') => bail!(
                "{path} is checked out at {commit}, not at the commit the superproject pins; \
                 run `git submodule update {path}`"
            ),
            Some('-') => {
                bail!("{path} is not checked out; run `git submodule update --init {path}`")
            }
            _ => bail!("{path} is in an unexpected state: {line}"),
        }
        commits.insert(path.to_owned(), commit.to_owned());
    }
    Ok(commits)
}

fn git(root: &Path, args: &[&str]) -> Result<String> {
    let output = Process::new("git")
        .arg("-C")
        .arg(root)
        .args(args)
        .output()
        .context("running git")?;
    if !output.status.success() {
        bail!(
            "`git {}` failed: {}",
            args.join(" "),
            String::from_utf8_lossy(&output.stderr).trim()
        );
    }
    String::from_utf8(output.stdout).context("git printed invalid UTF-8")
}

// The captures. emu-limits and sim-series run v0.4.2's code through a helper; backup is still
// to write, in the P0 golden task.

fn capture_emu_limits(root: &Path, out: &Path) -> Result<toml::Table> {
    run_helper(root, "emu_limits.py", out)
}

fn capture_sim_series(root: &Path, out: &Path) -> Result<toml::Table> {
    run_helper(root, "sim_series.py", out)
}

fn capture_backup(_root: &Path, _out: &Path) -> Result<toml::Table> {
    bail!("not written yet: seed stacks/iot and take `make backup`")
}

/// Runs `xtask/golden/<helper>`, which writes the fixtures into `out` and prints the manifest's
/// inputs as one JSON object. Its progress goes to stderr.
fn run_helper(root: &Path, helper: &str, out: &Path) -> Result<toml::Table> {
    let python = std::env::var_os(PYTHON).with_context(|| {
        format!(
            "set {PYTHON} to a Python 3.11+ with v0.4.2's packages installed from this \
             checkout (`pip install -e lib -e tools/emu`)"
        )
    })?;
    let script = root.join("xtask").join("golden").join(helper);
    let output = Process::new(&python)
        .arg(&script)
        .arg("--root")
        .arg(root)
        .arg("--out")
        .arg(out)
        // Sets iterate in a fixed order. Without it, the helper runs itself again with it.
        .env("PYTHONHASHSEED", "0")
        .stderr(Stdio::inherit())
        .output()
        .with_context(|| format!("running {} with {}", script.display(), python.display()))?;
    if !output.status.success() {
        bail!("{helper} failed: {}", output.status);
    }
    serde_json::from_slice::<toml::Table>(&output.stdout)
        .with_context(|| format!("reading the manifest inputs {helper} printed"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn submodule_status_records_each_pinned_commit() -> Result<()> {
        let output = " 51dc352 lib (v0.4.2)\n 9ba42c0 tools/emu (v0.1.0-8-g9ba42c0)\n d684d4d stacks/extras\n";
        let expected: BTreeMap<String, String> = [
            ("lib", "51dc352"),
            ("stacks/extras", "d684d4d"),
            ("tools/emu", "9ba42c0"),
        ]
        .into_iter()
        .map(|(path, commit)| (path.to_owned(), commit.to_owned()))
        .collect();
        assert_eq!(parse_submodule_status(output)?, expected);
        Ok(())
    }

    #[test]
    fn submodule_status_refuses_a_moved_submodule() {
        let err =
            parse_submodule_status(" 51dc352 lib (v0.4.2)\n+cc46b0e cli (v0.4.2-1-gcc46b0e)\n")
                .expect_err("a moved submodule is refused");
        assert!(
            err.to_string().contains("cli is checked out at cc46b0e"),
            "{err}"
        );
    }

    #[test]
    fn submodule_status_refuses_a_missing_submodule() {
        let err =
            parse_submodule_status("-60531e0 api\n").expect_err("a missing submodule is refused");
        assert!(err.to_string().contains("api is not checked out"), "{err}");
    }
}
