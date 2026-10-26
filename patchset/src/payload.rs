use std::collections::BTreeMap;
use std::io::{self, Read, Write};

use thiserror::Error;

use crate::manifest::{FORMAT, Manifest};

const MANIFEST_ENTRY: &str = "manifest.json";
const BLOB_PREFIX: &str = "blobs/";

/// The mod as shipped inside the installer: a manifest and the blobs it refers to, stored as a tar archive.
#[derive(Debug, Clone, PartialEq)]
pub struct Payload {
    pub manifest: Manifest,
    blobs: BTreeMap<String, Vec<u8>>,
}

#[derive(Debug, Error)]
pub enum PayloadError {
    #[error("ошибка чтения данных русификатора: {0}")]
    Io(#[from] io::Error),
    #[error("описание русификатора повреждено: {0}")]
    Json(#[from] serde_json::Error),
    #[error("в данных русификатора нет описания")]
    MissingManifest,
    #[error("формат данных {0} не поддерживается")]
    UnsupportedFormat(u32),
    #[error("в данных русификатора нет файла {0}")]
    MissingBlob(String),
    #[error("лишний файл в данных русификатора: {0}")]
    UnexpectedEntry(String),
}

impl Payload {
    /// Pairs a manifest with its blobs.
    ///
    /// # Errors
    /// Returns [`PayloadError::MissingBlob`] if the manifest refers to a blob that is not given and
    /// [`PayloadError::UnsupportedFormat`] if the manifest has another layout version.
    pub fn new(manifest: Manifest, blobs: BTreeMap<String, Vec<u8>>) -> Result<Self, PayloadError> {
        if manifest.format != FORMAT {
            return Err(PayloadError::UnsupportedFormat(manifest.format));
        }
        if let Some(missing) = manifest.files.iter().map(|f| f.content.blob()).find(|b| !blobs.contains_key(*b)) {
            return Err(PayloadError::MissingBlob(missing.to_owned()));
        }
        Ok(Self { manifest, blobs })
    }

    /// Contents of a blob named in the manifest.
    ///
    /// # Errors
    /// Returns [`PayloadError::MissingBlob`] for an unknown name.
    pub fn blob(&self, name: &str) -> Result<&[u8], PayloadError> {
        self.blobs.get(name).map(Vec::as_slice).ok_or_else(|| PayloadError::MissingBlob(name.to_owned()))
    }

    /// Writes the payload as a tar archive. Entries carry no timestamps, so equal payloads give equal bytes.
    ///
    /// # Errors
    /// Returns [`PayloadError::Io`] if writing fails.
    pub fn write_tar(&self, out: impl Write) -> Result<(), PayloadError> {
        let mut builder = tar::Builder::new(out);
        let manifest = serde_json::to_vec_pretty(&self.manifest)?;
        append(&mut builder, MANIFEST_ENTRY, &manifest)?;
        for (name, data) in &self.blobs {
            append(&mut builder, &format!("{BLOB_PREFIX}{name}"), data)?;
        }
        builder.into_inner()?.flush()?;
        Ok(())
    }

    /// Reads a payload written by [`Payload::write_tar`].
    ///
    /// # Errors
    /// Returns a [`PayloadError`] if the archive is damaged, lacks the manifest or a blob, or has extra entries.
    pub fn read_tar(input: impl Read) -> Result<Self, PayloadError> {
        let mut archive = tar::Archive::new(input);
        let mut manifest = None;
        let mut blobs = BTreeMap::new();
        for entry in archive.entries()? {
            let mut entry = entry?;
            let name = entry.path()?.to_string_lossy().replace('\\', "/");
            let mut data = Vec::new();
            entry.read_to_end(&mut data)?;
            if name == MANIFEST_ENTRY {
                manifest = Some(serde_json::from_slice::<Manifest>(&data)?);
            } else if let Some(blob) = name.strip_prefix(BLOB_PREFIX) {
                blobs.insert(blob.to_owned(), data);
            } else {
                return Err(PayloadError::UnexpectedEntry(name));
            }
        }
        Self::new(manifest.ok_or(PayloadError::MissingManifest)?, blobs)
    }
}

fn append(builder: &mut tar::Builder<impl Write>, name: &str, data: &[u8]) -> io::Result<()> {
    let mut header = tar::Header::new_gnu();
    header.set_size(data.len() as u64);
    header.set_mode(0o644);
    header.set_mtime(0);
    builder.append_data(&mut header, name, data)
}
