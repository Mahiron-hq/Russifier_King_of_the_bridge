use serde::{Deserialize, Serialize};

use crate::{GamePath, Sha256};

/// Version of the manifest layout; a payload with another value is refused.
pub const FORMAT: u32 = 1;

/// Description of the mod: every file it writes and how to produce it from the original game.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Manifest {
    pub format: u32,
    /// Version shown to the player, e.g. "Beta 0.1".
    pub version: String,
    pub files: Vec<FileEntry>,
    /// Folders that belong to the mod as a whole and are deleted with it.
    pub owned_dirs: Vec<GamePath>,
    pub settings: LanguageSettings,
}

/// One file the mod writes.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FileEntry {
    pub path: GamePath,
    /// Digest of the file once written.
    pub sha256: Sha256,
    pub content: Content,
}

/// How a mod file is produced.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum Content {
    /// Rewrites the game file at the same path; `patch` is a bsdiff from the original.
    Replace { original: Sha256, patch: String },
    /// A new file made from another, unchanged game file with the bsdiff `patch`.
    Derive { source: GamePath, original: Sha256, patch: String },
    /// A new file stored as is.
    Add { blob: String },
}

impl Content {
    /// Name of the payload blob this content is made from.
    pub fn blob(&self) -> &str {
        match self {
            Self::Replace { patch, .. } | Self::Derive { patch, .. } => patch,
            Self::Add { blob } => blob,
        }
    }
}

/// The game's language setting, which the installer points at Russian.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LanguageSettings {
    /// Value of the `language` setting that selects Russian.
    pub russian: f64,
    /// Value that selects English.
    pub english: f64,
    /// Settings file the game writes on its first start, with Russian already selected.
    pub first_run: serde_json::Value,
}

impl Manifest {
    /// Files the mod adds to the game (everything except rewritten game files).
    pub fn added(&self) -> impl Iterator<Item = &FileEntry> {
        self.files.iter().filter(|entry| !matches!(entry.content, Content::Replace { .. }))
    }
}
