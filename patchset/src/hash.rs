use std::fmt;

use serde::{Deserialize, Serialize};
use sha2::Digest;

/// SHA-256 digest of a file's contents, written as lowercase hex in the manifest.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Sha256(#[serde(with = "hex::serde")] [u8; 32]);

impl Sha256 {
    /// Digest of `bytes`.
    pub fn of(bytes: &[u8]) -> Self {
        Self(sha2::Sha256::digest(bytes).into())
    }
}

impl fmt::Display for Sha256 {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&hex::encode(self.0))
    }
}

impl fmt::Debug for Sha256 {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Display::fmt(self, f)
    }
}
