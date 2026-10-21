<div align="center">

# Русификатор King of the Bridge

**Русский перевод игры King of the Bridge: тексты, шрифт и картинки книги правил, без правки файлов игры**

[![License](https://img.shields.io/badge/license-Apache%202.0-green?style=flat-square)](LICENSE)
[![Release](https://img.shields.io/github/v/release/Mahiron-hq/Russifier_King_of_the_bridge?include_prereleases&style=flat-square&label=release)](https://github.com/Mahiron-hq/Russifier_King_of_the_bridge/releases)
[![Status](https://img.shields.io/badge/status-alpha-orange?style=flat-square)](#статус)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Steam-0078D4?style=flat-square&logo=windows&logoColor=white)](#установка)
[![BepInEx](https://img.shields.io/badge/BepInEx-5.4.23.4-blue?style=flat-square)](https://github.com/BepInEx/BepInEx)

</div>

---

Русификатор для игры King of the Bridge от игрока **lion.burmistrov, он же Lev Burmistrov (Mahiron-hq)**.
Это плагин [BepInEx](https://github.com/BepInEx/BepInEx), который подменяет английские тексты и
картинки игры на лету. Файлы самой игры он не меняет, поэтому русификатор можно убрать, удалив
несколько файлов.

### Статус

Русификатор всё ещё на этапе разработки, но вы уже можете им пользоваться. Книга правил
переведена полностью, не переведено только её оглавление. Всё остальное уже закончено.

Разработка замедлена в связи с малым количеством свободного времени, которое отнимает учёба, но она
не стоит на месте.

### Установка

1. **Скачайте архив** на странице [релизов](https://github.com/Mahiron-hq/Russifier_King_of_the_bridge/releases).
   Берите именно первый в списке архив, не `Source code`.

2. **Закройте игру и распакуйте архив** в корневую папку с игрой. Обычный путь для Steam:

   ```
   C:\Program Files (x86)\Steam\steamapps\common\King of the Bridge
   ```

3. **Проверьте структуру.** В папке с игрой должны оказаться такие файлы и папки:

   ```plaintext
   King of the Bridge/
   ├── BepInEx/
   ├── King of the Bridge_BurstDebugInformation_DoNotShip/
   ├── King of the Bridge_Data/
   ├── MonoBleedingEdge/
   ├── doorstop_config.ini
   ├── King of the Bridge.exe
   ├── UnityCrashHandler64.exe
   ├── UnityPlayer.dll
   └── winhttp.dll
   ```

4. **Запустите игру.**

Подробная инструкция с картинками есть в
[руководстве Steam](https://steamcommunity.com/sharedfiles/filedetails/?id=3662724406&preview=true).

#### Удаление

Закройте игру и удалите из её папки `BepInEx`, `doorstop_config.ini` и `winhttp.dll`. Если вы
пользуетесь другими модами на BepInEx, удалите только `BepInEx/plugins/RussianTranslationMod.dll` и
файлы русификатора рядом с ним.

### Как это устроено

| Что | Где | Зачем |
|---|---|---|
| `src/RussianTranslationMod` | исходный код плагина | перехватывает тексты TextMeshPro и спрайты через Harmony |
| `data/translation.txt` | словарь `оригинал=перевод` | переводы строк, поддерживаются склонения вида `{seconds\|секунда\|секунды\|секунд}` |
| `data/image_mapping.txt` | соответствие спрайтов и файлов | какая картинка чем заменяется |
| `data/images/translated` | переведённые PNG | попадают в игру |
| `data/images/original`, `data/images/source` | оригиналы из игры и PSD-исходники | для правки переводов |
| `data/fonts` | шрифт с кириллицей | `alagard-unicode-tmp` загружается плагином, `BubbleSans-Regular.otf` лежит рядом для работы с PSD |
| `data/source-tables` | выгрузка таблиц локализации игры | исходные строки для перевода |
| `scripts/build.ps1` | сборка релиза | компилирует плагин и собирает архив |

### Сборка из исходников

Нужны Windows, Visual Studio 2022 (или Build Tools) с пакетом нацеливания .NET Framework 4.7.2 и
установленная игра. BepInEx скачивается сам и проверяется по контрольной сумме.

```powershell
.\scripts\build.ps1 -GameDir 'D:\SteamLibrary\steamapps\common\King of the Bridge'
```

Готовый архив появится в `release/`. Чтобы собирать из Visual Studio, откройте
`RussianTranslationMod.sln` и положите рядом с проектом файл `RussianTranslationMod.csproj.user` со
свойством `GameDir` (он не попадает в git):

```xml
<Project>
  <PropertyGroup>
    <GameDir>D:\SteamLibrary\steamapps\common\King of the Bridge</GameDir>
  </PropertyGroup>
</Project>
```

### Обратная связь и ошибки

Если у вас есть предложения по улучшению или вы обнаружили ошибки в переводе, напишите мне в
телеграм-чате: [t.me/lion_burmistrov/5](https://t.me/lion_burmistrov/5). Я с радостью прочитаю ваши
сообщения и внесу изменения.

### Лицензия

[Apache License 2.0](LICENSE). Copyright 2026 Lev Burmistrov (Mahiron-hq).

Лицензия относится к коду и материалам русификатора. Игра King of the Bridge, её оригинальные тексты
и графика принадлежат их правообладателям, шрифты распространяются на условиях их авторов.
