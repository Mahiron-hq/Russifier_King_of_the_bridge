[![License](https://img.shields.io/badge/license-Apache%202.0-green?style=flat-square)](LICENSE)

# Русификатор King of the Bridge

Полный русский перевод King of the Bridge. Проект переводит интерфейс, диалоги, правила, концовки, достижения Steam и текст, нарисованный внутри страниц книги и кнопок оглавления.

Первоначальный русификатор создан **Lev Burmistrov / Mahiron-hq / lion.burmistrov**. Исходный перевод и подготовленные автором графические материалы сохранены и доработаны; техническая интеграция, покрытие графики, инструменты сборки и часть формулировок существенно переработаны. История Git сохранена для прозрачного авторства изменений.

Проверенная версия игры: `v1.024`, Unity `2022.3`, Windows x64. Загрузчик: BepInEx 5.

## Что переведено

- Все 327 строк из семи штатных Unity String Tables игры.
- Динамические строки с числами, временем и параметрами Smart String.
- Составные обвинения с учётом цвета, типа и рода шахматной фигуры.
- Названия и описания достижений, получаемые из Steam API.
- 42 локализованных страницы книги: правила, tutorial, оглавление и секретные страницы.
- 68 зеркальных кнопок оглавления, сгенерированных из оригинальных рамок.

Всего релиз содержит 396 словарных записей и 110 заменяемых PNG.

## Установка

Перед установкой закройте игру.

### Обновление с версии 0.x

Старая версия использовала DLL `RussianTranslationMod.dll` и размещала данные непосредственно в `BepInEx/plugins`. Перед установкой 1.0.0 удалите старые файлы русификатора:

```text
BepInEx/plugins/RussianTranslationMod.dll
BepInEx/plugins/translation.txt
BepInEx/plugins/image_mapping.txt
BepInEx/plugins/image/
```

Не удаляйте другие плагины. Новая версия целиком находится в отдельной папке `BepInEx/plugins/KingOfTheBridge.Russian` и сохраняет прежний GUID конфигурации `ru.translation.kingofthebridge`.

### Полный архив

Архив `KingOfTheBridge_Russian_Full.zip` уже содержит BepInEx 5 x64.

1. Откройте папку игры в Steam: «Управление» -> «Просмотреть локальные файлы».
2. Распакуйте содержимое архива в корень `King of the Bridge` с объединением папок.
3. Запустите игру.

После первого запуска в `BepInEx/LogOutput.log` должна появиться строка:

```text
King of the Bridge Russian Translation 1.0.0 loaded
```

### Только плагин

`KingOfTheBridge_Russian_Plugin.zip` предназначен для установки, где BepInEx 5 x64 уже настроен. Распакуйте архив в корень игры. Плагин окажется в:

```text
BepInEx/plugins/KingOfTheBridge.Russian/
```

Официальные выпуски BepInEx: <https://github.com/BepInEx/BepInEx/releases>

## Удаление

Удалите папку `BepInEx/plugins/KingOfTheBridge.Russian`. Сам BepInEx можно оставить для других модов.

## Диагностика

По умолчанию неизвестные игровые строки записываются в:

```text
BepInEx/plugins/KingOfTheBridge.Russian/untranslated.txt
```

Логирование можно отключить в `BepInEx/config/ru.translation.kingofthebridge.cfg`:

```ini
[Diagnostics]
LogUntranslated = false
```

Пока мод активен, внутренняя локаль игры фиксируется на English: русский словарь накладывается поверх полной английской таблицы. Пункт выбора языка поэтому отображается как «Русский» и не переключает игру на Dutch.

## Сборка

Требования:

- .NET SDK 9 или новее;
- установленная King of the Bridge;
- BepInEx 5 x64 в папке игры.

Сборка и создание архива плагина:

```powershell
.\build.ps1 -GamePath "D:\steam\steamapps\common\King of the Bridge" -Configuration Release -Package
```

Вместо параметра можно задать переменную `KOTB_GAME_PATH`. Жёстко заданных Steam-путей в проекте нет.

Чтобы одновременно создать полный архив, передайте официальный zip BepInEx:

```powershell
.\build.ps1 `
  -GamePath "D:\steam\steamapps\common\King of the Bridge" `
  -Configuration Release `
  -Package `
  -BepInExArchive ".\BepInEx_win_x64_5.4.23.5.zip"
```

Результаты создаются в `dist/`.

Оба архива также содержат README, историю изменений, основную лицензию и уведомления о сторонних материалах. Архив `Full` создаётся из переданного официального архива BepInEx без изменения его бинарных файлов.

## Проверки

Проверка словаря, шаблонов, рода и множественного числа:

```powershell
dotnet run --project tools\TranslationSmokeTests\TranslationSmokeTests.csproj -- translation.txt
```

Проверка структуры релизных данных:

```powershell
python tools\validate_release.py
```

Полный аудит String Tables и игровых ассетов требует пакетов из `requirements-dev.txt`:

```powershell
python -m pip install -r requirements-dev.txt
python tools\audit_translation.py --game "D:\steam\steamapps\common\King of the Bridge"
python tools\audit_game_assets.py --game "D:\steam\steamapps\common\King of the Bridge"
```

Повторная генерация кнопок оглавления:

```powershell
python tools\generate_link_sprites.py
```

Тексты кнопок находятся в `assets/link_labels.json`, оригинальные рамки и BubbleSans - в `assets/source/`.

Повторная генерация исправленных надписей внутри страниц правил:

```powershell
python tools\generate_rule_page_text.py
```

Тексты, допустимые области и параметры отдельных страниц находятся в `assets/rule_page_text.json`. Генератор очищает только заданные текстовые области и сохраняет заголовки, рисунки, прозрачность и исходный размер 320 x 320.

## Архитектура

- `LocalizedString.GetLocalizedString()` переводится до запуска анимации диалогов, поэтому длина печатаемого текста корректна без патча `maxVisibleCharacters`.
- `LocalizeStringEvent.UpdateString()` обрабатывает штатные компоненты Unity Localization и Smart Strings.
- Узкий TMP setter применяется только к известным составным шаблонам; неизвестный текст других модов не изменяется и не логируется.
- Шрифт игры сохраняется. Кириллический TMP asset подключается как fallback, без принудительного autosize, переноса или изменения alignment.
- Новые TMP-объекты обрабатываются через `TextMeshPro.OnEnable` и `TextMeshProUGUI.OnEnable`.
- Спрайты заменяются через setter-патчи. Созданные Sprite наследуют rect, pivot, pixels per unit и border оригинала.
- Полный обход объектов выполняется один раз после загрузки сцены; периодических сканирований нет.

## Известные ограничения

- Автоматически сгенерированные подписи оглавления проверены на контрольном листе; основные исправленные развороты дополнительно проверены непосредственно в раскрытой книге при 1920 x 1080.
- Страницы `page31` и `page_contents_1` используют оригинальную графику: первая содержит только формулу/рисунок, вторая пустая.
- Все строки проверены статически и основные экраны проверены запуском, но полный ручной проход всех секретов и концовок не выполнялся.
- Юмор, намеренная двусмысленность правил и отдельные формулировки достижений желательно дополнительно вычитать носителю русского языка вместе с игровым контекстом.

## Авторство

Исходный перевод и графика: **Lev Burmistrov / Mahiron-hq / lion.burmistrov**. Техническая переработка сохраняет первоначальную работу и историю репозитория.

Обратная связь: <https://t.me/lion_burmistrov/5>

## Лицензии

Исходный код, перевод и инструменты проекта распространяются по Apache License 2.0. Полный текст находится в [LICENSE](LICENSE), сведения об авторстве - в [NOTICE](NOTICE).

Шрифты, BepInEx и производные материалы King of the Bridge имеют отдельные условия. Подробности и ссылки на соответствующие лицензии приведены в [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Проект не является официальной локализацией и не связан с создателем игры.
