using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using BepInEx.Logging;

namespace KingOfTheBridge.Russian
{
    internal static class UntranslatedLog
    {
        private static readonly HashSet<string> Entries = new HashSet<string>(StringComparer.Ordinal);
        private static readonly Regex LatinText = new Regex("[A-Za-z]{2,}", RegexOptions.Compiled);
        private static string path;
        private static bool enabled;
        private static bool dirty;
        private static ManualLogSource logger;

        public static void Initialize(string outputPath, bool isEnabled, ManualLogSource log)
        {
            path = outputPath;
            enabled = isEnabled;
            logger = log;
            Entries.Clear();
            dirty = false;
            if (!enabled)
                return;
            try
            {
                File.WriteAllText(path, string.Empty, Encoding.UTF8);
            }
            catch (Exception exception)
            {
                logger?.LogWarning($"Could not reset untranslated strings log: {exception.Message}");
            }
        }

        public static void Register(string source, string origin)
        {
            if (!enabled || string.IsNullOrWhiteSpace(source) || source.Length > 500 || !LatinText.IsMatch(source))
                return;
            dirty |= Entries.Add($"[{origin}] {source.Replace("\r", "\\r").Replace("\n", "\\n")}");
        }

        public static void Flush()
        {
            if (!enabled || !dirty || string.IsNullOrEmpty(path))
                return;
            try
            {
                File.WriteAllLines(path, Entries.OrderBy(value => value, StringComparer.Ordinal), Encoding.UTF8);
                dirty = false;
            }
            catch (Exception exception)
            {
                logger?.LogWarning($"Could not write untranslated strings: {exception.Message}");
            }
        }
    }
}
