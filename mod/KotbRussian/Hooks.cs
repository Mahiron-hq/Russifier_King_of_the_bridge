using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using Newtonsoft.Json.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.Localization.Settings;

namespace KotbRussian
{
    /// <summary>
    /// Entry points that the patched Assembly-CSharp calls instead of the original code.
    /// Every hook falls back to the game's own behaviour when the selected language is not Russian.
    /// </summary>
    public static class Hooks
    {
        private const string LocaleCode = "ru";

        private static bool initialized;
        private static RussianData data;
        private static RuleBookScreenManager ruleBookScreenManager;

        /// <summary>
        /// Loads the Russian data file, registers the plural formatter and starts the runtime helpers.
        /// Safe to call repeatedly.
        /// </summary>
        public static void Init()
        {
            if (initialized)
            {
                return;
            }
            initialized = true;
            string root = Path.Combine(Application.streamingAssetsPath, "ru");
            data = RussianData.Load(Path.Combine(root, "ru_extra.json"));
            RegisterPluralFormatter();
            TextFitter.Create();
            SpriteSwapper.Create(Path.Combine(root, "sprites"));
            CreditsSignature.Create();
        }

        private static void RegisterPluralFormatter()
        {
            var formatter = LocalizationSettings.HasSettings ? LocalizationSettings.StringDatabase?.SmartFormatter : null;
            if (formatter == null)
            {
                Debug.LogError("[KotbRussian] no SmartFormatter; Russian plural forms will not render");
                return;
            }
            if (!formatter.FormatterExtensions.Exists(f => f is RussianPluralFormatter))
            {
                formatter.AddExtensions(new RussianPluralFormatter());
            }
        }

        internal static bool IsRussian
        {
            get
            {
                var locale = LocalizationSettings.HasSettings ? LocalizationSettings.SelectedLocale : null;
                return data != null && locale != null && locale.Identifier.Code == LocaleCode;
            }
        }

        /// <summary>Replaces the credits line that the game assembles as "It took you N hours, N minutes and N seconds."</summary>
        public static void SetCreditsTimeText(TMP_Text target, string original)
        {
            if (!IsRussian)
            {
                target.text = original;
                return;
            }
            // Same split as OverworldTrollManager.Credits.
            float total = SaveSystem.currentPlayerSaveData.totalGameTime;
            int hours = Mathf.FloorToInt(total / 3600f);
            int minutes = Mathf.FloorToInt(total / 60f) - hours * 60;
            int seconds = Mathf.FloorToInt(total % 60f);

            string text = "";
            if (hours > 0)
            {
                text += hours + " " + data.TimeForm("hours", hours) + " ";
            }
            text += minutes + " " + data.TimeForm("minutes", minutes) + " ";
            text += seconds + " " + data.TimeForm("seconds", seconds);
            target.text = data.TimeLead + " " + text;
        }

        /// <summary>
        /// Replaces the accusation line "COLOR PIECE RULE" so the colour adjective and the rule's verb agree
        /// with the grammatical gender of the selected piece.
        /// </summary>
        public static void SetAccusationText(TMP_Text target, string original)
        {
            string text = IsRussian ? BuildAccusation() ?? original : original;
            if (target.text != text)
            {
                target.text = text;
            }
        }

        private static string BuildAccusation()
        {
            if (ruleBookScreenManager == null)
            {
                ruleBookScreenManager = UnityEngine.Object.FindObjectOfType<RuleBookScreenManager>();
                if (ruleBookScreenManager == null)
                {
                    return null;
                }
            }
            var manager = ruleBookScreenManager;
            ChessPieceObject piece = RuleBookScreenManager.cheatGuessAttemptChessPiece;
            RuleBookPage page = RuleBookScreenManager.cheatGuessAttemptRulebookPage;

            string gender = data.PlaceholderPieceGender;
            string color = "";
            string pieceName = manager.chessPieceString.GetLocalizedString();
            string rule = "+ " + manager.violatedRuleString.GetLocalizedString();

            if (piece != null)
            {
                gender = data.PieceGender(piece.pieceData.pieceType);
                switch (piece.pieceColor)
                {
                    case ChessMatchManager.ChessColor.White:
                        color = data.Color("WhiteKey", gender);
                        break;
                    case ChessMatchManager.ChessColor.Black:
                        color = data.Color("BlackKey", gender);
                        break;
                }
                pieceName = piece.pieceData.pieceNameString.GetLocalizedString();
            }
            if (page != null)
            {
                rule = manager.ruleBookFogManager.CheckIfPageIsFogged(page)
                    ? "?"
                    : data.Rule(page.ruleBreakString.TableEntryReference.KeyId, gender) ?? page.ruleBreakString.GetLocalizedString();
            }
            return (color + " " + pieceName + " " + rule).ToUpper(CultureInfo.GetCultureInfo("ru-RU"));
        }

        /// <summary>Wraps SteamAchievements.TryGetNameOfAchievement and translates the returned English name.</summary>
        public static string AchievementName(string id)
        {
            return TranslateAchievement(SteamAchievements.TryGetNameOfAchievement(id));
        }

        /// <summary>Wraps SteamAchievements.TryGetDescriptionOfAchievement and translates the returned text.</summary>
        public static string AchievementDescription(string id)
        {
            return TranslateAchievement(SteamAchievements.TryGetDescriptionOfAchievement(id));
        }

        private static string TranslateAchievement(string english)
        {
            if (!IsRussian || english == null)
            {
                return english;
            }
            return data.Achievement(english.Trim()) ?? english;
        }

        /// <summary>
        /// Sets a dialog line after enabling auto-size, so the font size is settled on the full line before the
        /// typewriter starts revealing characters.
        /// </summary>
        public static void SetDialogText(TMP_Text target, string value)
        {
            TextFitter.Fit(target);
            target.text = value;
        }
    }

    internal sealed class RussianData
    {
        private readonly Dictionary<string, string[]> time = new Dictionary<string, string[]>();
        private readonly Dictionary<string, Dictionary<string, string>> colors = new Dictionary<string, Dictionary<string, string>>();
        private readonly Dictionary<string, string> pieceGender = new Dictionary<string, string>();
        private readonly Dictionary<long, Dictionary<string, string>> rules = new Dictionary<long, Dictionary<string, string>>();
        private readonly Dictionary<string, string> achievements = new Dictionary<string, string>();

        public string TimeLead { get; private set; }

        public string PlaceholderPieceGender { get; private set; }

        public static RussianData Load(string path)
        {
            if (!File.Exists(path))
            {
                Debug.LogError("[KotbRussian] data file not found: " + path);
                return null;
            }
            var root = JObject.Parse(File.ReadAllText(path));
            var result = new RussianData
            {
                TimeLead = (string)root["time_lead"],
                PlaceholderPieceGender = (string)root["placeholder_piece_gender"],
            };
            foreach (var unit in (JObject)root["time"])
            {
                result.time[unit.Key] = new[] { (string)unit.Value["one"], (string)unit.Value["few"], (string)unit.Value["many"] };
            }
            foreach (var color in (JObject)root["colors"])
            {
                result.colors[color.Key] = color.Value.ToObject<Dictionary<string, string>>();
            }
            foreach (var piece in (JObject)root["piece_gender"])
            {
                result.pieceGender[piece.Key] = (string)piece.Value;
            }
            foreach (var rule in (JObject)root["rules_by_id"])
            {
                result.rules[long.Parse(rule.Key, CultureInfo.InvariantCulture)] = rule.Value.ToObject<Dictionary<string, string>>();
            }
            foreach (var pair in (JObject)root["achievements"])
            {
                result.achievements[pair.Key.Trim()] = (string)pair.Value;
            }
            return result;
        }

        /// <summary>Picks the one/few/many form of a time unit for <paramref name="n"/>.</summary>
        public string TimeForm(string unit, int n)
        {
            return time[unit][RussianPluralFormatter.Category(n)];
        }

        public string Color(string key, string gender)
        {
            return colors.TryGetValue(key, out var forms) && forms.TryGetValue(gender, out var text) ? text : "";
        }

        public string PieceGender(ChessPieceData.ChessPieceType type)
        {
            return pieceGender.TryGetValue(type.ToString(), out var gender) ? gender : "m";
        }

        public string Rule(long keyId, string gender)
        {
            return rules.TryGetValue(keyId, out var forms) && forms.TryGetValue(gender, out var text) ? text : null;
        }

        public string Achievement(string english)
        {
            return achievements.TryGetValue(english, out var text) ? text : null;
        }
    }
}
