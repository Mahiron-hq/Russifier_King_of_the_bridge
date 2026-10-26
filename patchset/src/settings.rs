use std::fs;
use std::io;
use std::path::{Path, PathBuf};

use serde_json::{Value, json};
use thiserror::Error;

use crate::LanguageSettings;

const LANGUAGE_ID: &str = "language";

/// The game's `player_settings.txt`, a JSON list of `{settingID, settingValue}` containers.
#[derive(Debug, Clone)]
pub struct PlayerSettings {
    path: PathBuf,
}

#[derive(Debug, Error)]
pub enum SettingsError {
    #[error("{}: {source}", path.display())]
    Io {
        path: PathBuf,
        #[source]
        source: io::Error,
    },
    #[error("{}: файл настроек игры повреждён ({source})", path.display())]
    Json {
        path: PathBuf,
        #[source]
        source: serde_json::Error,
    },
    #[error("{}: в файле настроек игры нет списка настроек", path.display())]
    Layout { path: PathBuf },
}

impl PlayerSettings {
    /// The settings file of the current Windows user, in `AppData\LocalLow\Finn Schuuring\King of the Bridge`.
    pub fn locate() -> Option<Self> {
        let low = known_folders::get_known_folder_path(known_folders::KnownFolder::LocalAppDataLow)?;
        Some(Self::at(low.join("Finn Schuuring").join("King of the Bridge").join("player_settings.txt")))
    }

    pub fn at(path: impl Into<PathBuf>) -> Self {
        Self { path: path.into() }
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Selects Russian. Creates the game's first-run settings if the game has never been started.
    ///
    /// # Errors
    /// Returns [`SettingsError`] if the file cannot be read, parsed or written.
    pub fn select_russian(&self, language: &LanguageSettings) -> Result<(), SettingsError> {
        match self.read()? {
            Some(mut settings) => {
                self.set_language(&mut settings, language.russian)?;
                self.write(&settings)
            }
            None => self.write(&language.first_run),
        }
    }

    /// Switches the game back to English if Russian is selected; the game would otherwise point past its
    /// language list once the Russian locale is gone.
    ///
    /// # Errors
    /// Returns [`SettingsError`] if the file cannot be read, parsed or written.
    pub fn reset_to_english(&self, language: &LanguageSettings) -> Result<(), SettingsError> {
        let Some(mut settings) = self.read()? else { return Ok(()) };
        if self.language(&settings)? == Some(language.russian) {
            self.set_language(&mut settings, language.english)?;
            self.write(&settings)?;
        }
        Ok(())
    }

    fn read(&self) -> Result<Option<Value>, SettingsError> {
        match fs::read(&self.path) {
            Ok(data) => serde_json::from_slice(&data)
                .map(Some)
                .map_err(|source| SettingsError::Json { path: self.path.clone(), source }),
            Err(e) if e.kind() == io::ErrorKind::NotFound => Ok(None),
            Err(source) => Err(SettingsError::Io { path: self.path.clone(), source }),
        }
    }

    fn write(&self, settings: &Value) -> Result<(), SettingsError> {
        let io = |source| SettingsError::Io { path: self.path.clone(), source };
        if let Some(parent) = self.path.parent() {
            fs::create_dir_all(parent).map_err(io)?;
        }
        let data = serde_json::to_vec(settings).map_err(|e| io(io::Error::other(e)))?;
        fs::write(&self.path, data).map_err(io)
    }

    fn containers<'a>(&self, settings: &'a mut Value) -> Result<&'a mut Vec<Value>, SettingsError> {
        settings
            .get_mut("settingContainers")
            .and_then(Value::as_array_mut)
            .ok_or_else(|| SettingsError::Layout { path: self.path.clone() })
    }

    fn language(&self, settings: &Value) -> Result<Option<f64>, SettingsError> {
        let containers = settings
            .get("settingContainers")
            .and_then(Value::as_array)
            .ok_or_else(|| SettingsError::Layout { path: self.path.clone() })?;
        Ok(containers
            .iter()
            .find(|c| c.get("settingID").and_then(Value::as_str) == Some(LANGUAGE_ID))
            .and_then(|c| c.get("settingValue")?.get(0)?.as_f64()))
    }

    fn set_language(&self, settings: &mut Value, value: f64) -> Result<(), SettingsError> {
        let containers = self.containers(settings)?;
        let entry = json!({ "settingID": LANGUAGE_ID, "settingValue": [value] });
        match containers.iter_mut().find(|c| c.get("settingID").and_then(Value::as_str) == Some(LANGUAGE_ID)) {
            Some(container) => *container = entry,
            None => containers.push(entry),
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn language() -> LanguageSettings {
        LanguageSettings {
            russian: 2.0,
            english: 0.0,
            first_run: json!({ "settingContainers": [
                { "settingID": "vsync", "settingValue": [1.0] },
                { "settingID": "language", "settingValue": [2.0] },
            ]}),
        }
    }

    #[test]
    fn selects_russian_and_keeps_other_settings() -> Result<(), Box<dyn std::error::Error>> {
        let dir = tempfile::tempdir()?;
        let path = dir.path().join("player_settings.txt");
        fs::write(
            &path,
            r#"{"settingContainers":[{"settingID":"fullscreen","settingValue":[1.0]},{"settingID":"language","settingValue":[0.0]}]}"#,
        )?;
        let settings = PlayerSettings::at(&path);

        settings.select_russian(&language())?;
        assert_eq!(
            fs::read_to_string(&path)?,
            r#"{"settingContainers":[{"settingID":"fullscreen","settingValue":[1.0]},{"settingID":"language","settingValue":[2.0]}]}"#
        );

        settings.reset_to_english(&language())?;
        assert!(fs::read_to_string(&path)?.contains(r#"{"settingID":"language","settingValue":[0.0]}"#));
        Ok(())
    }

    #[test]
    fn writes_first_run_settings_when_the_game_never_started() -> Result<(), Box<dyn std::error::Error>> {
        let dir = tempfile::tempdir()?;
        let settings = PlayerSettings::at(dir.path().join("sub").join("player_settings.txt"));
        settings.select_russian(&language())?;
        let written: Value = serde_json::from_slice(&fs::read(settings.path())?)?;
        assert_eq!(written, language().first_run);
        Ok(())
    }

    #[test]
    fn leaves_dutch_alone_on_reset() -> Result<(), Box<dyn std::error::Error>> {
        let dir = tempfile::tempdir()?;
        let path = dir.path().join("player_settings.txt");
        let dutch = r#"{"settingContainers":[{"settingID":"language","settingValue":[1.0]}]}"#;
        fs::write(&path, dutch)?;
        PlayerSettings::at(&path).reset_to_english(&language())?;
        assert_eq!(fs::read_to_string(&path)?, dutch);
        Ok(())
    }
}
