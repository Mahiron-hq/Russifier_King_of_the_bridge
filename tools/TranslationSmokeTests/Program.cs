using System;
using System.Collections.Generic;
using System.IO;
using BepInEx.Logging;
using KingOfTheBridge.Russian;

internal static class Program
{
    private static int Main(string[] args)
    {
        string translationPath = args.Length > 0
            ? Path.GetFullPath(args[0])
            : Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "translation.txt"));
        var logger = new ManualLogSource();
        TranslationCatalog.Load(translationPath, logger);

        var failures = new List<string>();
        ExpectKnown("START", "Играть", failures);
        ExpectKnown("FULLSCREEN: Вкл", "Полный экран: Вкл", failures);
        ExpectKnown("SPEED CHESS MODE: Выкл", "Таймер: Выкл", failures);
        ExpectKnown("SPEEDRUN MODE: Выкл", "Спидран: Выкл", failures);
        ExpectKnown("WIPE SAVE FILE", "Сбросить игру", failures);
        ExpectKnown("After 22 attempts.", "После 22 попытки.", failures);
        ExpectKnown(
            "It took you 22 hours, 3 minutes and 1 second.",
            "На это у вас ушло 22 часа, 3 минуты и 1 секунда.",
            failures);
        ExpectComposite(
            "WHITE PAWN WAS MOVED.",
            "БЕЛАЯ ПЕШКА БЫЛА ПЕРЕМЕЩЕНА.",
            failures);
        ExpectComposite(
            "LANDMINE + [ RULE VIOLATED ]",
            "ДАР ЗНАНИЯ + [ НАРУШЕНО ПРАВИЛО ]",
            failures);
        ExpectComposite(
            "BLACK QUEEN WAS MOVED BY THE WRONG COLOR.",
            "ЧЁРНАЯ КОРОЛЕВА СХОДИЛА ЗА ДРУГОЙ ЦВЕТ.",
            failures);
        ExpectComposite(
            "WHITE ROOK JUMPED WHEN ONLY HE CAN JUMP.",
            "БЕЛАЯ ЛАДЬЯ ПРЫГНУЛА, ХОТЯ ЭТО МОЖЕТ ТОЛЬКО КОНЬ.",
            failures);
        ExpectComposite(
            "WHITE ROOK STEPPED TOO CLOSE TO ONE ANOTHER.",
            "БЕЛАЯ ЛАДЬЯ ВСТАЛА НА МЕСТО ДРУГОЙ ФИГУРЫ.",
            failures);

        string alreadyRussian = "Настройки";
        if (TranslationCatalog.TryTranslateKnown(alreadyRussian, out string changed) || changed != alreadyRussian)
            failures.Add("Already translated text was changed");

        if (failures.Count == 0)
        {
            Console.WriteLine("Translation smoke tests passed (13 cases).");
            return 0;
        }

        foreach (string failure in failures)
            Console.Error.WriteLine(failure);
        return 1;
    }

    private static void ExpectKnown(string source, string expected, ICollection<string> failures)
    {
        if (!TranslationCatalog.TryTranslateKnown(source, out string actual) || actual != expected)
            failures.Add($"Translate '{source}': expected '{expected}', got '{actual}'");
    }

    private static void ExpectComposite(string source, string expected, ICollection<string> failures)
    {
        if (!RussianGrammar.TryTranslateComposite(source, out string actual) || actual != expected)
            failures.Add($"Composite '{source}': expected '{expected}', got '{actual}'");
    }
}
