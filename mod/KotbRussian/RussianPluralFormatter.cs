using System.Globalization;
using UnityEngine.Localization.SmartFormat.Core.Extensions;

namespace KotbRussian
{
    /// <summary>
    /// SmartFormat "plural" formatter for Russian: {value:plural(ru):one|few|many}.
    /// The game's localization settings ship without a plural formatter, and the credits pass their counters as
    /// strings, which the stock PluralLocalizationFormatter refuses; this one parses them.
    /// </summary>
    internal sealed class RussianPluralFormatter : IFormatter
    {
        public string[] Names { get; set; } = { "plural" };

        public bool TryEvaluateFormat(IFormattingInfo formattingInfo)
        {
            var format = formattingInfo.Format;
            if (format == null || !TryGetCount(formattingInfo.CurrentValue, out long count))
            {
                return false;
            }
            var forms = format.Split('|');
            if (forms.Count < 2)
            {
                return false;
            }
            int index = System.Math.Min(Category(count), forms.Count - 1);
            formattingInfo.Write(forms[index], formattingInfo.CurrentValue);
            return true;
        }

        /// <summary>Russian plural category: 0 = one (1, 21, 31), 1 = few (2-4, 22-24), 2 = many.</summary>
        public static int Category(long n)
        {
            n = System.Math.Abs(n);
            long mod10 = n % 10, mod100 = n % 100;
            if (mod10 == 1 && mod100 != 11)
            {
                return 0;
            }
            if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14))
            {
                return 1;
            }
            return 2;
        }

        private static bool TryGetCount(object value, out long count)
        {
            switch (value)
            {
                case string text:
                    return long.TryParse(text.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out count);
                case int i:
                    count = i;
                    return true;
                case long l:
                    count = l;
                    return true;
                case float f:
                    count = (long)f;
                    return true;
                case double d:
                    count = (long)d;
                    return true;
                default:
                    count = 0;
                    return false;
            }
        }
    }
}
