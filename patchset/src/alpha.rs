//! The alpha versions 0.1-0.3: a BepInEx plugin that translated the game while it ran.
//!
//! Left in place, the plugin keeps swapping the rulebook pages for its own older pictures, so it goes when the mod
//! is installed or removed. BepInEx itself goes too, unless other mods still use it.

use std::fs;
use std::io;
use std::path::Path;

use crate::GameDir;
use crate::install::{InstallError, io_error, remove_dir, remove_file};

const BEPINEX: &str = "BepInEx";
const PLUGINS: &str = "BepInEx/plugins";
const PATCHERS: &str = "BepInEx/patchers";
const PLUGIN: &str = "RussianTranslationMod.dll";
/// What the plugin keeps next to itself; `untranslated.txt` is written while the game runs.
const PLUGIN_FILES: [&str; 5] =
    [PLUGIN, "translation.txt", "image_mapping.txt", "alagard-unicode-tmp", "untranslated.txt"];
const PLUGIN_DIRS: [&str; 1] = ["image"];
/// The loader the alpha archives put next to the game executable.
const LOADER_FILES: [&str; 2] = ["winhttp.dll", "doorstop_config.ini"];

/// What [`remove_alpha`] did.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AlphaRemoval {
    NotFound,
    /// The plugin and BepInEx are gone.
    Removed,
    /// The plugin is gone; BepInEx stays because other mods are installed in it.
    BepInExKept,
}

/// Whether the alpha plugin is in the game folder.
pub fn alpha_installed(game: &GameDir) -> bool {
    game.path().join(PLUGINS).join(PLUGIN).is_file()
}

/// Deletes the alpha plugin, and BepInEx with its loader when no other plugin or patcher is left in it.
///
/// # Errors
/// Returns [`InstallError::Io`] if a file cannot be listed or deleted.
pub fn remove_alpha(game: &GameDir) -> Result<AlphaRemoval, InstallError> {
    if !alpha_installed(game) {
        return Ok(AlphaRemoval::NotFound);
    }
    let root = game.path();
    let plugins = root.join(PLUGINS);
    for file in PLUGIN_FILES {
        remove_file(&plugins.join(file))?;
    }
    for dir in PLUGIN_DIRS {
        remove_dir(&plugins.join(dir))?;
    }

    if has_files(&plugins)? || has_files(&root.join(PATCHERS))? {
        return Ok(AlphaRemoval::BepInExKept);
    }
    for file in LOADER_FILES {
        remove_file(&root.join(file))?;
    }
    remove_dir(&root.join(BEPINEX))?;
    Ok(AlphaRemoval::Removed)
}

fn has_files(dir: &Path) -> Result<bool, InstallError> {
    let entries = match fs::read_dir(dir) {
        Ok(entries) => entries,
        Err(e) if e.kind() == io::ErrorKind::NotFound => return Ok(false),
        Err(e) => return Err(io_error(dir, e)),
    };
    for entry in entries {
        let path = entry.map_err(|e| io_error(dir, e))?.path();
        if !path.is_dir() || has_files(&path)? {
            return Ok(true);
        }
    }
    Ok(false)
}
