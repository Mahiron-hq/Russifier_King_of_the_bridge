use std::path::{Path, PathBuf};

use thiserror::Error;

/// Steam app id of King of the Bridge.
pub const APP_ID: u32 = 2_523_120;
pub const EXECUTABLE: &str = "King of the Bridge.exe";
pub const DATA_DIR: &str = "King of the Bridge_Data";

/// A folder that holds the game.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameDir(PathBuf);

#[derive(Debug, Error)]
pub enum GameDirError {
    #[error("в этой папке нет {EXECUTABLE}")]
    NoExecutable,
    #[error("в этой папке нет {DATA_DIR}")]
    NoData,
}

impl GameDir {
    /// Accepts `path` if it contains the game's executable and data folder.
    ///
    /// # Errors
    /// Returns [`GameDirError`] naming the part that is missing.
    pub fn open(path: impl Into<PathBuf>) -> Result<Self, GameDirError> {
        let path = path.into();
        if !path.join(EXECUTABLE).is_file() {
            return Err(GameDirError::NoExecutable);
        }
        if !path.join(DATA_DIR).is_dir() {
            return Err(GameDirError::NoData);
        }
        Ok(Self(path))
    }

    pub fn path(&self) -> &Path {
        &self.0
    }
}

/// Where Steam installed the game, if Steam and the game are found.
pub fn find_steam_install() -> Option<PathBuf> {
    let steam = steamlocate::SteamDir::locate().ok()?;
    let (app, library) = steam.find_app(APP_ID).ok()??;
    Some(library.resolve_app_dir(&app))
}
