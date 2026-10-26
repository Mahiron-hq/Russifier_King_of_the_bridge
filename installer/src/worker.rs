//! Runs the installation off the UI thread and reports back through a channel.

use std::error::Error;
use std::io;
use std::sync::Arc;
use std::sync::mpsc::{self, Receiver, TryRecvError};
use std::thread;

use patchset::{AlphaRemoval, GameDir, InstallError, Payload, PlayerSettings};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Task {
    Install,
    Uninstall,
}

pub enum Message {
    Progress { done: usize, total: usize, file: String },
    Finished(Result<Outcome, String>),
}

/// What the player should be told once the work is done.
pub struct Outcome {
    pub alpha: AlphaRemoval,
    /// Set when the game files are fine but the language setting could not be changed.
    pub settings_warning: Option<String>,
}

pub struct Worker {
    receiver: Receiver<Message>,
}

impl Worker {
    pub fn start(task: Task, game: GameDir, payload: Arc<Payload>, ctx: egui::Context) -> Self {
        let (sender, receiver) = mpsc::channel();
        thread::spawn(move || {
            let mut report = |progress: patchset::Progress<'_>| {
                let message =
                    Message::Progress { done: progress.done, total: progress.total, file: progress.file.to_string() };
                // The window may already be gone; then nobody is waiting for progress.
                let _ = sender.send(message);
                ctx.request_repaint();
            };
            let result = match task {
                Task::Install => patchset::install(&game, &payload, &mut report),
                Task::Uninstall => patchset::uninstall(&game, &payload.manifest, &mut report),
            };
            // The alpha goes only after the mod is in place, so a failed install still leaves a working translation.
            let finished = result.map_err(|e| describe(&e)).and_then(|()| {
                let settings_warning = update_settings(task, &payload).err();
                let alpha = patchset::remove_alpha(&game).map_err(|e| alpha_left(task, &e))?;
                Ok(Outcome { alpha, settings_warning })
            });
            let _ = sender.send(Message::Finished(finished));
            ctx.request_repaint();
        });
        Self { receiver }
    }

    /// Messages that arrived since the last call; `None` once the worker is gone without finishing.
    pub fn poll(&self) -> Option<Vec<Message>> {
        let mut messages = Vec::new();
        loop {
            match self.receiver.try_recv() {
                Ok(message) => messages.push(message),
                Err(TryRecvError::Empty) => return Some(messages),
                Err(TryRecvError::Disconnected) => return if messages.is_empty() { None } else { Some(messages) },
            }
        }
    }
}

fn update_settings(task: Task, payload: &Payload) -> Result<(), String> {
    let settings = PlayerSettings::locate().ok_or("не найдена папка AppData\\LocalLow")?;
    let language = &payload.manifest.settings;
    match task {
        Task::Install => settings.select_russian(language),
        Task::Uninstall => settings.reset_to_english(language),
    }
    .map_err(|e| e.to_string())
}

fn alpha_left(task: Task, error: &InstallError) -> String {
    let done = match task {
        Task::Install => "установлен",
        Task::Uninstall => "удалён",
    };
    format!(
        "Русификатор {done}, но альфа-версию убрать не удалось: {}\n\n\
         Удалите вручную файл BepInEx\\plugins\\RussianTranslationMod.dll из папки игры.",
        describe(error)
    )
}

fn describe(error: &InstallError) -> String {
    let denied = error
        .source()
        .and_then(|source| source.downcast_ref::<io::Error>())
        .is_some_and(|e| e.kind() == io::ErrorKind::PermissionDenied);
    if denied {
        format!("{error}\n\nНет прав на запись в папку игры. Запустите установщик от имени администратора.")
    } else {
        error.to_string()
    }
}
