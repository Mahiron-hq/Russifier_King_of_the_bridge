#![windows_subsystem = "windows"]

mod app;
mod assets;
mod theme;
mod worker;

fn main() -> eframe::Result {
    let version = patchset::display_version(env!("CARGO_PKG_VERSION"));
    let mut viewport = egui::ViewportBuilder::default()
        .with_title(format!("Русификатор King of the Bridge – {version}"))
        .with_inner_size(app::WINDOW_SIZE)
        .with_resizable(false)
        .with_maximize_button(false);
    if let Some(icon) = assets::window_icon() {
        viewport = viewport.with_icon(icon);
    }
    let options = eframe::NativeOptions { viewport, centered: true, ..Default::default() };
    eframe::run_native(
        "kotb-russian-installer",
        options,
        Box::new(move |cc| Ok(Box::new(app::App::new(&cc.egui_ctx, version)))),
    )
}
