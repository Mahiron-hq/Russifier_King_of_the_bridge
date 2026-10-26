//! Files baked into the executable. The payload and the game art come from the release build (`build/`); a build
//! without them still compiles, and the window then explains that it has nothing to install.

use egui::{ColorImage, TextureHandle, TextureOptions};

pub const PAYLOAD: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/payload.tar"));
const HEADER: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/header.png"));
const LOGO: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/logo.png"));
const ICON: &[u8] = include_bytes!("../assets/icon.png");
pub const LICENSE: &str = include_str!("../assets/license_ru.txt");
pub const THIRD_PARTY: &str = include_str!(concat!(env!("OUT_DIR"), "/third_party.txt"));

pub struct Textures {
    pub header: Option<TextureHandle>,
    pub logo: Option<TextureHandle>,
}

impl Textures {
    pub fn load(ctx: &egui::Context) -> Self {
        let texture = |name: &str, bytes: &[u8]| {
            // Pixel art: nearest-neighbour keeps the pixels square when scaled.
            decode(bytes).map(|image| ctx.load_texture(name, image, TextureOptions::NEAREST))
        };
        Self { header: texture("header", HEADER), logo: texture("logo", LOGO) }
    }
}

pub fn window_icon() -> Option<egui::IconData> {
    let image = image::load_from_memory(ICON).ok()?.into_rgba8();
    Some(egui::IconData { width: image.width(), height: image.height(), rgba: image.into_raw() })
}

fn decode(bytes: &[u8]) -> Option<ColorImage> {
    if bytes.is_empty() {
        return None;
    }
    let image = image::load_from_memory(bytes).ok()?.into_rgba8();
    let size = [image.width() as usize, image.height() as usize];
    Some(ColorImage::from_rgba_unmultiplied(size, image.as_raw()))
}
