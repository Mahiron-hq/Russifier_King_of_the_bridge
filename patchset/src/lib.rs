//! Everything the installer does to the game folder, kept apart from the window so it can be tested.
//!
//! A [`Payload`] holds the mod as differences against the original game files. [`install`] checks the game
//! against the payload, backs up the files it rewrites and applies the mod; [`uninstall`] puts the originals back.
//! [`remove_alpha`] clears away the BepInEx plugin of the alpha versions.

mod alpha;
mod builder;
mod game;
mod hash;
mod install;
mod manifest;
mod path;
mod payload;
mod settings;
mod version;

pub use alpha::{AlphaRemoval, alpha_installed, remove_alpha};
pub use builder::{BuildError, BuildSpec, DeriveRule, build};
pub use game::{APP_ID, DATA_DIR, EXECUTABLE, GameDir, GameDirError, find_steam_install};
pub use hash::Sha256;
pub use install::{BACKUP_DIR, InstallError, Progress, State, inspect, install, uninstall};
pub use manifest::{Content, FORMAT, FileEntry, LanguageSettings, Manifest};
pub use path::{GamePath, InvalidGamePath};
pub use payload::{Payload, PayloadError};
pub use settings::{PlayerSettings, SettingsError};
pub use version::display_version;
