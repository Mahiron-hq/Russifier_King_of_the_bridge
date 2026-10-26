use std::path::PathBuf;
use std::process::Command;
use std::sync::Arc;

use egui::{Align, Frame, Layout, Margin, RichText, ScrollArea, TextEdit, Vec2, vec2};
use patchset::{APP_ID, AlphaRemoval, EXECUTABLE, GameDir, Payload, State};

use crate::assets::{self, Textures};
use crate::theme::{self, GREEN, MOSS, READING, RED};
use crate::worker::{Message, Outcome, Task, Worker};

pub const REPOSITORY: &str = "https://github.com/Mahiron-hq/Russifier_King_of_the_bridge";
pub const WINDOW_SIZE: [f32; 2] = [800.0, 600.0];
const HEADER_HEIGHT: f32 = 180.0;
const BAR_HEIGHT: f32 = 60.0;
const FRAME_MARGIN: i8 = 10;
const PAGE_MARGIN: i8 = 28;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Page {
    Start,
    License,
    Folder,
    Working,
    Done,
}

/// Result of checking the folder the player picked.
enum Folder {
    Missing(String),
    Running,
    Unsupported(String),
    /// `alpha` is set when the BepInEx plugin of the alpha versions is in the folder too.
    Ready {
        game: GameDir,
        state: State,
        alpha: bool,
    },
}

pub struct App {
    version: String,
    payload: Result<Arc<Payload>, String>,
    textures: Textures,
    page: Page,
    task: Task,
    accepted: bool,
    show_third_party: bool,
    path: String,
    folder: Folder,
    worker: Option<Worker>,
    progress: (usize, usize, String),
    result: Option<Result<Outcome, String>>,
    launch_game: bool,
}

impl App {
    pub fn new(ctx: &egui::Context, version: String) -> Self {
        theme::apply(ctx);
        let payload = load_payload(&version);
        let path = patchset::find_steam_install().map(|p| p.display().to_string()).unwrap_or_default();
        let mut app = Self {
            version,
            payload,
            textures: Textures::load(ctx),
            page: Page::Start,
            task: Task::Install,
            accepted: false,
            show_third_party: false,
            path,
            folder: Folder::Missing(String::new()),
            worker: None,
            progress: (0, 0, String::new()),
            result: None,
            launch_game: false,
        };
        app.check_folder();
        app
    }

    fn check_folder(&mut self) {
        self.folder = match (&self.payload, GameDir::open(PathBuf::from(self.path.trim().trim_matches('"')))) {
            (Err(e), _) => Folder::Missing(e.clone()),
            (_, Err(e)) if self.path.trim().is_empty() => Folder::Missing(format!("укажите папку игры ({e})")),
            (_, Err(e)) => Folder::Missing(e.to_string()),
            (Ok(payload), Ok(game)) => match patchset::inspect(&game, &payload.manifest) {
                Ok(_) if game_running() => Folder::Running,
                Ok(state) => Folder::Ready { alpha: patchset::alpha_installed(&game), game, state },
                Err(e) => Folder::Unsupported(e.to_string()),
            },
        };
    }

    fn can_continue(&self) -> bool {
        match self.page {
            Page::Start => self.payload.is_ok(),
            Page::License => self.accepted,
            Page::Folder => match (&self.folder, self.task) {
                (Folder::Ready { .. }, Task::Install) => true,
                (Folder::Ready { state, alpha, .. }, Task::Uninstall) => *state != State::NotInstalled || *alpha,
                _ => false,
            },
            Page::Working | Page::Done => false,
        }
    }

    fn next(&mut self, ctx: &egui::Context) {
        self.page = match (self.page, self.task) {
            (Page::Start, Task::Install) => Page::License,
            (Page::Start, Task::Uninstall) | (Page::License, _) => {
                self.check_folder();
                Page::Folder
            }
            (Page::Folder, task) => {
                self.check_folder();
                let (Folder::Ready { game, .. }, Ok(payload)) = (&self.folder, &self.payload) else {
                    return;
                };
                self.worker = Some(Worker::start(task, game.clone(), Arc::clone(payload), ctx.clone()));
                Page::Working
            }
            (page, _) => page,
        };
    }

    fn back(&mut self) {
        self.page = match (self.page, self.task) {
            (Page::License, _) | (Page::Folder, Task::Uninstall) => Page::Start,
            (Page::Folder, Task::Install) => Page::License,
            (page, _) => page,
        };
    }

    fn poll_worker(&mut self) {
        let Some(worker) = &self.worker else { return };
        let Some(messages) = worker.poll() else {
            self.result = Some(Err("установка прервалась без ответа".into()));
            self.worker = None;
            self.page = Page::Done;
            return;
        };
        for message in messages {
            match message {
                Message::Progress { done, total, file } => self.progress = (done, total, file),
                Message::Finished(result) => {
                    self.result = Some(result);
                    self.worker = None;
                    self.page = Page::Done;
                }
            }
        }
    }

    fn finish(&self, ctx: &egui::Context) {
        if self.launch_game && matches!(self.result, Some(Ok(_))) && self.task == Task::Install {
            // Through Steam, so the game starts the same way as from the library.
            let _ = Command::new("explorer").arg(format!("steam://rungameid/{APP_ID}")).spawn();
        }
        ctx.send_viewport_cmd(egui::ViewportCommand::Close);
    }
}

impl eframe::App for App {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        let ctx = ui.ctx().clone();
        self.poll_worker();
        if ctx.input(|i| i.viewport().close_requested()) && self.page == Page::Working {
            ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
        }

        egui::Panel::top("header").exact_size(HEADER_HEIGHT).frame(Frame::NONE).show(ui, |ui| {
            if let Some(header) = &self.textures.header {
                ui.add(egui::Image::new(header).fit_to_exact_size(vec2(ui.available_width(), HEADER_HEIGHT)));
            }
        });
        egui::Panel::bottom("buttons")
            .exact_size(BAR_HEIGHT)
            .frame(Frame::NONE.fill(theme::DARK).inner_margin(Margin::symmetric(PAGE_MARGIN, 14)))
            .show(ui, |ui| self.buttons(ui, &ctx));
        egui::CentralPanel::no_frame()
            .frame(Frame::NONE.fill(theme::DARK).inner_margin(Margin {
                left: PAGE_MARGIN,
                right: PAGE_MARGIN,
                top: 8,
                bottom: 6,
            }))
            .show(ui, |ui| match self.page {
                Page::Start => self.start_page(ui),
                Page::License => self.license_page(ui),
                Page::Folder => self.folder_page(ui),
                Page::Working => self.working_page(ui),
                Page::Done => self.done_page(ui),
            });
    }
}

// Pages
impl App {
    fn start_page(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            if let Some(logo) = &self.textures.logo {
                ui.add(egui::Image::new(logo).fit_to_exact_size(logo.size_vec2()));
            }
        });
        ui.add_space(4.0);
        ui.label(
            "Мастер установит русский перевод игры: тексты, диалоги тролля, книгу правил, \
             оглавление, достижения и шрифт с кириллицей. Русский язык появится в настройках игры \
             рядом с английским и нидерландским.",
        );
        ui.add_space(6.0);
        if let Err(error) = &self.payload {
            ui.colored_label(RED, error);
            return;
        }

        let installed = match &self.folder {
            Folder::Ready { state: State::Installed { version, current }, .. } => Some(match (version, current) {
                (_, true) => format!("Русификатор {} уже установлен.", self.version),
                (Some(version), false) => format!("Установлен русификатор {version}."),
                (None, false) => "Установлена предыдущая версия русификатора.".to_owned(),
            }),
            Folder::Ready { state: State::NotInstalled, .. } => Some(String::new()),
            _ => None,
        };
        if let Some(text) = installed.filter(|t| !t.is_empty()) {
            ui.colored_label(GREEN, text);
        }
        if matches!(self.folder, Folder::Ready { alpha: true, .. }) {
            ui.colored_label(GREEN, "Найдена альфа-версия русификатора, установщик её уберёт.");
        }

        ui.add_space(4.0);
        choice(ui, &mut self.task, Task::Install, "Установить русификатор", &format!("версия {}", self.version));
        choice(ui, &mut self.task, Task::Uninstall, "Удалить русификатор", "вернуть игре оригинальные файлы");
    }

    fn license_page(&mut self, ui: &mut egui::Ui) {
        ui.heading("Лицензионное соглашение");
        ui.label("Прочитайте условия использования русификатора.");
        // Laid out from the bottom, so the checkbox always keeps its place and the text takes what is left.
        ui.with_layout(Layout::bottom_up(Align::Min), |ui| {
            ui.checkbox(&mut self.accepted, "Я принимаю условия лицензионного соглашения");
            let height = ui.available_height() - 2.0 * f32::from(FRAME_MARGIN) - ui.spacing().item_spacing.y - 2.0;
            ui.with_layout(Layout::top_down(Align::Min), |ui| {
                Frame::NONE.fill(ui.visuals().extreme_bg_color).stroke((1.0, MOSS)).inner_margin(FRAME_MARGIN).show(
                    ui,
                    |ui| {
                        ScrollArea::vertical().max_height(height.max(40.0)).auto_shrink([false, false]).show(
                            ui,
                            |ui| {
                                let text = |s: &str| {
                                    RichText::new(s).family(egui::FontFamily::Name(READING.into())).size(14.0)
                                };
                                ui.label(text(&preamble(&self.version)).strong());
                                ui.add_space(8.0);
                                ui.label(text(assets::LICENSE));
                                if !assets::THIRD_PARTY.is_empty() {
                                    ui.add_space(8.0);
                                    ui.toggle_value(&mut self.show_third_party, "Лицензии сторонних компонентов");
                                    if self.show_third_party {
                                        ui.label(text(assets::THIRD_PARTY));
                                    }
                                }
                            },
                        );
                    },
                );
            });
        });
    }

    fn folder_page(&mut self, ui: &mut egui::Ui) {
        ui.heading("Папка игры");
        ui.label(format!(
            "Установщик ищет игру в библиотеках Steam. Если игра установлена в другом месте, укажите папку, \
             в которой лежит {EXECUTABLE}."
        ));
        ui.add_space(4.0);
        let label = ui.label("Папка:");
        // The whole row, so the usual Steam path fits without scrolling.
        let field = TextEdit::singleline(&mut self.path).desired_width(f32::INFINITY);
        if ui.add(field).labelled_by(label.id).changed() {
            self.check_folder();
        }
        ui.with_layout(Layout::right_to_left(Align::Min), |ui| {
            if ui.add_sized([100.0, 28.0], egui::Button::new("Обзор…")).clicked()
                && let Some(folder) = rfd::FileDialog::new().set_title("Папка King of the Bridge").pick_folder()
            {
                self.path = folder.display().to_string();
                self.check_folder();
            }
        });
        let (color, text) = match (&self.folder, self.task) {
            (Folder::Missing(e), _) => (RED, e.clone()),
            (Folder::Running, _) => (RED, "Игра запущена. Закройте её и нажмите «Обновить».".to_owned()),
            (Folder::Unsupported(e), _) => (RED, e.clone()),
            (Folder::Ready { state: State::NotInstalled, alpha: false, .. }, Task::Uninstall) => {
                (RED, "Русификатор в этой папке не установлен.".to_owned())
            }
            (Folder::Ready { state, alpha, .. }, task) => {
                let found = match (state, task) {
                    (State::NotInstalled, Task::Install) => "Игра найдена, версия поддерживается.",
                    (State::Installed { .. }, Task::Install) => {
                        "Игра найдена. Установленный русификатор будет обновлён."
                    }
                    (State::NotInstalled, Task::Uninstall) => "Игра найдена.",
                    (State::Installed { .. }, Task::Uninstall) => "Игра найдена, русификатор можно удалить.",
                };
                let alpha = if *alpha {
                    " Альфа-версия русификатора на BepInEx будет удалена."
                } else {
                    ""
                };
                (GREEN, format!("{found}{alpha}"))
            }
        };
        ui.colored_label(color, text);
        if matches!(self.folder, Folder::Running | Folder::Unsupported(_)) && ui.button("Обновить").clicked() {
            self.check_folder();
        }
    }

    fn working_page(&mut self, ui: &mut egui::Ui) {
        ui.heading(match self.task {
            Task::Install => "Установка…",
            Task::Uninstall => "Удаление…",
        });
        ui.label("Не закрывайте окно, пока работа не закончится.");
        ui.add_space(12.0);
        let (done, total, file) = &self.progress;
        let fraction = if *total == 0 { 0.0 } else { *done as f32 / *total as f32 };
        ui.add(egui::ProgressBar::new(fraction).desired_height(22.0).fill(GREEN).corner_radius(0));
        ui.label(RichText::new(file).small().color(GREEN));
    }

    fn done_page(&mut self, ui: &mut egui::Ui) {
        match (&self.result, self.task) {
            (Some(Ok(Outcome { alpha, settings_warning: warning })), task) => {
                ui.heading(match task {
                    Task::Install => "Готово!",
                    Task::Uninstall => "Русификатор удалён",
                });
                ui.label(match task {
                    Task::Install => "Русификатор установлен. Приятной игры!",
                    Task::Uninstall => "Оригинальные файлы игры восстановлены.",
                });
                match (warning, task) {
                    (None, Task::Install) => ui.label("Русский язык уже выбран в настройках игры."),
                    (None, Task::Uninstall) => ui.label("Язык игры переключён на английский."),
                    (Some(warning), _) => ui.colored_label(
                        RED,
                        format!(
                            "Не удалось изменить язык в настройках игры: {warning}\n\
                             Выберите язык вручную: Настройки -> Текст -> Язык."
                        ),
                    ),
                };
                match alpha {
                    AlphaRemoval::NotFound => {}
                    AlphaRemoval::Removed => {
                        ui.label("Альфа-версия русификатора и BepInEx удалены.");
                    }
                    AlphaRemoval::BepInExKept => {
                        ui.label("Альфа-версия русификатора удалена. BepInEx оставлен: в нём есть другие моды.");
                    }
                }
                if task == Task::Install {
                    ui.add_space(8.0);
                    ui.checkbox(&mut self.launch_game, "Запустить игру");
                }
            }
            (Some(Err(error)), _) => {
                ui.heading("Не получилось");
                ui.colored_label(RED, error);
            }
            (None, _) => {}
        }
    }

    fn buttons(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        ui.horizontal(|ui| {
            ui.label(RichText::new(&self.version).color(GREEN));
            ui.label(RichText::new("·").color(MOSS));
            ui.hyperlink_to("GitHub", REPOSITORY);
            ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                let size = Vec2::new(110.0, 32.0);
                match self.page {
                    Page::Working => {}
                    Page::Done => {
                        if ui.add_sized(size, egui::Button::new("Готово")).clicked() {
                            self.finish(ctx);
                        }
                    }
                    page => {
                        if ui.add_sized(size, egui::Button::new("Отмена")).clicked() {
                            ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                        }
                        let label = match (page, self.task) {
                            (Page::Folder, Task::Install) => "Установить",
                            (Page::Folder, Task::Uninstall) => "Удалить",
                            _ => "Далее",
                        };
                        if ui.add_enabled(self.can_continue(), egui::Button::new(label).min_size(size)).clicked() {
                            self.next(ctx);
                        }
                        if page != Page::Start && ui.add_sized(size, egui::Button::new("Назад")).clicked() {
                            self.back();
                        }
                    }
                }
            });
        });
    }
}

fn choice(ui: &mut egui::Ui, current: &mut Task, value: Task, title: &str, note: &str) {
    let selected = *current == value;
    let text = RichText::new(if selected { format!("> {title}") } else { format!("  {title}") });
    let response = ui.add(egui::Button::selectable(selected, text).min_size(vec2(ui.available_width(), 34.0)));
    if response.clicked() {
        *current = value;
    }
    ui.label(RichText::new(format!("      {note}")).small().color(GREEN));
}

fn preamble(version: &str) -> String {
    format!(
        "Русификатор King of the Bridge, версия {version}\n\
         © 2026 Лев Бурмистров (Mahiron-hq)\n\n\
         Перевод, переведённые изображения и программный код русификатора распространяются на условиях \
         лицензии Creative Commons «С указанием авторства – Некоммерческая – С сохранением условий» 4.0 \
         Международная (CC BY-NC-SA 4.0). Её полный текст приведён ниже и опубликован по адресу \
         creativecommons.org/licenses/by-nc-sa/4.0/legalcode.ru.\n\n\
         Коротко: русификатор можно бесплатно скачивать, устанавливать и распространять с указанием автора. \
         Изменённые версии можно распространять только бесплатно, с указанием автора и на условиях этой же \
         лицензии. Продавать русификатор или его части нельзя. Это краткое изложение не заменяет текст лицензии.\n\n\
         Игра King of the Bridge, её оригинальные тексты, изображения и другие материалы принадлежат \
         их правообладателям и под эту лицензию не подпадают. Русификатор неофициальный и не связан \
         с разработчиком игры.\n\n\
         Русификатор изменяет файлы игры. Перед изменением оригиналы сохраняются в папку RussianMod_backup \
         внутри папки игры, а удаление через этот установщик возвращает их на место. Русификатор \
         предоставляется «как есть», без каких-либо гарантий (раздел 5 лицензии).\n\n\
         Шрифты и библиотеки, на которых построен русификатор, распространяются на условиях их авторов; \
         их лицензии приведены в конце."
    )
}

fn load_payload(version: &str) -> Result<Arc<Payload>, String> {
    if assets::PAYLOAD.is_empty() {
        return Err("Эта сборка установщика не содержит файлов русификатора.".into());
    }
    let payload = Payload::read_tar(assets::PAYLOAD).map_err(|e| e.to_string())?;
    if payload.manifest.version != version {
        return Err(format!(
            "Данные русификатора ({}) не совпадают с версией установщика ({version}).",
            payload.manifest.version
        ));
    }
    Ok(Arc::new(payload))
}

fn game_running() -> bool {
    let mut system = sysinfo::System::new();
    system.refresh_processes(sysinfo::ProcessesToUpdate::All, true);
    system.processes().values().any(|process| process.name().eq_ignore_ascii_case(EXECUTABLE))
}

#[cfg(test)]
mod tests {
    use std::path::PathBuf;

    use egui_kittest::Harness;
    use egui_kittest::kittest::Queryable;

    use super::*;

    const SCALES: [f32; 3] = [1.0, 1.25, 1.5];
    const STEAM_PATH: &str = r"C:\Program Files (x86)\Steam\steamapps\common\King of the Bridge";

    fn harness(page: Page, task: Task, pixels_per_point: f32) -> Harness<'static, App> {
        let mut harness = Harness::builder()
            .with_size(WINDOW_SIZE)
            .with_pixels_per_point(pixels_per_point)
            .build_eframe(|cc| App::new(&cc.egui_ctx, patchset::display_version(env!("CARGO_PKG_VERSION"))));
        let app = harness.state_mut();
        app.page = page;
        app.task = task;
        app.result = Some(Ok(Outcome { alpha: AlphaRemoval::NotFound, settings_warning: None }));
        harness.run_ok();
        harness
    }

    /// Renders the page to `target/ui-pages` so the window can be looked at without starting it.
    fn save(harness: &mut Harness<'_, App>, name: &str) {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("target").join("ui-pages");
        std::fs::create_dir_all(&dir).expect("target directory is writable");
        let image = harness.render().expect("the test renderer draws the window");
        image.save(dir.join(format!("{name}.png"))).expect("snapshot is writable");
    }

    fn content_bottom() -> f32 {
        WINDOW_SIZE[1] - BAR_HEIGHT
    }

    /// An empty folder that passes for the game.
    fn fake_game() -> GameDir {
        let game = std::env::temp_dir().join("kotb-installer-test-game");
        std::fs::create_dir_all(game.join(patchset::DATA_DIR)).expect("temp directory is writable");
        std::fs::write(game.join(EXECUTABLE), b"").expect("temp directory is writable");
        GameDir::open(&game).expect("the folder was just laid out as a game")
    }

    fn assert_above_bar(harness: &Harness<'_, App>, name: &str, last: &str) {
        let rect = harness.get_by_label_contains(last).rect();
        assert!(
            rect.bottom() <= content_bottom(),
            "{name}: \"{last}\" ends at {} but the button bar starts at {}",
            rect.bottom(),
            content_bottom()
        );
    }

    #[test]
    fn every_page_fits_above_the_button_bar() {
        let pages = [
            (Page::Start, Task::Install, "start", "Удалить русификатор"),
            (Page::License, Task::Install, "license", "Я принимаю условия"),
            (Page::Folder, Task::Install, "folder", "Обзор"),
            (Page::Working, Task::Install, "working", "Не закрывайте окно"),
            (Page::Done, Task::Install, "done", "Запустить игру"),
            (Page::Done, Task::Uninstall, "done-uninstall", "Оригинальные файлы игры восстановлены"),
        ];
        for scale in SCALES {
            for (page, task, name, last) in pages {
                let mut harness = harness(page, task, scale);
                save(&mut harness, &format!("{name}@{scale}"));
                assert_above_bar(&harness, &format!("{name} at {scale}x"), last);
            }
        }
    }

    #[test]
    fn alpha_messages_fit_above_the_button_bar() {
        let installed = State::Installed { version: None, current: false };
        for scale in SCALES {
            let mut folder = harness(Page::Folder, Task::Install, scale);
            folder.state_mut().folder = Folder::Ready { game: fake_game(), state: installed.clone(), alpha: true };
            folder.run_ok();
            save(&mut folder, &format!("folder-alpha@{scale}"));
            assert_above_bar(&folder, &format!("folder with the alpha at {scale}x"), "BepInEx будет удалена");

            let mut done = harness(Page::Done, Task::Install, scale);
            done.state_mut().result = Some(Ok(Outcome {
                alpha: AlphaRemoval::BepInExKept,
                settings_warning: Some("нет доступа".into()),
            }));
            done.run_ok();
            save(&mut done, &format!("done-alpha@{scale}"));
            assert_above_bar(&done, &format!("done with the alpha at {scale}x"), "Запустить игру");
        }
    }

    #[test]
    fn steam_path_fits_the_field() {
        for scale in SCALES {
            let mut window = harness(Page::Folder, Task::Install, scale);
            window.state_mut().path = STEAM_PATH.to_owned();
            window.run_ok();
            let field = window.get_by_label("Папка:").rect();
            let font = egui::TextStyle::Body.resolve(&window.ctx.global_style());
            let text = window.ctx.fonts_mut(|f| f.layout_no_wrap(STEAM_PATH.to_owned(), font, GREEN).size().x);
            assert!(text + 8.0 <= field.width(), "at {scale}x the path takes {text} of {}", field.width());
        }
    }

    /// Redraws `docs/screenshots` as a player sees the window on a first install.
    /// Run with `cargo test -p installer -- --ignored readme_screenshots`.
    #[test]
    #[ignore = "writes into docs/"]
    fn readme_screenshots() {
        let game = fake_game();
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("docs").join("screenshots");
        std::fs::create_dir_all(&dir).expect("docs directory is writable");
        let pages =
            [(Page::Start, "start"), (Page::License, "license"), (Page::Folder, "folder"), (Page::Done, "done")];
        for (page, name) in pages {
            let mut harness = harness(page, Task::Install, 1.0);
            let app = harness.state_mut();
            app.path = STEAM_PATH.to_owned();
            app.folder = Folder::Ready { game: game.clone(), state: State::NotInstalled, alpha: false };
            app.accepted = page == Page::License;
            harness.run_ok();
            let image = harness.render().expect("the test renderer draws the window");
            image.save(dir.join(format!("installer-{name}.png"))).expect("screenshot is writable");
        }
    }
}
