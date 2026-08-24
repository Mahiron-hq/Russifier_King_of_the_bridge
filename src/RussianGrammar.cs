using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;

namespace KingOfTheBridge.Russian
{
    internal static class RussianGrammar
    {
        private enum Gender { Masculine, Feminine, Neuter }

        private static readonly Regex PieceExpression = new Regex(
            @"^(WHITE|BLACK)\s+(PAWN|KNIGHT|BISHOP|ROOK|QUEEN|KING)",
            RegexOptions.Compiled);
        private static readonly Regex LandmineExpression = new Regex(
            @"^\s*LANDMINE\s+(.+)$",
            RegexOptions.Compiled);

        private static readonly Dictionary<string, Gender> PieceGenders = new Dictionary<string, Gender>
        {
            { "PAWN", Gender.Feminine },
            { "KNIGHT", Gender.Masculine },
            { "BISHOP", Gender.Masculine },
            { "ROOK", Gender.Feminine },
            { "QUEEN", Gender.Feminine },
            { "KING", Gender.Masculine },
            { "LANDMINE", Gender.Masculine }
        };

        private static readonly Dictionary<string, string> Pieces = new Dictionary<string, string>
        {
            { "WHITE PAWN", "БЕЛАЯ ПЕШКА" }, { "WHITE KNIGHT", "БЕЛЫЙ КОНЬ" },
            { "WHITE BISHOP", "БЕЛЫЙ СЛОН" }, { "WHITE ROOK", "БЕЛАЯ ЛАДЬЯ" },
            { "WHITE QUEEN", "БЕЛАЯ КОРОЛЕВА" }, { "WHITE KING", "БЕЛЫЙ КОРОЛЬ" },
            { "BLACK PAWN", "ЧЁРНАЯ ПЕШКА" }, { "BLACK KNIGHT", "ЧЁРНЫЙ КОНЬ" },
            { "BLACK BISHOP", "ЧЁРНЫЙ СЛОН" }, { "BLACK ROOK", "ЧЁРНАЯ ЛАДЬЯ" },
            { "BLACK QUEEN", "ЧЁРНАЯ КОРОЛЕВА" }, { "BLACK KING", "ЧЁРНЫЙ КОРОЛЬ" }
        };

        private static readonly Dictionary<string, string[]> Rules = new Dictionary<string, string[]>
        {
            { "DID NOT CATCH THE OTHER CHEATING?", Forms("НЕ ЗАМЕТИЛ ОБМАН ПРОТИВНИКА?", "НЕ ЗАМЕТИЛА ОБМАН ПРОТИВНИКА?", "НЕ ЗАМЕТИЛО ОБМАН ПРОТИВНИКА?") },
            { "FALSELY ACCUSED THE OTHER OF CHEATING?", Forms("ЛОЖНО ОБВИНИЛ ПРОТИВНИКА В ОБМАНЕ?", "ЛОЖНО ОБВИНИЛА ПРОТИВНИКА В ОБМАНЕ?", "ЛОЖНО ОБВИНИЛО ПРОТИВНИКА В ОБМАНЕ?") },
            { "WAS MOVED BY THE WRONG COLOR.", Forms("СХОДИЛ ЗА ДРУГОЙ ЦВЕТ.", "СХОДИЛА ЗА ДРУГОЙ ЦВЕТ.", "СХОДИЛО ЗА ДРУГОЙ ЦВЕТ.") },
            { "WAS ALSO A QUEEN?", Forms("БЫЛ ТАКЖЕ КОРОЛЕВОЙ?", "БЫЛА ТАКЖЕ КОРОЛЕВОЙ?", "БЫЛО ТАКЖЕ КОРОЛЕВОЙ?") },
            { "MOVED BIG MINDED.", Forms("ДВИГАЛСЯ, ВИТАЯ В ОБЛАКАХ.", "ДВИГАЛАСЬ, ВИТАЯ В ОБЛАКАХ.", "ДВИГАЛОСЬ, ВИТАЯ В ОБЛАКАХ.") },
            { "WAS NOT A METAPHOR?", Forms("НЕ БЫЛ МЕТАФОРОЙ?", "НЕ БЫЛА МЕТАФОРОЙ?", "НЕ БЫЛО МЕТАФОРОЙ?") },
            { "HAS WRONGLY DEFINED BACKWARDS.", Forms("НЕПРАВИЛЬНО ШАГНУЛ НАЗАД.", "НЕПРАВИЛЬНО ШАГНУЛА НАЗАД.", "НЕПРАВИЛЬНО ШАГНУЛО НАЗАД.") },
            { "DID NOT TROT, CANTER OR GALLOP.", Forms("НЕ ЛЕТЕЛ ГАЛОПОМ И НЕ НЁССЯ ВСКАЧЬ.", "НЕ ЛЕТЕЛА ГАЛОПОМ И НЕ НЕСЛАСЬ ВСКАЧЬ.", "НЕ ЛЕТЕЛО ГАЛОПОМ И НЕ НЕСЛОСЬ ВСКАЧЬ.") },
            { "NEIGHS.", Forms("РЖЁТ.") },
            { "JUMPED WHEN ONLY HE CAN JUMP.", Forms("ПРЫГНУЛ, ХОТЯ ЭТО МОЖЕТ ТОЛЬКО КОНЬ.", "ПРЫГНУЛА, ХОТЯ ЭТО МОЖЕТ ТОЛЬКО КОНЬ.", "ПРЫГНУЛО, ХОТЯ ЭТО МОЖЕТ ТОЛЬКО КОНЬ.") },
            { "DIED AND BLACK WINS THE GAME?", Forms("УМЕР, И ЧЁРНЫЕ ВЫИГРАЛИ?", "УМЕРЛА, И ЧЁРНЫЕ ВЫИГРАЛИ?", "УМЕРЛО, И ЧЁРНЫЕ ВЫИГРАЛИ?") },
            { "DID NOT SUPPORT THE MONARCHY?", Forms("НЕ ПОДДЕРЖАЛ МОНАРХИЮ?", "НЕ ПОДДЕРЖАЛА МОНАРХИЮ?", "НЕ ПОДДЕРЖАЛО МОНАРХИЮ?") },
            { "DID NOT SEEM LAZY.", Forms("НЕ ВЫГЛЯДЕЛ ЛЕНИВЫМ.", "НЕ ВЫГЛЯДЕЛА ЛЕНИВОЙ.", "НЕ ВЫГЛЯДЕЛО ЛЕНИВЫМ.") },
            { "TRAVELED IN THE DIRECTION OF + .", Forms("ДВИГАЛСЯ В НАПРАВЛЕНИИ + .", "ДВИГАЛАСЬ В НАПРАВЛЕНИИ + .", "ДВИГАЛОСЬ В НАПРАВЛЕНИИ + .") },
            { "TRAVELED IN DIRECTION OF X .", Forms("ДВИГАЛСЯ В НАПРАВЛЕНИИ × .", "ДВИГАЛАСЬ В НАПРАВЛЕНИИ × .", "ДВИГАЛОСЬ В НАПРАВЛЕНИИ × .") },
            { "DID NOT GET SUPPER?", Forms("НЕ ПОЛУЧИЛ УЖИН?", "НЕ ПОЛУЧИЛА УЖИН?", "НЕ ПОЛУЧИЛО УЖИН?") },
            { "DID NOT MERGE INTO A CASTLE.", Forms("НЕ ОБЪЕДИНИЛСЯ В ЗАМОК.", "НЕ ОБЪЕДИНИЛАСЬ В ЗАМОК.", "НЕ ОБЪЕДИНИЛОСЬ В ЗАМОК.") },
            { "DID NOT GENERATE VALORITE SCRAPS.", Forms("НЕ СОЗДАЛ ОСКОЛКОВ ВАЛОРИТА.", "НЕ СОЗДАЛА ОСКОЛКОВ ВАЛОРИТА.", "НЕ СОЗДАЛО ОСКОЛКОВ ВАЛОРИТА.") },
            { "DOES NOT KNOW MOVE ETIQUETTE.", Forms("НЕ ЗНАЕТ ЭТИКЕТА ХОДОВ.") },
            { "DATES BACK TO THE WRINKLED AGES.", Forms("ВОСХОДИТ К ДРЕВНИМ ВРЕМЕНАМ.") },
            { "DID NOT ASCEND WHEN THEY SHOULD HAVE.", Forms("НЕ ВОЗНЁССЯ, КОГДА ДОЛЖЕН БЫЛ.", "НЕ ВОЗНЕСЛАСЬ, КОГДА ДОЛЖНА БЫЛА.", "НЕ ВОЗНЕСЛОСЬ, КОГДА ДОЛЖНО БЫЛО.") },
            { "DID NOT FLIP HORIZONTALLY.", Forms("НЕ ПЕРЕВЕРНУЛ ВЕСЬ МИР ПО ГОРИЗОНТАЛИ.", "НЕ ПЕРЕВЕРНУЛА ВЕСЬ МИР ПО ГОРИЗОНТАЛИ.", "НЕ ПЕРЕВЕРНУЛО ВЕСЬ МИР ПО ГОРИЗОНТАЛИ.") },
            { "FORGOT TO BRING A GIFT.", Forms("ЗАБЫЛ ПРИНЕСТИ ПОДАРОК.", "ЗАБЫЛА ПРИНЕСТИ ПОДАРОК.", "ЗАБЫЛО ПРИНЕСТИ ПОДАРОК.") },
            { "DID NOT ADJUST THEIR DAMAGE POWER.", Forms("НЕ УВЕЛИЧИЛ СВОЮ МОЩЬ.", "НЕ УВЕЛИЧИЛА СВОЮ МОЩЬ.", "НЕ УВЕЛИЧИЛО СВОЮ МОЩЬ.") },
            { "STEPPED TOO CLOSE TO ONE ANOTHER.", Forms("ВСТАЛ НА МЕСТО ДРУГОЙ ФИГУРЫ.", "ВСТАЛА НА МЕСТО ДРУГОЙ ФИГУРЫ.", "ВСТАЛО НА МЕСТО ДРУГОЙ ФИГУРЫ.") },
            { "DID NOT WORK OUT OF TOWN.", Forms("НЕ РАБОТАЛ ЗА ГОРОДОМ.", "НЕ РАБОТАЛА ЗА ГОРОДОМ.", "НЕ РАБОТАЛО ЗА ГОРОДОМ.") },
            { "WAS MOVED.", Forms("БЫЛ ПЕРЕМЕЩЁН.", "БЫЛА ПЕРЕМЕЩЕНА.", "БЫЛО ПЕРЕМЕЩЕНО.") },
            { "WAS NOT SLIPPERY.", Forms("НЕ БЫЛ СКОЛЬЗКИМ.", "НЕ БЫЛА СКОЛЬЗКОЙ.", "НЕ БЫЛО СКОЛЬЗКИМ.") },
            { "IS BAD AT COUNTING.", Forms("ПЛОХО СЧИТАЕТ.") },
            { "HAD AN AFFAIR.", Forms("ИМЕЛ РОМАН НА СТОРОНЕ.", "ИМЕЛА РОМАН НА СТОРОНЕ.", "ИМЕЛО РОМАН НА СТОРОНЕ.") },
            { "WAS NOT CREDITED IN THE EPILOGUE?", Forms("НЕ БЫЛ УПОМЯНУТ В ЭПИЛОГЕ?", "НЕ БЫЛА УПОМЯНУТА В ЭПИЛОГЕ?", "НЕ БЫЛО УПОМЯНУТО В ЭПИЛОГЕ?") },
            { "IS NOT EVEN TRYING?", Forms("ДАЖЕ НЕ СОБИРАЕТСЯ ПРОЧЕСТЬ ПРАВИЛА?") },
            { "DOES NOT SUSPECT THE OTHER COLOR?", Forms("НЕ ПОДОЗРЕВАЕТ ДРУГОЙ ЦВЕТ?") },
            { "DOES NOT UNDERSTAND THIS PAGE?", Forms("НЕ ПОНИМАЕТ ЭТУ СТРАНИЦУ?") },
            { "IS NOT CONTENT?", Forms("НЕ ДОВОЛЕН?", "НЕ ДОВОЛЬНА?", "НЕ ДОВОЛЬНО?") }
        };

        public static string ApplyPlural(string template, string parameterName, string value)
        {
            Regex expression = new Regex(@"\{" + Regex.Escape(parameterName) + @"\|([^|]+)\|([^|]+)\|([^}]+)\}");
            Match match = expression.Match(template);
            if (!match.Success)
                return template;

            if (!int.TryParse(value, out int number))
                return template.Replace(match.Value, value + " " + match.Groups[3].Value);

            int absolute = Math.Abs(number);
            int lastTwo = absolute % 100;
            int last = absolute % 10;
            string form = lastTwo >= 11 && lastTwo <= 19
                ? match.Groups[3].Value
                : last == 1
                    ? match.Groups[1].Value
                    : last >= 2 && last <= 4
                        ? match.Groups[2].Value
                        : match.Groups[3].Value;
            return template.Replace(match.Value, value + " " + form);
        }

        public static bool TryTranslateComposite(string source, out string result)
        {
            result = source;
            string value = source.Trim().ToUpperInvariant();
            if (value == "[ CHESS PIECE ] + [ RULE VIOLATED ]")
            {
                result = "[ ШАХМАТНАЯ ФИГУРА ] + [ НАРУШЕНО ПРАВИЛО ]";
                return true;
            }
            if (value == "[ CHESS PIECE ] ?")
            {
                result = "[ ШАХМАТНАЯ ФИГУРА ] ?";
                return true;
            }
            if (value.StartsWith("[ CHESS PIECE ]", StringComparison.Ordinal))
            {
                result = "[ ШАХМАТНАЯ ФИГУРА ] " + TranslateRule(value.Substring("[ CHESS PIECE ]".Length).Trim(), Gender.Masculine);
                return true;
            }

            Match landmine = LandmineExpression.Match(value);
            if (landmine.Success)
            {
                string rule = landmine.Groups[1].Value.Trim();
                result = rule == "+ [ RULE VIOLATED ]"
                    ? "ДАР ЗНАНИЯ + [ НАРУШЕНО ПРАВИЛО ]"
                    : "ДАР ЗНАНИЯ " + TranslateRule(rule, Gender.Masculine);
                return true;
            }

            Match piece = PieceExpression.Match(value);
            if (!piece.Success)
                return false;

            string pieceKey = piece.Groups[1].Value + " " + piece.Groups[2].Value;
            if (!Pieces.TryGetValue(pieceKey, out string translatedPiece))
                return false;

            string rest = value.Substring(piece.Length).Trim();
            result = rest == "+ [ RULE VIOLATED ]"
                ? translatedPiece + " + [ НАРУШЕНО ПРАВИЛО ]"
                : translatedPiece + " " + TranslateRule(rest, PieceGenders[piece.Groups[2].Value]);
            return true;
        }

        private static string TranslateRule(string rule, Gender gender)
        {
            if (Rules.TryGetValue(rule, out string[] forms))
                return forms[(int)gender];
            return TranslationCatalog.TryTranslateExact(rule, out string translated) ? translated.ToUpperInvariant() : rule;
        }

        private static string[] Forms(string all)
        {
            return new[] { all, all, all };
        }

        private static string[] Forms(string masculine, string feminine, string neuter)
        {
            return new[] { masculine, feminine, neuter };
        }
    }
}
