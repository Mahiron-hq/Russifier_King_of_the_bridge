using BepInEx;
using HarmonyLib;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using System.Linq;

[BepInPlugin("ru.translation.kingofthebridge", "Russian Translation", "2.0.0")]
public class TranslationMod : BaseUnityPlugin
{
    private static TMP_FontAsset russianFont;
    private static TranslationMod instance;
    private static HashSet<string> untranslatedStrings = new HashSet<string>();
    private static string untranslatedFilePath;

    private void Awake()
    {
        instance = this;
        untranslatedFilePath = Path.Combine(Paths.PluginPath, "untranslated.txt");

        Harmony harmony = new Harmony("ru.translation.kingofthebridge");
        harmony.PatchAll();
        Logger.LogInfo("Русификатор загружен v2.0.0 FINAL");

        Dictionary.LoadFromFile(Path.Combine(Paths.PluginPath, "translation.txt"), Logger);

        string assetBundlePath = Path.Combine(Paths.PluginPath, "alagard-unicode-TMP");
        AssetBundle bundle = AssetBundle.LoadFromFile(assetBundlePath);

        if (bundle != null)
        {
            TMP_FontAsset fontAsset = bundle.LoadAsset<TMP_FontAsset>("alagard-unicode-TMP");
            if (fontAsset != null)
            {
                russianFont = fontAsset;
                Logger.LogInfo("TMP шрифт загружен");
                ApplyFontToAllTMP();
                SceneManager.sceneLoaded += OnSceneLoaded;
            }
            else
            {
                Logger.LogError("TMP_FontAsset не найден");
            }
        }
        else
        {
            Logger.LogError("AssetBundle не загружен");
        }

        StartCoroutine(MonitorNewTextObjects());
        StartCoroutine(SaveUntranslatedPeriodically());
        StartCoroutine(TMPMaxVisibleCharactersPatch.CleanupOldEntries());
    }

    private void OnSceneLoaded(Scene scene, LoadSceneMode mode)
    {
        ApplyFontToAllTMP();
    }

    private void ApplyFontToAllTMP()
    {
        if (russianFont == null) return;

        TMP_Text[] allTexts = Resources.FindObjectsOfTypeAll<TMP_Text>();
        foreach (TMP_Text t in allTexts)
        {
            if (t != null && t.gameObject.scene.IsValid())
            {
                if (t.font != russianFont)
                {
                    t.font = russianFont;
                }
                EnableAutoSize(t);
            }
        }
    }

    private IEnumerator MonitorNewTextObjects()
    {
        yield return new WaitForSeconds(5f);

        while (true)
        {
            yield return new WaitForSeconds(2f);
            if (russianFont != null)
            {
                TMP_Text[] allTexts = Resources.FindObjectsOfTypeAll<TMP_Text>();
                foreach (TMP_Text t in allTexts)
                {
                    if (t != null && t.gameObject.scene.IsValid())
                    {
                        if (t.font != russianFont)
                        {
                            t.font = russianFont;
                        }
                        EnableAutoSize(t);
                    }
                }
            }
        }
    }

    private void EnableAutoSize(TMP_Text text)
    {
        if (text.enableAutoSizing) return;
        float currentSize = text.fontSize;
        text.enableAutoSizing = true;
        text.fontSizeMin = 8f;
        text.fontSizeMax = currentSize;
        text.enableWordWrapping = true;
    }

    public static void ApplyFontToText(TMP_Text text)
    {
        if (russianFont != null && text != null && text.font != russianFont)
        {
            text.font = russianFont;
        }
        if (text != null && !text.enableAutoSizing)
        {
            float currentSize = text.fontSize;
            text.enableAutoSizing = true;
            text.fontSizeMin = 8f;
            text.fontSizeMax = currentSize;
            text.enableWordWrapping = true;
        }
    }

    public static void RegisterUntranslated(string original, string type)
    {
        if (string.IsNullOrEmpty(original)) return;
        if (original.Length > 500) return;
        if (original.All(c => char.IsDigit(c) || c == '.' || c == ',' || c == ' ' || c == ':' || c == '/')) return;

        string entry = $"[{type}] {original}";
        lock (untranslatedStrings)
        {
            untranslatedStrings.Add(entry);
        }
    }

    private IEnumerator SaveUntranslatedPeriodically()
    {
        yield return new WaitForSeconds(10f);

        while (true)
        {
            yield return new WaitForSeconds(30f);
            SaveUntranslatedToFile();
        }
    }

    private void OnApplicationQuit()
    {
        SaveUntranslatedToFile();
    }

    private static void SaveUntranslatedToFile()
    {
        lock (untranslatedStrings)
        {
            if (untranslatedStrings.Count > 0)
            {
                try
                {
                    List<string> sorted = new List<string>(untranslatedStrings);
                    sorted.Sort();
                    File.WriteAllLines(untranslatedFilePath, sorted, System.Text.Encoding.UTF8);
                    instance?.Logger.LogInfo($"Сохранено {untranslatedStrings.Count} непереведённых строк");
                }
                catch (System.Exception e)
                {
                    instance?.Logger.LogError($"Ошибка сохранения: {e.Message}");
                }
            }
        }
    }
}

[HarmonyPatch(typeof(string), nameof(string.Format), new System.Type[] { typeof(string), typeof(object) })]
public static class StringFormat1Patch
{
    static void Prefix(ref string format)
    {
        format = Translator.Translate(format, "string.Format");
    }
}

[HarmonyPatch(typeof(string), nameof(string.Format), new System.Type[] { typeof(string), typeof(object), typeof(object) })]
public static class StringFormat2Patch
{
    static void Prefix(ref string format)
    {
        format = Translator.Translate(format, "string.Format");
    }
}

[HarmonyPatch(typeof(string), nameof(string.Format), new System.Type[] { typeof(string), typeof(object), typeof(object), typeof(object) })]
public static class StringFormat3Patch
{
    static void Prefix(ref string format)
    {
        format = Translator.Translate(format, "string.Format");
    }
}

[HarmonyPatch(typeof(string), nameof(string.Format), new System.Type[] { typeof(string), typeof(object[]) })]
public static class StringFormatArrayPatch
{
    static void Prefix(ref string format)
    {
        format = Translator.Translate(format, "string.Format");
    }
}

[HarmonyPatch(typeof(Text), "text", MethodType.Setter)]
public static class TextPatch
{
    static void Prefix(ref string value)
    {
        value = Translator.Translate(value, "Text.text");
    }
}

[HarmonyPatch(typeof(TMP_Text), "text", MethodType.Setter)]
public static class TMPTextPropertyPatch
{
    static void Prefix(TMP_Text __instance, ref string value)
    {
        value = Translator.Translate(value, "TMP_Text.text");
    }

    static void Postfix(TMP_Text __instance)
    {
        TranslationMod.ApplyFontToText(__instance);
    }
}

[HarmonyPatch(typeof(TMP_Text), "maxVisibleCharacters", MethodType.Setter)]
public static class TMPMaxVisibleCharactersPatch
{
    private static Dictionary<int, TextAnimationData> animationData = new Dictionary<int, TextAnimationData>();
    private static HashSet<int> trackedInstances = new HashSet<int>();

    private class TextAnimationData
    {
        public string originalText;
        public string translatedText;
        public int originalLength;
        public int translatedLength;
    }

    static void Prefix(TMP_Text __instance, ref int value)
    {
        if (__instance == null || string.IsNullOrEmpty(__instance.text)) return;

        int instanceID = __instance.GetInstanceID();
        string currentText = __instance.text;

        if (!trackedInstances.Contains(instanceID))
        {
            trackedInstances.Add(instanceID);
        }

        if (!animationData.ContainsKey(instanceID))
        {
            string originalText = FindOriginalText(currentText);
            animationData[instanceID] = new TextAnimationData
            {
                originalText = originalText,
                translatedText = currentText,
                originalLength = originalText.Length,
                translatedLength = currentText.Length
            };
        }
        else
        {
            var data = animationData[instanceID];
            if (data.translatedText != currentText)
            {
                string originalText = FindOriginalText(currentText);
                data.originalText = originalText;
                data.translatedText = currentText;
                data.originalLength = originalText.Length;
                data.translatedLength = currentText.Length;
            }
        }

        var info = animationData[instanceID];

        if (value < info.translatedLength && info.originalLength > 0)
        {
            float progress = (float)value / (float)info.originalLength;
            int newValue = Mathf.RoundToInt(info.translatedLength * progress);
            value = Mathf.Clamp(newValue, 0, info.translatedLength);
        }
    }

    private static string FindOriginalText(string translatedText)
    {
        foreach (var pair in Dictionary.Map)
        {
            if (pair.Value == translatedText)
            {
                return pair.Key;
            }
        }
        return translatedText;
    }

    public static IEnumerator CleanupOldEntries()
    {
        while (true)
        {
            yield return new WaitForSeconds(30f);

            List<int> toRemove = new List<int>();

            foreach (int instanceID in trackedInstances)
            {
                TMP_Text[] allTexts = Resources.FindObjectsOfTypeAll<TMP_Text>();
                bool found = false;

                foreach (var text in allTexts)
                {
                    if (text != null && text.GetInstanceID() == instanceID)
                    {
                        found = true;
                        break;
                    }
                }

                if (!found)
                {
                    toRemove.Add(instanceID);
                }
            }

            foreach (int id in toRemove)
            {
                animationData.Remove(id);
                trackedInstances.Remove(id);
            }

            if (toRemove.Count > 0)
            {
                Debug.Log($"Очищено {toRemove.Count} устаревших записей анимации");
            }
        }
    }
}

public class TranslationPattern
{
    private string originalPrefix;
    private string translatedPrefix;

    public TranslationPattern(string original, string translated)
    {
        originalPrefix = original;
        translatedPrefix = translated;
    }

    public string TryTranslate(string text)
    {
        if (text.StartsWith(originalPrefix))
        {
            string suffix = text.Substring(originalPrefix.Length);
            string translatedSuffix = Translator.TranslateSimple(suffix);
            return translatedPrefix + translatedSuffix;
        }
        return null;
    }
}

public class ParameterizedTranslation
{
    private string pattern;
    private string translation;
    private Regex regex;

    public ParameterizedTranslation(string pattern, string translation)
    {
        this.pattern = pattern;
        this.translation = translation;

        string regexPattern = Regex.Escape(pattern);
        regexPattern = Regex.Replace(regexPattern, @"\\?\{(\w+)\\?\}", @"(?<$1>\d+)");

        try
        {
            regex = new Regex("^" + regexPattern + "$", RegexOptions.Singleline);
        }
        catch (System.Exception) { }
    }

    public string TryTranslate(string text)
    {
        if (regex == null) return null;

        try
        {
            Match match = regex.Match(text);
            if (match.Success)
            {
                string result = translation;
                foreach (Group group in match.Groups)
                {
                    if (group.Name != "0" && int.TryParse(group.Name, out _) == false)
                    {
                        string value = group.Value;

                        if (result.Contains("{" + group.Name + "|"))
                        {
                            result = RussianPlurals.ApplyPlural(result, group.Name, value);
                        }
                        else
                        {
                            result = result.Replace("{" + group.Name + "}", value);
                        }
                    }
                }
                return result;
            }
        }
        catch (System.Exception) { }

        return null;
    }
}

public static class RussianPlurals
{
    public static string ApplyPlural(string template, string paramName, string value)
    {
        Regex pluralRegex = new Regex(@"\{" + paramName + @"\|([^|]+)\|([^|]+)\|([^}]+)\}");
        Match match = pluralRegex.Match(template);

        if (!match.Success)
            return template.Replace("{" + paramName + "}", value);

        string form1 = match.Groups[1].Value;
        string form2 = match.Groups[2].Value;
        string form3 = match.Groups[3].Value;

        if (!int.TryParse(value, out int number))
            return template.Replace(match.Value, value + " " + form3);

        string selectedForm = GetPluralForm(number, form1, form2, form3);
        return template.Replace(match.Value, value + " " + selectedForm);
    }

    private static string GetPluralForm(int number, string form1, string form2, string form3)
    {
        int mod10 = number % 10;
        int mod100 = number % 100;

        if (mod100 >= 11 && mod100 <= 19)
            return form3;

        if (mod10 == 1)
            return form1;

        if (mod10 >= 2 && mod10 <= 4)
            return form2;

        return form3;
    }
}

public enum Gender
{
    Masculine,
    Feminine,
    Neuter
}

public class CompositeTranslation
{
    private Regex pieceRegex;
    private Regex landmineRegex;

    private Dictionary<string, Gender> pieceGenders = new Dictionary<string, Gender>
    {
        { "PAWN", Gender.Feminine },
        { "KNIGHT", Gender.Masculine },
        { "BISHOP", Gender.Masculine },
        { "ROOK", Gender.Feminine },
        { "QUEEN", Gender.Masculine },
        { "KING", Gender.Masculine },
        { "LANDMINE", Gender.Masculine }
    };

    private Dictionary<string, Dictionary<string, string>> declensions = new Dictionary<string, Dictionary<string, string>>
    {
        {
            "WHITE", new Dictionary<string, string>
            {
                { "PAWN", "Белая пешка" },
                { "KNIGHT", "Белый конь" },
                { "BISHOP", "Белый слон" },
                { "ROOK", "Белая ладья" },
                { "QUEEN", "Белый ферзь" },
                { "KING", "Белый король" },
                { "LANDMINE", "Дар знания" }
            }
        },
        {
            "BLACK", new Dictionary<string, string>
            {
                { "PAWN", "Чёрная пешка" },
                { "KNIGHT", "Чёрный конь" },
                { "BISHOP", "Чёрный слон" },
                { "ROOK", "Чёрная ладья" },
                { "QUEEN", "Чёрный ферзь" },
                { "KING", "Чёрный король" },
                { "LANDMINE", "Дар знания" }
            }
        }
    };

    private Dictionary<string, string[]> ruleGenderForms = new Dictionary<string, string[]>
    {
        { "DID NOT CATCH THE OTHER CHEATING?", new[] { "не заметил обман противника?", "не заметила обман противника?", "не заметило обман противника?" } },
        { "FALSELY ACCUSED THE OTHER OF CHEATING?", new[] { "ложно обвинил противника в обмане?", "ложно обвинила противника в обмане?", "ложно обвинило противника в обмане?" } },
        { "WAS MOVED BY THE WRONG COLOR.", new[] { "был перемещён чужой рукой.", "была перемещена чужой рукой.", "было перемещено чужой рукой." } },
        { "WAS ALSO A QUEEN?", new[] { "был также ферзём?", "была также ферзём?", "было также ферзём?" } },
        { "MOVED BIG MINDED.", new[] { "двигался, витая в облаках.", "двигалась, витая в облаках.", "двигалось, витая в облаках." } },
        { "WAS NOT A METAPHOR?", new[] { "не был метафорой?", "не была метафорой?", "не было метафорой?" } },
        { "HAS WRONGLY DEFINED BACKWARDS.", new[] { "неправильно шагнул назад.", "неправильно шагнула назад.", "неправильно шагнуло назад." } },
        { "DID NOT TROT, CANTER OR GALLOP.", new[] { "не летел галопом и не нёсся вскачь.", "не летела галопом и не неслась вскачь.", "не летело галопом и не неслось вскачь." } },
        { "NEIGHS.", new[] { "ржёт.", "ржёт.", "ржёт." } },
        { "JUMPED WHEN ONLY HE CAN JUMP.", new[] { "прыгнул, хотя на поле только один прыгун.", "прыгнула, хотя на поле только один прыгун.", "прыгнуло, хотя на поле только один прыгун." } },
        { "DIED AND BLACK WINS THE GAME?", new[] { "умер и чёрные выиграли?", "умерла и чёрные выиграли?", "умерло и чёрные выиграли?" } },
        { "DID NOT SUPPORT THE MONARCHY?", new[] { "не поддержал монархию?", "не поддержала монархию?", "не поддержало монархию?" } },
        { "DID NOT SEEM LAZY.", new[] { "не выглядел ленивым.", "не выглядела ленивой.", "не выглядело ленивым." } },
        { "TRAVELED IN THE DIRECTION OF + .", new[] { "двигался в направлении + .", "двигалась в направлении + .", "двигалось в направлении + ." } },
        { "TRAVELED IN DIRECTION OF X .", new[] { "двигался в направлении × .", "двигалась в направлении × .", "двигалось в направлении × ." } },
        { "DID NOT GET SUPPER?", new[] { "не получил ужин?", "не получила ужин?", "не получило ужин?" } },
        { "DID NOT MERGE INTO A CASTLE.", new[] { "не объединился в замок.", "не объединилась в замок.", "не объединилось в замок." } },
        { "DID NOT GENERATE VALORITE SCRAPS.", new[] { "не создал кусков валорита.", "не создала кусков валорита.", "не создало кусков валорита." } },
        { "DOES NOT KNOW MOVE ETIQUETTE.", new[] { "не знает этикета ходов.", "не знает этикета ходов.", "не знает этикета ходов." } },
        { "DATES BACK TO THE WRINKLED AGES.", new[] { "восходит к древним временам.", "восходит к древним временам.", "восходит к древним временам." } },
        { "DID NOT ASCEND WHEN THEY SHOULD HAVE.", new[] { "не вознёсся, когда должен был.", "не вознеслась, когда должна была.", "не вознеслось, когда должно было." } },
        { "DID NOT FLIP HORIZONTALLY.", new[] { "не перевернул весь мир по горизонтали.", "не перевернула весь мир по горизонтали.", "не перевернуло весь мир по горизонтали." } },
        { "FORGOT TO BRING A GIFT.", new[] { "забыл принести подарок.", "забыла принести подарок.", "забыло принести подарок." } },
        { "DID NOT ADJUST THEIR DAMAGE POWER.", new[] { "не увеличил свою мощь.", "не увеличила свою мощь.", "не увеличило свою мощь." } },
        { "STEPPED TOO CLOSE TO ONE ANOTHER.", new[] { "подошёл слишком близко к другой фигуре?", "подошла слишком близко к другой фигуре?", "подошло слишком близко к другой фигуре?" } },
        { "DID NOT WORK OUT OF TOWN.", new[] { "не работал за городом.", "не работала за городом.", "не работало за городом." } },
        { "WAS MOVED.", new[] { "был перемещён.", "была перемещена.", "было перемещено." } },
        { "WAS NOT SLIPPERY.", new[] { "не был скользким.", "не была скользкой.", "не было скользким." } },
        { "IS BAD AT COUNTING.", new[] { "плохо считает.", "плохо считает.", "плохо считает." } },
        { "HAD AN AFFAIR.", new[] { "имел роман на стороне?", "имела роман на стороне?", "имело роман на стороне?" } },
        { "WAS NOT CREDITED IN THE EPILOGUE?", new[] { "не был упомянут в эпилоге?", "не была упомянута в эпилоге?", "не было упомянуто в эпилоге?" } },
        { "IS NOT EVEN TRYING?", new[] { "даже не собирается прочесть правила?", "даже не собирается прочесть правила?", "даже не собирается прочесть правила?" } },
        { "DOES NOT SUSPECT THE OTHER COLOR?", new[] { "не подозревает другой цвет?", "не подозревает другой цвет?", "не подозревает другой цвет?" } },
        { "DOES NOT UNDERSTAND THIS PAGE?", new[] { "не понимает эту страницу?", "не понимает эту страницу?", "не понимает эту страницу?" } },
        { "IS NOT CONTENT?", new[] { "не доволен?", "не довольна?", "не довольно?" } }
    };

    public CompositeTranslation()
    {
        pieceRegex = new Regex(@"^(WHITE|BLACK)\s+(PAWN|KNIGHT|BISHOP|ROOK|QUEEN|KING)");
        landmineRegex = new Regex(@"^\s*LANDMINE\s+(.+)$");
    }

    private string GetGenderedRule(string rule, Gender gender)
    {
        if (ruleGenderForms.TryGetValue(rule, out string[] forms))
        {
            int index = (int)gender;
            return forms[index];
        }

        return Translator.TranslateSimple(rule);
    }

    public string TryTranslate(string text)
    {
        if (text.Trim() == "[ CHESS PIECE ] + [ RULE VIOLATED ]")
        {
            return "[ ШАХМАТНАЯ ФИГУРА ] + [ ПРАВИЛО НАРУШЕНО ]";
        }
        if (text.Trim() == "[ CHESS PIECE ] ?")
        {
            return "[ ШАХМАТНАЯ ФИГУРА ] ?";
        }

        if (text.Contains("[ CHESS PIECE ]"))
        {
            string rule = text.Replace("[ CHESS PIECE ]", "").Trim();
            string translatedRule = Translator.TranslateSimple(rule);
            return "[ ШАХМАТНАЯ ФИГУРА ] " + translatedRule;
        }

        // Обработка LANDMINE + [ RULE VIOLATED ]
        if (text.Trim() == "LANDMINE + [ RULE VIOLATED ]")
        {
            return "Дар знания + [ ПРАВИЛО НАРУШЕНО ]";
        }

        // Обработка LANDMINE + правило
        Match landmineMatch = landmineRegex.Match(text);
        if (landmineMatch.Success)
        {
            string rule = landmineMatch.Groups[1].Value.Trim();

            // Убираем "+ [ RULE VIOLATED ]" если есть
            if (rule == "+ [ RULE VIOLATED ]")
            {
                return "Дар знания + [ ПРАВИЛО НАРУШЕНО ]";
            }

            string translatedRule = GetGenderedRule(rule, Gender.Masculine);
            return $"Дар знания {translatedRule}";
        }

        if (text.Contains("+ [ RULE VIOLATED ]"))
        {
            Match pieceMatch = pieceRegex.Match(text);
            if (pieceMatch.Success)
            {
                string color = pieceMatch.Groups[1].Value;
                string piece = pieceMatch.Groups[2].Value;

                if (declensions.ContainsKey(color) && declensions[color].ContainsKey(piece))
                {
                    string translatedPiece = declensions[color][piece];
                    return $"{translatedPiece} + [ ПРАВИЛО НАРУШЕНО ]";
                }
            }
        }

        Match fullMatch = pieceRegex.Match(text);
        if (fullMatch.Success)
        {
            string color = fullMatch.Groups[1].Value;
            string piece = fullMatch.Groups[2].Value;
            string rest = text.Substring(fullMatch.Length).Trim();

            if (declensions.ContainsKey(color) && declensions[color].ContainsKey(piece))
            {
                string translatedPiece = declensions[color][piece];
                Gender gender = pieceGenders.ContainsKey(piece) ? pieceGenders[piece] : Gender.Masculine;
                string translatedRest = GetGenderedRule(rest, gender);

                return $"{translatedPiece} {translatedRest}";
            }
        }

        return null;
    }
}

public static class Translator
{
    private static List<ParameterizedTranslation> parameterizedTranslations = new List<ParameterizedTranslation>();
    private static CompositeTranslation compositeTranslation = new CompositeTranslation();
    private static Dictionary<string, string> translationCache = new Dictionary<string, string>();
    private const int MAX_CACHE_SIZE = 1000;

    private static Dictionary<string, string> hardcodedTranslations = new Dictionary<string, string>
    {
        // ADDITIONAL DESIGN
        { "ADDITIONAL DESIGN\n\nILSE BAARS\nMERIJN TRIMBOS\nRANDY QUERREVELD", "Дополнительный дизайн\n\nILSE BAARS\nMERIJN TRIMBOS\nRANDY QUERREVELD" },
        
        // SPECIAL THANKS блоки - все варианты с разными \n
        { "SPECIAL THANKS\n\n\nKAREL MILLENAAR\nVALENTIJN MUIJRERS\nDIMME VAN DER HOUT", "Особая благодарность\n\n\nKAREL MILLENAAR\nVALENTIJN MUIJRERS\nDIMME VAN DER HOUT" },
        { "SPECIAL THANKS\n\nKAREL MILLENAAR\nVALENTIJN MUIJRERS\nDIMME VAN DER HOUT", "Особая благодарность\n\nKAREL MILLENAAR\nVALENTIJN MUIJRERS\nDIMME VAN DER HOUT" },

        { "SPECIAL THANKS\n\nCATHY VAN DE LAAK\nJANDIRK VAN DINGENEN", "Особая благодарность\n\nCATHY VAN DE LAAK\nJANDIRK VAN DINGENEN" },

        { "SPECIAL THANKS\n\nFRANK SCHUURING\nILJA SCHUURING\nJOEP SCHUURING\nBRAM SCHUURING", "Особая благодарность\n\nFRANK SCHUURING\nILJA SCHUURING\nJOEP SCHUURING\nBRAM SCHUURING" },

        { "SPECIAL THANKS\n\nORION KEREN PUTS\nDAVID KOLB\nJURRE DE GROOT\nMAXYM EBELING\nBENITO VAN DER ZANDEN", "Особая благодарность\n\nORION KEREN PUTS\nDAVID KOLB\nJURRE DE GROOT\nMAXYM EBELING\nBENITO VAN DER ZANDEN" },

        { "SPECIAL THANKS\n\nROEL VAN BROEKHOVEN\nKAAN WIJNAND\nPEPIJN BELDER\nJORIS BELDER\nMILO DAMMERS", "Особая благодарность\n\nROEL VAN BROEKHOVEN\nKAAN WIJNAND\nPEPIJN BELDER\nJORIS BELDER\nMILO DAMMERS" },
        
        // Авторский блок
        { "Thank you for playing.", "Спасибо за игру.\n\nПеревёл lion.burmistrov" }
    };

    public static void AddParameterizedTranslation(string pattern, string translation)
    {
        parameterizedTranslations.Add(new ParameterizedTranslation(pattern, translation));
    }

    public static string TranslateSimple(string text)
    {
        if (Dictionary.Map.TryGetValue(text, out string translated))
            return translated;
        return text;
    }

    public static string Translate(string original, string type)
    {
        if (string.IsNullOrEmpty(original))
            return original;

        // Нормализуем только \r\n -> \n, НЕ трогаем количество переносов
        string normalized = original.Replace("\r\n", "\n");

        // Специальная обработка для блоков SPECIAL THANKS и ADDITIONAL DESIGN
        if (normalized.StartsWith("SPECIAL THANKS\n"))
        {
            return normalized.Replace("SPECIAL THANKS", "Особая благодарность");
        }
        if (normalized.StartsWith("ADDITIONAL DESIGN\n"))
        {
            return normalized.Replace("ADDITIONAL DESIGN", "Дополнительный дизайн");
        }

        if (hardcodedTranslations.TryGetValue(normalized, out string hardcoded))
            return hardcoded;

        if (translationCache.TryGetValue(normalized, out string cached))
            return cached;

        if (Dictionary.Map.TryGetValue(normalized, out string translated))
        {
            AddToCache(normalized, translated);
            return translated;
        }

        if (Dictionary.Map.TryGetValue(original, out string translated2))
        {
            AddToCache(normalized, translated2);
            return translated2;
        }

        string compositeResult = compositeTranslation.TryTranslate(original);
        if (compositeResult != null)
        {
            AddToCache(normalized, compositeResult);
            return compositeResult;
        }

        foreach (var paramTranslation in parameterizedTranslations)
        {
            string result = paramTranslation.TryTranslate(original);
            if (result != null)
            {
                AddToCache(normalized, result);
                return result;
            }
        }

        foreach (var pattern in Dictionary.Patterns)
        {
            string result = pattern.TryTranslate(original);
            if (result != null)
            {
                AddToCache(normalized, result);
                return result;
            }
        }

        TranslationMod.RegisterUntranslated(original, type);

        AddToCache(normalized, original);
        return original;
    }

    private static void AddToCache(string key, string value)
    {
        if (translationCache.Count >= MAX_CACHE_SIZE)
        {
            var toRemove = translationCache.Keys.Take(MAX_CACHE_SIZE / 2).ToList();
            foreach (var k in toRemove)
            {
                translationCache.Remove(k);
            }
        }

        translationCache[key] = value;
    }
}

public static class Dictionary
{
    public static readonly System.Collections.Generic.Dictionary<string, string> Map =
        new System.Collections.Generic.Dictionary<string, string>();

    public static readonly List<TranslationPattern> Patterns = new List<TranslationPattern>();

    public static void LoadFromFile(string path, BepInEx.Logging.ManualLogSource logger)
    {
        if (!File.Exists(path))
        {
            logger.LogError($"Файл перевода не найден: {path}");
            return;
        }

        logger.LogInfo($"Загрузка переводов из: {path}");

        string[] lines = File.ReadAllLines(path, System.Text.Encoding.UTF8);
        int loadedCount = 0;
        int patternCount = 0;
        int parameterizedCount = 0;

        foreach (string line in lines)
        {
            if (string.IsNullOrWhiteSpace(line) || line.StartsWith("#"))
                continue;

            int separatorIndex = line.IndexOf('=');
            if (separatorIndex == -1)
                continue;

            string original = line.Substring(0, separatorIndex);
            string translated = line.Substring(separatorIndex + 1);

            bool hasParameters = original.Contains("{") && original.Contains("}");

            if (hasParameters)
            {
                Translator.AddParameterizedTranslation(original, translated);
                parameterizedCount++;
            }
            else if (original.EndsWith(" "))
            {
                Patterns.Add(new TranslationPattern(original, translated));
                patternCount++;
            }

            Map[original] = translated;
            loadedCount++;
        }

        logger.LogInfo($"Загружено: {loadedCount} строк ({patternCount} паттернов, {parameterizedCount} параметризованных)");
    }
}