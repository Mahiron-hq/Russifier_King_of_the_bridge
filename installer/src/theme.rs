//! Colours and fonts taken from the game: its four-colour palette and the Alagard pixel font.

use std::sync::Arc;

use egui::{Color32, CornerRadius, FontData, FontDefinitions, FontFamily, FontId, Stroke, TextStyle, vec2};

pub const DARK: Color32 = Color32::from_rgb(36, 40, 40);
pub const MOSS: Color32 = Color32::from_rgb(58, 80, 67);
pub const GREEN: Color32 = Color32::from_rgb(127, 152, 96);
pub const CREAM: Color32 = Color32::from_rgb(248, 238, 191);
/// Not in the game's palette; a muted red that still sits well next to it, for errors only.
pub const RED: Color32 = Color32::from_rgb(222, 120, 96);

const PIXEL_FONT: &str = "alagard";
/// Family for long legal text, where the pixel font would be tiring to read.
pub const READING: &str = "reading";

pub fn apply(ctx: &egui::Context) {
    let mut fonts = FontDefinitions::default();
    fonts.font_data.insert(
        PIXEL_FONT.to_owned(),
        Arc::new(FontData::from_static(include_bytes!("../assets/alagard-cyrillic.ttf"))),
    );
    let defaults = fonts.families.get(&FontFamily::Proportional).cloned().unwrap_or_default();
    fonts.families.insert(FontFamily::Name(READING.into()), defaults.clone());
    let mut pixel_first = vec![PIXEL_FONT.to_owned()];
    pixel_first.extend(defaults);
    fonts.families.insert(FontFamily::Proportional, pixel_first);
    ctx.set_fonts(fonts);

    ctx.all_styles_mut(|style| {
        // The pixel font is drawn on a 16 px grid, so sizes stay at multiples of 16 to keep it sharp.
        style.text_styles = [
            (TextStyle::Heading, FontId::proportional(32.0)),
            (TextStyle::Body, FontId::proportional(16.0)),
            (TextStyle::Button, FontId::proportional(16.0)),
            (TextStyle::Monospace, FontId::monospace(13.0)),
            (TextStyle::Small, FontId::new(13.0, FontFamily::Name(READING.into()))),
        ]
        .into();
        style.spacing.item_spacing = vec2(8.0, 8.0);
        style.spacing.button_padding = vec2(14.0, 6.0);
        style.spacing.interact_size.y = 28.0;

        let visuals = &mut style.visuals;
        visuals.dark_mode = true;
        visuals.override_text_color = Some(CREAM);
        visuals.panel_fill = DARK;
        visuals.window_fill = DARK;
        visuals.extreme_bg_color = Color32::from_rgb(28, 31, 31);
        visuals.faint_bg_color = MOSS;
        visuals.hyperlink_color = GREEN;
        visuals.selection.bg_fill = MOSS;
        visuals.selection.stroke = Stroke::new(1.0, CREAM);

        let widgets = &mut visuals.widgets;
        for (state, fill, border) in [
            (&mut widgets.inactive, MOSS, GREEN),
            (&mut widgets.hovered, Color32::from_rgb(78, 104, 82), CREAM),
            (&mut widgets.active, GREEN, CREAM),
            (&mut widgets.open, MOSS, CREAM),
        ] {
            state.bg_fill = fill;
            state.weak_bg_fill = fill;
            state.bg_stroke = Stroke::new(2.0, border);
            state.fg_stroke = Stroke::new(1.5, CREAM);
            state.corner_radius = CornerRadius::ZERO;
            state.expansion = 0.0;
        }
        widgets.noninteractive.bg_stroke = Stroke::new(1.0, MOSS);
        widgets.noninteractive.fg_stroke = Stroke::new(1.0, CREAM);
        widgets.noninteractive.corner_radius = CornerRadius::ZERO;
    });
}
