use std::collections::BTreeMap;
use std::error::Error;
use std::fs;
use std::path::Path;

use patchset::{
    BACKUP_DIR, BuildSpec, DeriveRule, GameDir, GamePath, InstallError, LanguageSettings, Payload, State, build,
    inspect, install, uninstall,
};
use serde_json::json;
use tempfile::TempDir;

type TestResult = Result<(), Box<dyn Error>>;

const DATA: &str = "King of the Bridge_Data";

fn write_tree(root: &Path, files: &[(&str, &[u8])]) -> Result<(), Box<dyn Error>> {
    for (path, data) in files {
        let path = GamePath::try_from(*path)?.resolve(root);
        fs::create_dir_all(path.parent().ok_or("no parent")?)?;
        fs::write(path, data)?;
    }
    Ok(())
}

fn snapshot(root: &Path) -> Result<BTreeMap<String, Vec<u8>>, Box<dyn Error>> {
    let mut files = BTreeMap::new();
    let mut pending = vec![root.to_path_buf()];
    while let Some(dir) = pending.pop() {
        for entry in fs::read_dir(dir)? {
            let path = entry?.path();
            if path.is_dir() {
                pending.push(path);
            } else {
                let relative = path.strip_prefix(root)?.to_string_lossy().replace('\\', "/");
                files.insert(relative, fs::read(&path)?);
            }
        }
    }
    Ok(files)
}

fn original_game() -> &'static [(&'static str, &'static [u8])] {
    &[
        ("King of the Bridge.exe", b"exe"),
        ("King of the Bridge_Data/sharedassets0.assets", b"assets with the English language list"),
        ("King of the Bridge_Data/Managed/Assembly-CSharp.dll", b"game code"),
        ("King of the Bridge_Data/aa/strings-english(en)_all.bundle", b"English strings: Hello, Bridge"),
        ("King of the Bridge_Data/aa/locales_all.bundle", b"locales: en, nl"),
    ]
}

/// Builds a payload that turns the original game into the original plus `changes`.
fn payload(version: &str, changes: &[(&str, &[u8])]) -> Result<Payload, Box<dyn Error>> {
    let work = TempDir::new()?;
    let original = work.path().join("original");
    let patched = work.path().join("patched");
    write_tree(&original, original_game())?;
    write_tree(&patched, original_game())?;
    write_tree(&patched, changes)?;
    let spec = BuildSpec {
        version: version.to_owned(),
        owned_dirs: vec![GamePath::try_from("King of the Bridge_Data/StreamingAssets/ru")?],
        derive_rules: vec![
            DeriveRule { from: "-russian(ru)_".into(), to: "-english(en)_".into() },
            DeriveRule { from: "-russian(ru)_".into(), to: "_".into() },
        ],
        settings: LanguageSettings { russian: 2.0, english: 0.0, first_run: json!({ "settingContainers": [] }) },
    };
    Ok(build(&original, &patched, &spec)?)
}

fn beta() -> &'static [(&'static str, &'static [u8])] {
    &[
        ("King of the Bridge_Data/sharedassets0.assets", b"assets with the English, Dutch and Russian list"),
        ("King of the Bridge_Data/Managed/Assembly-CSharp.dll", b"game code calling the helper"),
        ("King of the Bridge_Data/Managed/KotbRussian.dll", b"helper"),
        ("King of the Bridge_Data/aa/strings-russian(ru)_all.bundle", b"Russian strings: Privet, Most"),
        ("King of the Bridge_Data/aa/locales-russian(ru)_all.bundle", b"locales: ru"),
        ("King of the Bridge_Data/StreamingAssets/ru/sprites/or.png", b"tile"),
    ]
}

fn game() -> Result<(TempDir, GameDir), Box<dyn Error>> {
    let dir = TempDir::new()?;
    write_tree(dir.path(), original_game())?;
    let game = GameDir::open(dir.path())?;
    Ok((dir, game))
}

fn expected_after(payload_changes: &[(&str, &[u8])]) -> Result<BTreeMap<String, Vec<u8>>, Box<dyn Error>> {
    let dir = TempDir::new()?;
    write_tree(dir.path(), original_game())?;
    write_tree(dir.path(), payload_changes)?;
    snapshot(dir.path())
}

fn without_backup(mut files: BTreeMap<String, Vec<u8>>) -> BTreeMap<String, Vec<u8>> {
    files.retain(|path, _| !path.starts_with(BACKUP_DIR));
    files
}

#[test]
fn derives_new_bundles_from_the_english_ones() -> TestResult {
    let payload = payload("Beta 0.1", beta())?;
    let kinds: BTreeMap<_, _> =
        payload.manifest.files.iter().map(|f| (f.path.as_str().to_owned(), f.content.clone())).collect();
    assert!(matches!(
        &kinds["King of the Bridge_Data/aa/strings-russian(ru)_all.bundle"],
        patchset::Content::Derive { source, .. } if source.as_str() == "King of the Bridge_Data/aa/strings-english(en)_all.bundle"
    ));
    assert!(matches!(
        &kinds["King of the Bridge_Data/aa/locales-russian(ru)_all.bundle"],
        patchset::Content::Derive { source, .. } if source.as_str() == "King of the Bridge_Data/aa/locales_all.bundle"
    ));
    assert!(matches!(&kinds["King of the Bridge_Data/Managed/KotbRussian.dll"], patchset::Content::Add { .. }));
    assert!(matches!(&kinds[&format!("{DATA}/sharedassets0.assets")], patchset::Content::Replace { .. }));
    Ok(())
}

#[test]
fn installs_and_uninstalls_back_to_the_exact_original() -> TestResult {
    let (dir, game) = game()?;
    let before = snapshot(dir.path())?;
    let payload = payload("Beta 0.1", beta())?;
    assert_eq!(inspect(&game, &payload.manifest)?, State::NotInstalled);

    let mut reported = 0;
    install(&game, &payload, &mut |_| reported += 1)?;
    assert_eq!(reported, payload.manifest.files.len());
    assert_eq!(without_backup(snapshot(dir.path())?), expected_after(beta())?);
    assert_eq!(
        inspect(&game, &payload.manifest)?,
        State::Installed { version: Some("Beta 0.1".into()), current: true }
    );

    uninstall(&game, &payload.manifest, &mut |_| {})?;
    assert_eq!(snapshot(dir.path())?, before);
    assert_eq!(inspect(&game, &payload.manifest)?, State::NotInstalled);
    Ok(())
}

#[test]
fn reinstalling_the_same_version_changes_nothing() -> TestResult {
    let (dir, game) = game()?;
    let payload = payload("Beta 0.1", beta())?;
    install(&game, &payload, &mut |_| {})?;
    let first = snapshot(dir.path())?;
    install(&game, &payload, &mut |_| {})?;
    assert_eq!(snapshot(dir.path())?, first);
    Ok(())
}

#[test]
fn updates_an_older_version_and_drops_its_leftovers() -> TestResult {
    let (dir, game) = game()?;
    let before = snapshot(dir.path())?;
    let mut alpha: Vec<(&str, &[u8])> = beta().to_vec();
    alpha[0].1 = b"assets from the alpha";
    alpha.push(("King of the Bridge_Data/Managed/OldHelper.dll", b"old"));
    let old = payload("Alpha 0.3", &alpha)?;
    install(&game, &old, &mut |_| {})?;

    let new = payload("Beta 0.1", beta())?;
    assert_eq!(inspect(&game, &new.manifest)?, State::Installed { version: Some("Alpha 0.3".into()), current: false });
    install(&game, &new, &mut |_| {})?;
    assert_eq!(without_backup(snapshot(dir.path())?), expected_after(beta())?);

    uninstall(&game, &new.manifest, &mut |_| {})?;
    assert_eq!(snapshot(dir.path())?, before);
    Ok(())
}

#[test]
fn handles_installs_without_a_record() -> TestResult {
    let (dir, game) = game()?;
    let payload = payload("Beta 0.1", beta())?;
    install(&game, &payload, &mut |_| {})?;
    fs::remove_file(dir.path().join(BACKUP_DIR).join("install.json"))?;
    assert_eq!(inspect(&game, &payload.manifest)?, State::Installed { version: None, current: false });
    install(&game, &payload, &mut |_| {})?;
    assert_eq!(without_backup(snapshot(dir.path())?), expected_after(beta())?);
    Ok(())
}

#[test]
fn refuses_an_unknown_game_version_without_touching_it() -> TestResult {
    let (dir, game) = game()?;
    write_tree(dir.path(), &[("King of the Bridge_Data/Managed/Assembly-CSharp.dll", b"game code, patch 1.1")])?;
    let before = snapshot(dir.path())?;
    let payload = payload("Beta 0.1", beta())?;
    let error = install(&game, &payload, &mut |_| {}).err().ok_or("install accepted an unknown game")?;
    assert!(matches!(error, InstallError::UnsupportedGame { path } if path.as_str().ends_with("Assembly-CSharp.dll")));
    assert_eq!(snapshot(dir.path())?, before);
    Ok(())
}

#[test]
fn refuses_to_uninstall_without_backups() -> TestResult {
    let (dir, game) = game()?;
    let payload = payload("Beta 0.1", beta())?;
    install(&game, &payload, &mut |_| {})?;
    fs::remove_dir_all(dir.path().join(BACKUP_DIR))?;
    let before = snapshot(dir.path())?;
    let error = uninstall(&game, &payload.manifest, &mut |_| {}).err().ok_or("uninstall without backups")?;
    assert!(matches!(error, InstallError::MissingBackup { .. }));
    assert_eq!(snapshot(dir.path())?, before);
    Ok(())
}

#[test]
fn rejects_a_damaged_payload_before_writing() -> TestResult {
    let (dir, game) = game()?;
    let before = snapshot(dir.path())?;
    let mut archive = Vec::new();
    payload("Beta 0.1", beta())?.write_tar(&mut archive)?;
    let helper = archive.windows(6).position(|w| w == b"helper").ok_or("blob not found")?;
    archive[helper] = b'H';
    let damaged = Payload::read_tar(archive.as_slice())?;
    let error = install(&game, &damaged, &mut |_| {}).err().ok_or("damaged payload accepted")?;
    assert!(matches!(error, InstallError::CorruptPayload { .. }));
    assert_eq!(snapshot(dir.path())?, before);
    Ok(())
}
