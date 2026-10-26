use std::fmt;
use std::path::{Component, Path, PathBuf};

use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Location of a file inside the game folder: relative, `/`-separated, never leaving the folder.
#[derive(Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(try_from = "String", into = "String")]
pub struct GamePath(String);

/// A string that is not a valid [`GamePath`].
#[derive(Debug, Error)]
#[error("недопустимый путь внутри папки игры: {0:?}")]
pub struct InvalidGamePath(pub String);

impl GamePath {
    /// Converts a path relative to the game folder.
    ///
    /// # Errors
    /// Returns [`InvalidGamePath`] for absolute paths and paths with `.`, `..` or non-UTF-8 components.
    pub fn from_relative(path: &Path) -> Result<Self, InvalidGamePath> {
        let mut parts = Vec::new();
        for component in path.components() {
            match component {
                Component::Normal(part) => match part.to_str() {
                    Some(part) => parts.push(part),
                    None => return Err(InvalidGamePath(path.display().to_string())),
                },
                _ => return Err(InvalidGamePath(path.display().to_string())),
            }
        }
        Self::try_from(parts.join("/"))
    }

    /// The path as stored in the manifest.
    pub fn as_str(&self) -> &str {
        &self.0
    }

    /// The file's location under `root`.
    pub fn resolve(&self, root: &Path) -> PathBuf {
        self.0.split('/').fold(root.to_path_buf(), |path, part| path.join(part))
    }
}

impl TryFrom<String> for GamePath {
    type Error = InvalidGamePath;

    fn try_from(value: String) -> Result<Self, Self::Error> {
        let valid = !value.is_empty()
            && value
                .split('/')
                .all(|part| !part.is_empty() && part != "." && part != ".." && !part.contains(['\\', ':']));
        if valid { Ok(Self(value)) } else { Err(InvalidGamePath(value)) }
    }
}

impl TryFrom<&str> for GamePath {
    type Error = InvalidGamePath;

    fn try_from(value: &str) -> Result<Self, Self::Error> {
        Self::try_from(value.to_owned())
    }
}

impl From<GamePath> for String {
    fn from(path: GamePath) -> Self {
        path.0
    }
}

impl fmt::Display for GamePath {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl fmt::Debug for GamePath {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Debug::fmt(&self.0, f)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_paths_that_leave_the_game_folder() {
        for bad in ["", "/abs", "a/../b", "a//b", "./a", "C:/x", "a\\b"] {
            assert!(GamePath::try_from(bad).is_err(), "{bad:?} accepted");
        }
    }

    #[test]
    fn converts_native_relative_paths() -> Result<(), InvalidGamePath> {
        let path = GamePath::from_relative(Path::new("Data").join("Managed").join("a.dll").as_path())?;
        assert_eq!(path.as_str(), "Data/Managed/a.dll");
        assert_eq!(path.resolve(Path::new("root")), Path::new("root").join("Data").join("Managed").join("a.dll"));
        Ok(())
    }
}
