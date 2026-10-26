use std::fmt::Display;
use std::fs;
use std::path::Path;

use patchset::{BuildSpec, GameDir, LanguageSettings, Payload, build, install, uninstall};
use proptest::prelude::*;
use serde_json::json;

fn spec() -> BuildSpec {
    BuildSpec {
        version: "test".into(),
        owned_dirs: Vec::new(),
        derive_rules: Vec::new(),
        settings: LanguageSettings { russian: 2.0, english: 0.0, first_run: json!({}) },
    }
}

fn fail(error: impl Display) -> TestCaseError {
    TestCaseError::fail(error.to_string())
}

fn game_with(dir: &Path, file: &str, data: &[u8]) -> Result<(), TestCaseError> {
    fs::create_dir_all(dir.join("King of the Bridge_Data")).map_err(fail)?;
    fs::write(dir.join("King of the Bridge.exe"), b"exe").map_err(fail)?;
    fs::write(dir.join(file), data).map_err(fail)
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(48))]

    /// Any pair of file contents survives build, tar, read, install and uninstall unchanged.
    #[test]
    fn rewritten_files_round_trip(
        original in proptest::collection::vec(any::<u8>(), 0..4096),
        patched in proptest::collection::vec(any::<u8>(), 0..4096),
        added in proptest::collection::vec(any::<u8>(), 0..512),
    ) {
        let work = tempfile::tempdir().map_err(fail)?;
        let (a, b) = (work.path().join("a"), work.path().join("b"));
        let file = "King of the Bridge_Data/file.bin";
        let new = "King of the Bridge_Data/new.bin";
        game_with(&a, file, &original)?;
        game_with(&b, file, &patched)?;
        fs::write(b.join(new), &added).map_err(fail)?;

        let payload = build(&a, &b, &spec()).map_err(fail)?;
        let mut archive = Vec::new();
        payload.write_tar(&mut archive).map_err(fail)?;
        let read = Payload::read_tar(archive.as_slice()).map_err(fail)?;
        prop_assert_eq!(&read, &payload);

        let game = GameDir::open(&a).map_err(fail)?;
        install(&game, &read, &mut |_| {}).map_err(fail)?;
        prop_assert_eq!(fs::read(a.join(file)).map_err(fail)?, patched);
        prop_assert_eq!(fs::read(a.join(new)).map_err(fail)?, added);
        uninstall(&game, &read.manifest, &mut |_| {}).map_err(fail)?;
        prop_assert_eq!(fs::read(a.join(file)).map_err(fail)?, original);
        prop_assert!(!a.join(new).exists());
    }
}

#[test]
fn tar_output_is_reproducible() -> Result<(), Box<dyn std::error::Error>> {
    let work = tempfile::tempdir()?;
    let (a, b) = (work.path().join("a"), work.path().join("b"));
    fs::create_dir_all(&a)?;
    fs::create_dir_all(&b)?;
    fs::write(b.join("x.bin"), b"x")?;
    let payload = build(&a, &b, &spec())?;
    let (mut first, mut second) = (Vec::new(), Vec::new());
    payload.write_tar(&mut first)?;
    payload.write_tar(&mut second)?;
    assert_eq!(first, second);
    assert_eq!(Payload::read_tar(first.as_slice())?.manifest.files.len(), 1);
    Ok(())
}
