/// The version as players see it: `0.4.0-beta.1` reads "Beta 0.1", `1.2.0` reads "1.2".
///
/// Pre-releases count from 0.1 within their stage, the way the earlier alphas 0.1-0.3 were numbered.
pub fn display_version(cargo_version: &str) -> String {
    let (release, pre) = cargo_version.split_once('-').unwrap_or((cargo_version, ""));
    if let Some((stage, number)) = pre.split_once('.') {
        let mut letters = stage.chars();
        if let Some(first) = letters.next() {
            return format!("{}{} 0.{number}", first.to_uppercase(), letters.as_str());
        }
    }
    let mut parts = release.split('.');
    match (parts.next(), parts.next(), parts.next()) {
        (Some(major), Some(minor), Some("0") | None) => format!("{major}.{minor}"),
        _ => release.to_owned(),
    }
}

#[cfg(test)]
mod tests {
    use super::display_version;

    #[test]
    fn reads_like_the_release_names() {
        assert_eq!(display_version("0.4.0-beta.1"), "Beta 0.1");
        assert_eq!(display_version("0.4.0-beta.2"), "Beta 0.2");
        assert_eq!(display_version("0.3.0-alpha.3"), "Alpha 0.3");
        assert_eq!(display_version("1.0.0"), "1.0");
        assert_eq!(display_version("1.0.2"), "1.0.2");
    }
}
