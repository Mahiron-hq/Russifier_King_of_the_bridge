use std::fs;
use std::io::{self, Cursor};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::manifest::{Content, FileEntry, Manifest};
use crate::{GameDir, GamePath, Payload, PayloadError, Sha256};

/// Folder inside the game where the originals of rewritten files are kept while the mod is installed.
pub const BACKUP_DIR: &str = "RussianMod_backup";
const RECORD: &str = "install.json";
const TEMP_SUFFIX: &str = ".kotb-tmp";

/// What [`inspect`] found in the game folder.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum State {
    NotInstalled,
    /// `version` is unknown for installs made before the installer kept a record.
    Installed {
        version: Option<String>,
        current: bool,
    },
}

#[derive(Debug, Error)]
pub enum InstallError {
    #[error(
        "файл {path} не совпадает ни с одной известной версией. Возможно, вышло обновление игры: \
         проверьте целостность файлов в Steam и скачайте свежую версию русификатора"
    )]
    UnsupportedGame { path: GamePath },
    #[error(
        "нет резервной копии оригинала {path}. Восстановите файлы игры через Steam \
         («Свойства» -> «Установленные файлы» -> «Проверить целостность файлов»)"
    )]
    MissingBackup { path: GamePath },
    #[error("данные русификатора повреждены: {path} получился не таким, как нужно")]
    CorruptPayload { path: GamePath },
    #[error(transparent)]
    Payload(#[from] PayloadError),
    #[error("{}: {source}", path.display())]
    Io {
        path: PathBuf,
        #[source]
        source: io::Error,
    },
}

/// Reported before each file is written or restored.
#[derive(Debug, Clone, Copy)]
pub struct Progress<'a> {
    pub done: usize,
    pub total: usize,
    pub file: &'a GamePath,
}

#[derive(Debug, Default, Serialize, Deserialize)]
struct Record {
    version: String,
    files: Vec<GamePath>,
}

/// Works out whether the mod is installed, and whether the game is a version this payload supports.
///
/// # Errors
/// Returns [`InstallError::UnsupportedGame`] if a game file matches neither the original, the mod's result nor a
/// backed-up original, and [`InstallError::Io`] if a file cannot be read.
pub fn inspect(game: &GameDir, manifest: &Manifest) -> Result<State, InstallError> {
    let root = game.path();
    let backup = root.join(BACKUP_DIR);
    let (mut replaced, mut clean, mut current) = (0, 0, 0);
    for entry in &manifest.files {
        match &entry.content {
            Content::Replace { original, .. } => {
                replaced += 1;
                let now = hash_file(&entry.path.resolve(root))?;
                if now == *original {
                    clean += 1;
                } else if now == entry.sha256 {
                    current += 1;
                } else if hash_existing(&entry.path.resolve(&backup))? != Some(*original) {
                    return Err(InstallError::UnsupportedGame { path: entry.path.clone() });
                }
            }
            Content::Derive { source, original, .. } => {
                if hash_file(&source.resolve(root))? != *original {
                    return Err(InstallError::UnsupportedGame { path: source.clone() });
                }
            }
            Content::Add { .. } => {}
        }
    }
    if clean == replaced && !backup.exists() {
        return Ok(State::NotInstalled);
    }
    let mut added_current = true;
    for entry in manifest.added() {
        added_current &= hash_existing(&entry.path.resolve(root))? == Some(entry.sha256);
    }
    let version = read_record(&backup)?.map(|record| record.version);
    let current = current == replaced && added_current && version.as_deref() == Some(manifest.version.as_str());
    Ok(State::Installed { version, current })
}

/// Installs the mod, replacing any earlier version.
///
/// Every file is produced and checked in memory before the game folder is touched. Originals of rewritten files
/// go to [`BACKUP_DIR`]. If writing fails halfway, the game files are put back as they were originally.
///
/// # Errors
/// Returns [`InstallError`] if the game version is not supported, the payload is damaged or a file cannot be
/// read or written.
pub fn install(game: &GameDir, payload: &Payload, progress: &mut dyn FnMut(Progress<'_>)) -> Result<(), InstallError> {
    let manifest = &payload.manifest;
    inspect(game, manifest)?;
    let root = game.path();
    let backup = root.join(BACKUP_DIR);

    let mut plan = Vec::with_capacity(manifest.files.len());
    for entry in &manifest.files {
        plan.push(prepare(root, &backup, payload, entry)?);
    }

    for planned in &plan {
        if let (Some(original), Content::Replace { original: digest, .. }) = (&planned.original, &planned.entry.content)
        {
            let copy = planned.entry.path.resolve(&backup);
            if hash_existing(&copy)? != Some(*digest) {
                write_atomic(&copy, original)?;
            }
        }
    }

    let previous = read_record(&backup)?.unwrap_or_default();
    let result = remove_added(root, manifest, &previous).and_then(|()| {
        for (done, planned) in plan.iter().enumerate() {
            progress(Progress { done, total: plan.len(), file: &planned.entry.path });
            write_atomic(&planned.entry.path.resolve(root), &planned.output)?;
        }
        let record = Record {
            version: manifest.version.clone(),
            files: manifest.added().map(|entry| entry.path.clone()).collect(),
        };
        write_record(&backup, &record)
    });
    if let Err(error) = result {
        roll_back(root, &backup, manifest, &plan);
        return Err(error);
    }
    Ok(())
}

/// Removes the mod: restores the backed-up originals and deletes everything the mod added.
///
/// All originals are checked before anything is changed.
///
/// # Errors
/// Returns [`InstallError::MissingBackup`] if a rewritten file has no valid backup, and [`InstallError::Io`] if a
/// file cannot be read, written or deleted.
pub fn uninstall(
    game: &GameDir,
    manifest: &Manifest,
    progress: &mut dyn FnMut(Progress<'_>),
) -> Result<(), InstallError> {
    let root = game.path();
    let backup = root.join(BACKUP_DIR);
    let mut restore = Vec::new();
    for entry in &manifest.files {
        let Content::Replace { original, .. } = &entry.content else { continue };
        if hash_file(&entry.path.resolve(root))? == *original {
            continue;
        }
        let copy = entry.path.resolve(&backup);
        let data = read_existing(&copy)?.filter(|data| Sha256::of(data) == *original);
        match data {
            Some(data) => restore.push((&entry.path, data)),
            None => return Err(InstallError::MissingBackup { path: entry.path.clone() }),
        }
    }

    for (done, (path, data)) in restore.iter().enumerate() {
        progress(Progress { done, total: restore.len(), file: path });
        write_atomic(&path.resolve(root), data)?;
    }
    let record = read_record(&backup)?.unwrap_or_default();
    remove_added(root, manifest, &record)?;
    remove_dir(&backup)
}

struct Planned<'a> {
    entry: &'a FileEntry,
    /// Clean original of a rewritten file, when it is still available.
    original: Option<Vec<u8>>,
    output: Vec<u8>,
}

fn prepare<'a>(
    root: &Path,
    backup: &Path,
    payload: &Payload,
    entry: &'a FileEntry,
) -> Result<Planned<'a>, InstallError> {
    let (original, output) = match &entry.content {
        Content::Replace { original: digest, patch } => {
            let now = read(&entry.path.resolve(root))?;
            let original = if Sha256::of(&now) == *digest {
                Some(now.clone())
            } else {
                read_existing(&entry.path.resolve(backup))?.filter(|data| Sha256::of(data) == *digest)
            };
            let output = match &original {
                Some(original) => apply(original, payload.blob(patch)?, &entry.path)?,
                // Already this version's file and its backup is gone: keep it, nothing to rebuild it from.
                None => now,
            };
            (original, output)
        }
        Content::Derive { source, patch, .. } => {
            (None, apply(&read(&source.resolve(root))?, payload.blob(patch)?, &entry.path)?)
        }
        Content::Add { blob } => (None, payload.blob(blob)?.to_vec()),
    };
    if Sha256::of(&output) != entry.sha256 {
        return Err(InstallError::CorruptPayload { path: entry.path.clone() });
    }
    Ok(Planned { entry, original, output })
}

/// Puts the game back to its original files. Best effort: the error that caused it is the one worth reporting.
fn roll_back(root: &Path, backup: &Path, manifest: &Manifest, plan: &[Planned<'_>]) {
    let mut all_restored = true;
    for planned in plan {
        if !matches!(planned.entry.content, Content::Replace { .. }) {
            continue;
        }
        match &planned.original {
            Some(original) => all_restored &= write_atomic(&planned.entry.path.resolve(root), original).is_ok(),
            None => all_restored = false,
        }
    }
    let _ = remove_added(root, manifest, &Record::default());
    if all_restored {
        let _ = remove_dir(backup);
    }
}

fn remove_added(root: &Path, manifest: &Manifest, record: &Record) -> Result<(), InstallError> {
    for path in manifest.added().map(|entry| &entry.path).chain(&record.files) {
        remove_file(&path.resolve(root))?;
    }
    for dir in &manifest.owned_dirs {
        remove_dir(&dir.resolve(root))?;
    }
    Ok(())
}

fn apply(source: &[u8], patch: &[u8], path: &GamePath) -> Result<Vec<u8>, InstallError> {
    let corrupt = |_| InstallError::CorruptPayload { path: path.clone() };
    let patcher = qbsdiff::Bspatch::new(patch).map_err(corrupt)?;
    let mut output = Vec::with_capacity(usize::try_from(patcher.hint_target_size()).unwrap_or(0));
    patcher.apply(source, Cursor::new(&mut output)).map_err(corrupt)?;
    Ok(output)
}

fn read_record(backup: &Path) -> Result<Option<Record>, InstallError> {
    let path = backup.join(RECORD);
    match read_existing(&path)? {
        // A damaged record only loses the version label; the manifest still lists every file to remove.
        Some(data) => Ok(serde_json::from_slice(&data).ok()),
        None => Ok(None),
    }
}

fn write_record(backup: &Path, record: &Record) -> Result<(), InstallError> {
    let path = backup.join(RECORD);
    let data = serde_json::to_vec_pretty(record).map_err(|e| io_error(&path, io::Error::other(e)))?;
    write_atomic(&path, &data)
}

fn hash_file(path: &Path) -> Result<Sha256, InstallError> {
    Ok(Sha256::of(&read(path)?))
}

fn hash_existing(path: &Path) -> Result<Option<Sha256>, InstallError> {
    Ok(read_existing(path)?.map(|data| Sha256::of(&data)))
}

fn read(path: &Path) -> Result<Vec<u8>, InstallError> {
    fs::read(path).map_err(|e| io_error(path, e))
}

fn read_existing(path: &Path) -> Result<Option<Vec<u8>>, InstallError> {
    match fs::read(path) {
        Ok(data) => Ok(Some(data)),
        Err(e) if e.kind() == io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(io_error(path, e)),
    }
}

/// Writes through a temporary file and a rename, so a crash never leaves a half-written game file.
fn write_atomic(path: &Path, data: &[u8]) -> Result<(), InstallError> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| io_error(parent, e))?;
    }
    let mut temp = path.as_os_str().to_owned();
    temp.push(TEMP_SUFFIX);
    let temp = PathBuf::from(temp);
    fs::write(&temp, data).map_err(|e| io_error(&temp, e))?;
    fs::rename(&temp, path).map_err(|e| {
        let _ = fs::remove_file(&temp);
        io_error(path, e)
    })
}

pub(crate) fn remove_file(path: &Path) -> Result<(), InstallError> {
    match fs::remove_file(path) {
        Err(e) if e.kind() != io::ErrorKind::NotFound => Err(io_error(path, e)),
        _ => Ok(()),
    }
}

pub(crate) fn remove_dir(path: &Path) -> Result<(), InstallError> {
    match fs::remove_dir_all(path) {
        Err(e) if e.kind() != io::ErrorKind::NotFound => Err(io_error(path, e)),
        _ => Ok(()),
    }
}

pub(crate) fn io_error(path: &Path, source: io::Error) -> InstallError {
    InstallError::Io { path: path.to_path_buf(), source }
}
