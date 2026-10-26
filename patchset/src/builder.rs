use std::collections::BTreeMap;
use std::fs;
use std::io::{self, Cursor};
use std::path::{Path, PathBuf};

use thiserror::Error;

use crate::manifest::{Content, FORMAT, FileEntry, LanguageSettings, Manifest};
use crate::{GamePath, InvalidGamePath, Payload, PayloadError, Sha256};

/// Renames a new file's name into the name of the game file it is derived from, e.g. the Russian bundle into the
/// English bundle it was cloned from.
#[derive(Debug, Clone)]
pub struct DeriveRule {
    pub from: String,
    pub to: String,
}

/// What [`build`] needs besides the two game copies.
#[derive(Debug, Clone)]
pub struct BuildSpec {
    pub version: String,
    pub owned_dirs: Vec<GamePath>,
    /// Tried in order on each new file; the first that names an existing original file wins.
    pub derive_rules: Vec<DeriveRule>,
    pub settings: LanguageSettings,
}

#[derive(Debug, Error)]
pub enum BuildError {
    #[error("{path}: {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: io::Error,
    },
    #[error(transparent)]
    Path(#[from] InvalidGamePath),
    #[error("{0} exists in the original game but not in the patched copy; the mod never deletes game files")]
    Removed(GamePath),
    #[error(transparent)]
    Payload(#[from] PayloadError),
}

/// Compares an original game folder with a patched copy and packs the difference.
///
/// Changed files become [`Content::Replace`], new files become [`Content::Derive`] when a [`DeriveRule`] names an
/// original file to diff against, and [`Content::Add`] otherwise.
///
/// # Errors
/// Returns a [`BuildError`] if a folder cannot be read or the patched copy lacks an original file.
pub fn build(original: &Path, patched: &Path, spec: &BuildSpec) -> Result<Payload, BuildError> {
    let original_files = list_files(original)?;
    let patched_files = list_files(patched)?;
    if let Some(removed) = original_files.keys().find(|p| !patched_files.contains_key(*p)) {
        return Err(BuildError::Removed(removed.clone()));
    }

    let mut files = Vec::new();
    let mut blobs = BTreeMap::new();
    for (path, patched_path) in &patched_files {
        let data = read(patched_path)?;
        let content = match original_files.get(path) {
            Some(original_path) => {
                let source = read(original_path)?;
                if source == data {
                    continue;
                }
                let patch = format!("{path}.bsdiff");
                blobs.insert(patch.clone(), diff(&source, &data, original_path)?);
                Content::Replace { original: Sha256::of(&source), patch }
            }
            None => match derive_source(path, &original_files, &spec.derive_rules)? {
                Some((source, source_path)) => {
                    let source_data = read(source_path)?;
                    let patch = format!("{path}.bsdiff");
                    blobs.insert(patch.clone(), diff(&source_data, &data, source_path)?);
                    Content::Derive { source, original: Sha256::of(&source_data), patch }
                }
                None => {
                    let blob = path.to_string();
                    blobs.insert(blob.clone(), data.clone());
                    Content::Add { blob }
                }
            },
        };
        files.push(FileEntry { path: path.clone(), sha256: Sha256::of(&data), content });
    }

    let manifest = Manifest {
        format: FORMAT,
        version: spec.version.clone(),
        files,
        owned_dirs: spec.owned_dirs.clone(),
        settings: spec.settings.clone(),
    };
    Ok(Payload::new(manifest, blobs)?)
}

fn derive_source<'a>(
    path: &GamePath,
    original_files: &'a BTreeMap<GamePath, PathBuf>,
    rules: &[DeriveRule],
) -> Result<Option<(GamePath, &'a PathBuf)>, BuildError> {
    for rule in rules {
        if !path.as_str().contains(&rule.from) {
            continue;
        }
        let candidate = GamePath::try_from(path.as_str().replace(&rule.from, &rule.to))?;
        if let Some(found) = original_files.get(&candidate) {
            return Ok(Some((candidate, found)));
        }
    }
    Ok(None)
}

fn list_files(root: &Path) -> Result<BTreeMap<GamePath, PathBuf>, BuildError> {
    let mut files = BTreeMap::new();
    let mut pending = vec![root.to_path_buf()];
    while let Some(dir) = pending.pop() {
        let entries = fs::read_dir(&dir).map_err(|source| BuildError::Io { path: dir.clone(), source })?;
        for entry in entries {
            let entry = entry.map_err(|source| BuildError::Io { path: dir.clone(), source })?;
            let path = entry.path();
            let kind = entry.file_type().map_err(|source| BuildError::Io { path: path.clone(), source })?;
            if kind.is_dir() {
                pending.push(path);
            } else if kind.is_file() {
                let relative = path.strip_prefix(root).unwrap_or(&path);
                files.insert(GamePath::from_relative(relative)?, path);
            }
        }
    }
    Ok(files)
}

fn read(path: &Path) -> Result<Vec<u8>, BuildError> {
    fs::read(path).map_err(|source| BuildError::Io { path: path.to_path_buf(), source })
}

fn diff(source: &[u8], target: &[u8], path: &Path) -> Result<Vec<u8>, BuildError> {
    let mut patch = Vec::new();
    qbsdiff::Bsdiff::new(source, target)
        .compare(Cursor::new(&mut patch))
        .map_err(|source| BuildError::Io { path: path.to_path_buf(), source })?;
    Ok(patch)
}
