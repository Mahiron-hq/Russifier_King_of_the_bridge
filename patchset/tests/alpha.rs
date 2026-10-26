use std::collections::BTreeSet;
use std::error::Error;
use std::fs;
use std::path::Path;

use patchset::{AlphaRemoval, GameDir, alpha_installed, remove_alpha};
use tempfile::TempDir;

type TestResult = Result<(), Box<dyn Error>>;

const GAME: [&str; 3] = ["King of the Bridge.exe", "King of the Bridge_Data/sharedassets0.assets", "UnityPlayer.dll"];

/// Layout of the alpha 0.3 archive after the game has been started once with it.
const ALPHA: [&str; 13] = [
    "winhttp.dll",
    "doorstop_config.ini",
    "BepInEx/LogOutput.log",
    "BepInEx/cache/chainloader_typeloader.dat",
    "BepInEx/config/BepInEx.cfg",
    "BepInEx/core/BepInEx.dll",
    "BepInEx/core/0Harmony.dll",
    "BepInEx/plugins/RussianTranslationMod.dll",
    "BepInEx/plugins/translation.txt",
    "BepInEx/plugins/image_mapping.txt",
    "BepInEx/plugins/alagard-unicode-tmp",
    "BepInEx/plugins/untranslated.txt",
    "BepInEx/plugins/image/page1.png",
];

fn game_with(files: &[&str]) -> Result<(TempDir, GameDir), Box<dyn Error>> {
    let dir = TempDir::new()?;
    for file in GAME.iter().chain(files) {
        let path = dir.path().join(file);
        fs::create_dir_all(path.parent().ok_or("no parent")?)?;
        fs::write(path, file.as_bytes())?;
    }
    if files.iter().any(|f| f.starts_with("BepInEx/")) {
        // BepInEx ships an empty patchers folder.
        fs::create_dir_all(dir.path().join("BepInEx/patchers"))?;
    }
    let game = GameDir::open(dir.path())?;
    Ok((dir, game))
}

fn files(root: &Path) -> Result<BTreeSet<String>, Box<dyn Error>> {
    let mut found = BTreeSet::new();
    let mut pending = vec![root.to_path_buf()];
    while let Some(dir) = pending.pop() {
        for entry in fs::read_dir(dir)? {
            let path = entry?.path();
            if path.is_dir() {
                pending.push(path);
            } else {
                found.insert(path.strip_prefix(root)?.to_string_lossy().replace('\\', "/"));
            }
        }
    }
    Ok(found)
}

fn names(list: &[&str]) -> BTreeSet<String> {
    list.iter().map(|s| (*s).to_owned()).collect()
}

#[test]
fn alpha_alone_goes_with_bepinex() -> TestResult {
    let (dir, game) = game_with(&ALPHA)?;
    assert!(alpha_installed(&game));
    assert_eq!(remove_alpha(&game)?, AlphaRemoval::Removed);
    assert_eq!(files(dir.path())?, names(&GAME));
    assert!(!dir.path().join("BepInEx").exists());
    assert!(!alpha_installed(&game));
    Ok(())
}

#[test]
fn bepinex_stays_for_other_plugins() -> TestResult {
    let (dir, game) = game_with(&[&ALPHA[..], &["BepInEx/plugins/OtherMod/OtherMod.dll"]].concat())?;
    assert_eq!(remove_alpha(&game)?, AlphaRemoval::BepInExKept);
    let left = files(dir.path())?;
    let plugin = ALPHA.iter().filter(|f| f.starts_with("BepInEx/plugins/"));
    assert!(plugin.into_iter().all(|f| !left.contains(*f)), "plugin files left: {left:?}");
    for kept in
        ["winhttp.dll", "doorstop_config.ini", "BepInEx/core/BepInEx.dll", "BepInEx/plugins/OtherMod/OtherMod.dll"]
    {
        assert!(left.contains(kept), "{kept} was removed");
    }
    Ok(())
}

#[test]
fn bepinex_stays_for_patchers() -> TestResult {
    let (dir, game) = game_with(&[&ALPHA[..], &["BepInEx/patchers/Fix.dll"]].concat())?;
    assert_eq!(remove_alpha(&game)?, AlphaRemoval::BepInExKept);
    assert!(dir.path().join("winhttp.dll").is_file());
    assert!(!dir.path().join("BepInEx/plugins/RussianTranslationMod.dll").exists());
    Ok(())
}

#[test]
fn empty_plugin_folders_do_not_keep_bepinex() -> TestResult {
    let (dir, game) = game_with(&ALPHA)?;
    fs::create_dir_all(dir.path().join("BepInEx/plugins/Empty/Nested"))?;
    assert_eq!(remove_alpha(&game)?, AlphaRemoval::Removed);
    assert_eq!(files(dir.path())?, names(&GAME));
    Ok(())
}

#[test]
fn bepinex_without_the_alpha_is_left_alone() -> TestResult {
    let mods = ["winhttp.dll", "doorstop_config.ini", "BepInEx/core/BepInEx.dll", "BepInEx/plugins/OtherMod.dll"];
    let (dir, game) = game_with(&mods)?;
    let before = files(dir.path())?;
    assert!(!alpha_installed(&game));
    assert_eq!(remove_alpha(&game)?, AlphaRemoval::NotFound);
    assert_eq!(files(dir.path())?, before);
    Ok(())
}
