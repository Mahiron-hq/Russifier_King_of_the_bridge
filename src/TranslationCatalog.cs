using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using BepInEx.Logging;

namespace KingOfTheBridge.Russian
{
    internal static class TranslationCatalog
    {
        private const int MaxCacheSize = 2048;
        private static readonly Dictionary<string, string> Entries =
            new Dictionary<string, string>(StringComparer.Ordinal);
        private static readonly List<PrefixTranslation> Prefixes = new List<PrefixTranslation>();
        private static readonly List<ParameterizedTranslation> Parameters = new List<ParameterizedTranslation>();
        private static readonly Dictionary<string, string> Cache =
            new Dictionary<string, string>(StringComparer.Ordinal);
        private static readonly HashSet<string> DeferredFragments = new HashSet<string>(StringComparer.Ordinal)
        {
            "It took you",
            "hour,",
            "hours,",
            "minute and",
            "minutes and",
            "second.",
            "seconds."
        };

        public static void Load(string path, ManualLogSource logger)
        {
            Entries.Clear();
            Prefixes.Clear();
            Parameters.Clear();
            Cache.Clear();

            if (!File.Exists(path))
            {
                logger.LogError($"Translation file not found: {path}");
                return;
            }

            int lineNumber = 0;
            foreach (string rawLine in File.ReadAllLines(path, Encoding.UTF8))
            {
                lineNumber++;
                if (string.IsNullOrWhiteSpace(rawLine) || rawLine.StartsWith("#", StringComparison.Ordinal))
                    continue;

                int separator = rawLine.IndexOf('=');
                if (separator < 1)
                {
                    logger.LogWarning($"Ignoring malformed translation line {lineNumber}");
                    continue;
                }

                string source = DecodeEscapes(rawLine.Substring(0, separator));
                string translation = DecodeEscapes(rawLine.Substring(separator + 1));
                if (Entries.ContainsKey(source))
                    logger.LogWarning($"Duplicate translation key on line {lineNumber}: {source}");
                Entries[source] = translation;

                if (source.EndsWith(" ", StringComparison.Ordinal))
                    Prefixes.Add(new PrefixTranslation(source, translation));
                if (Regex.IsMatch(source, @"\{[A-Za-z_][A-Za-z0-9_]*\}"))
                    Parameters.Add(new ParameterizedTranslation(source, translation, logger));
            }

            logger.LogInfo($"Loaded {Entries.Count} translations ({Prefixes.Count} prefixes, {Parameters.Count} templates)");
        }

        public static string Translate(string source, string origin)
        {
            if (DeferredFragments.Contains(source))
                return source;
            if (TryTranslateKnown(source, out string translated))
                return translated;
            if (ContainsCyrillic(source))
                return source;

            UntranslatedLog.Register(source, origin);
            return source;
        }

        public static bool TryTranslateKnown(string source, out string translated)
        {
            translated = source;
            if (string.IsNullOrEmpty(source))
                return false;

            string normalized = NormalizeLineEndings(source);
            if (Cache.TryGetValue(normalized, out translated))
                return translated != normalized;

            if (TryTranslateCore(normalized, out translated))
            {
                AddToCache(normalized, translated);
                return true;
            }

            string trimmed = normalized.Trim();
            if (trimmed.Length != normalized.Length && TryTranslateCore(trimmed, out string trimmedTranslation))
            {
                int leading = normalized.Length - normalized.TrimStart().Length;
                int trailing = normalized.Length - normalized.TrimEnd().Length;
                translated = normalized.Substring(0, leading) + trimmedTranslation;
                if (trailing > 0)
                    translated += normalized.Substring(normalized.Length - trailing);
                AddToCache(normalized, translated);
                return true;
            }

            AddToCache(normalized, normalized);
            translated = source;
            return false;
        }

        public static bool TryTranslateExact(string source, out string translated)
        {
            return Entries.TryGetValue(source, out translated);
        }

        private static bool TryTranslateCore(string source, out string translated)
        {
            if (Entries.TryGetValue(source, out translated))
                return true;

            if (source.StartsWith("SPECIAL THANKS\n", StringComparison.Ordinal))
            {
                translated = "ОСОБАЯ БЛАГОДАРНОСТЬ" + source.Substring("SPECIAL THANKS".Length);
                return true;
            }
            if (source.StartsWith("ADDITIONAL DESIGN\n", StringComparison.Ordinal))
            {
                translated = "ДОПОЛНИТЕЛЬНЫЙ ДИЗАЙН" + source.Substring("ADDITIONAL DESIGN".Length);
                return true;
            }

            foreach (ParameterizedTranslation parameter in Parameters)
            {
                if (parameter.TryTranslate(source, out translated))
                    return true;
            }
            foreach (PrefixTranslation prefix in Prefixes)
            {
                if (prefix.TryTranslate(source, out translated))
                    return true;
            }

            translated = source;
            return false;
        }

        private static string NormalizeLineEndings(string value)
        {
            return value.Replace("\r\n", "\n").Replace('\r', '\n');
        }

        private static string DecodeEscapes(string value)
        {
            return value.Replace("\\n", "\n").Replace("\\r", "\r").Replace("\\t", "\t");
        }

        private static bool ContainsCyrillic(string value)
        {
            return value.Any(character => character >= '\u0400' && character <= '\u04ff');
        }

        private static void AddToCache(string source, string translated)
        {
            if (Cache.Count >= MaxCacheSize)
                Cache.Clear();
            Cache[source] = translated;
        }

        private sealed class PrefixTranslation
        {
            private readonly string source;
            private readonly string translation;

            public PrefixTranslation(string source, string translation)
            {
                this.source = source;
                this.translation = translation;
            }

            public bool TryTranslate(string value, out string result)
            {
                if (!value.StartsWith(source, StringComparison.Ordinal))
                {
                    result = value;
                    return false;
                }

                string suffix = value.Substring(source.Length);
                if (Entries.TryGetValue(suffix, out string translatedSuffix))
                    suffix = translatedSuffix;
                result = translation + suffix;
                return true;
            }
        }

        private sealed class ParameterizedTranslation
        {
            private static readonly Regex Placeholder =
                new Regex(@"\\\{([A-Za-z_][A-Za-z0-9_]*)\}", RegexOptions.Compiled);
            private readonly string translation;
            private readonly Regex expression;

            public ParameterizedTranslation(string source, string translation, ManualLogSource logger)
            {
                this.translation = translation;
                try
                {
                    string pattern = Placeholder.Replace(Regex.Escape(source), match =>
                        "(?<" + match.Groups[1].Value + ">.+?)");
                    expression = new Regex("^" + pattern + "$", RegexOptions.Compiled | RegexOptions.Singleline);
                }
                catch (Exception exception)
                {
                    logger.LogWarning($"Invalid translation template '{source}': {exception.Message}");
                }
            }

            public bool TryTranslate(string source, out string result)
            {
                result = source;
                if (expression == null)
                    return false;

                Match match = expression.Match(source);
                if (!match.Success)
                    return false;

                result = translation;
                foreach (string groupName in expression.GetGroupNames())
                {
                    if (groupName == "0" || int.TryParse(groupName, out _))
                        continue;
                    string value = match.Groups[groupName].Value;
                    result = RussianGrammar.ApplyPlural(result, groupName, value);
                    result = result.Replace("{" + groupName + "}", value);
                }
                return true;
            }
        }
    }
}
