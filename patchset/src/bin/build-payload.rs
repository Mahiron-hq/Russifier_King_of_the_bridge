//! Packs the difference between a clean copy of the game and a copy with the mod applied into the payload the
//! installer embeds.

use std::fs::{self, File};
use std::io::BufWriter;
use std::path::PathBuf;

use anyhow::{Context, Result};
use clap::Parser;
use patchset::{BuildSpec, DeriveRule, GamePath, LanguageSettings, build};

#[derive(Parser)]
struct Args {
    /// Game folder without the mod.
    #[arg(long)]
    original: PathBuf,
    /// Copy of the same folder with the mod applied.
    #[arg(long)]
    patched: PathBuf,
    /// First-run settings with Russian selected, written by tools/build_mod.py.
    #[arg(long)]
    settings: PathBuf,
    #[arg(long)]
    out: PathBuf,
}

fn main() -> Result<()> {
    let args = Args::parse();
    let first_run = serde_json::from_slice(
        &fs::read(&args.settings).with_context(|| format!("reading {}", args.settings.display()))?,
    )
    .context("parsing the first-run settings")?;
    let spec = BuildSpec {
        version: patchset::display_version(env!("CARGO_PKG_VERSION")),
        owned_dirs: vec![GamePath::try_from("King of the Bridge_Data/StreamingAssets/ru")?],
        // The Russian bundles are clones of the English ones; the locale list has no language in its name.
        derive_rules: vec![
            DeriveRule { from: "-russian(ru)_".into(), to: "-english(en)_".into() },
            DeriveRule { from: "-russian(ru)_".into(), to: "_".into() },
        ],
        settings: LanguageSettings { russian: 2.0, english: 0.0, first_run },
    };
    let payload = build(&args.original, &args.patched, &spec)?;
    let out = File::create(&args.out).with_context(|| format!("creating {}", args.out.display()))?;
    payload.write_tar(BufWriter::new(out))?;
    for file in &payload.manifest.files {
        println!("{:<8} {}", kind(&file.content), file.path);
    }
    Ok(())
}

fn kind(content: &patchset::Content) -> &'static str {
    match content {
        patchset::Content::Replace { .. } => "replace",
        patchset::Content::Derive { .. } => "derive",
        patchset::Content::Add { .. } => "add",
    }
}
