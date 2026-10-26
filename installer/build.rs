//! Embeds the release build outputs (payload, game art, third-party licences) and the Windows resources.

use std::env;
use std::error::Error;
use std::fs;
use std::path::PathBuf;

/// Files produced by `scripts/build.ps1` under `build/`; missing ones are embedded empty.
const BUILD_OUTPUTS: [(&str, &str); 4] = [
    ("payload.tar", "payload.tar"),
    ("header.png", "ui/header.png"),
    ("logo.png", "ui/logo.png"),
    ("third_party.txt", "ui/third_party.txt"),
];

const MANIFEST: &str = r#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security><requestedPrivileges><requestedExecutionLevel level="asInvoker" uiAccess="false"/></requestedPrivileges></security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application><supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/></application>
  </compatibility>
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/pm</dpiAware>
      <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>
    </windowsSettings>
  </application>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity type="win32" name="Microsoft.Windows.Common-Controls" version="6.0.0.0"
        processorArchitecture="*" publicKeyToken="6595b64144ccf1df" language="*"/>
    </dependentAssembly>
  </dependency>
</assembly>
"#;

fn main() -> Result<(), Box<dyn Error>> {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR")?);
    let build_dir = manifest_dir.join("..").join("build");
    let out_dir = PathBuf::from(env::var("OUT_DIR")?);
    for (name, source) in BUILD_OUTPUTS {
        let source = build_dir.join(source);
        println!("cargo:rerun-if-changed={}", source.display());
        let data = if source.is_file() { fs::read(&source)? } else { Vec::new() };
        fs::write(out_dir.join(name), data)?;
    }

    if env::var("CARGO_CFG_TARGET_OS")? == "windows" {
        let version = env::var("CARGO_PKG_VERSION")?;
        let numeric = file_version()?;
        let mut resource = winresource::WindowsResource::new();
        resource
            .set_icon("assets/icon.ico")
            .set_manifest(MANIFEST)
            .set_language(0x0419)
            .set("FileDescription", "Русификатор King of the Bridge")
            .set("ProductName", "Русификатор King of the Bridge")
            .set("CompanyName", "Mahiron-hq")
            .set("LegalCopyright", "© 2026 Lev Burmistrov (Mahiron-hq). CC BY-NC-SA 4.0")
            .set("FileVersion", &version)
            .set("ProductVersion", &version)
            .set("OriginalFilename", "KotB_Russian_Installer.exe")
            .set("InternalName", "installer")
            .set_version_info(winresource::VersionInfo::FILEVERSION, numeric)
            .set_version_info(winresource::VersionInfo::PRODUCTVERSION, numeric);
        resource.compile()?;
    }
    Ok(())
}

/// `MAJOR.MINOR.PATCH.N` for the Windows version fields, where N is the pre-release number (`beta.1` -> 1).
fn file_version() -> Result<u64, Box<dyn Error>> {
    let part = |name: &str| -> Result<u64, Box<dyn Error>> { Ok(env::var(name)?.parse()?) };
    let pre = env::var("CARGO_PKG_VERSION_PRE")?;
    let build = pre.rsplit('.').next().and_then(|n| n.parse::<u64>().ok()).unwrap_or(0);
    Ok(part("CARGO_PKG_VERSION_MAJOR")? << 48
        | part("CARGO_PKG_VERSION_MINOR")? << 32
        | part("CARGO_PKG_VERSION_PATCH")? << 16
        | build)
}
