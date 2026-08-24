using System;
using HarmonyLib;
using TMPro;
using UnityEngine;
using UnityEngine.Localization;
using UnityEngine.Localization.Components;
using UnityEngine.UI;

namespace KingOfTheBridge.Russian
{
    internal static class TranslationContext
    {
        [ThreadStatic]
        private static int compositeRuleDepth;

        public static bool IsCompositeRule => compositeRuleDepth > 0;
        public static void EnterCompositeRule() => compositeRuleDepth++;
        public static void ExitCompositeRule() => compositeRuleDepth = Math.Max(0, compositeRuleDepth - 1);
    }

    [HarmonyPatch(typeof(LocalizedString), nameof(LocalizedString.GetLocalizedString), new Type[] { })]
    internal static class LocalizedStringPatch
    {
        private static void Postfix(ref string __result)
        {
            if (!TranslationContext.IsCompositeRule)
                __result = TranslationCatalog.Translate(__result, "LocalizedString");
        }
    }

    [HarmonyPatch(typeof(LocalizeStringEvent), "UpdateString")]
    internal static class LocalizeStringEventPatch
    {
        private static void Prefix(ref string value)
        {
            value = TranslationCatalog.Translate(value, "LocalizeStringEvent");
        }
    }

    [HarmonyPatch(typeof(TMP_Text), "text", MethodType.Setter)]
    internal static class TmpTextSetterPatch
    {
        private static void Prefix(ref string value)
        {
            if (TranslationContext.IsCompositeRule)
            {
                if (RussianGrammar.TryTranslateComposite(value, out string composite))
                    value = composite;
                return;
            }

            if (TranslationCatalog.TryTranslateKnown(value, out string translated))
                value = translated;
        }
    }

    [HarmonyPatch(typeof(TextMeshPro), "OnEnable")]
    internal static class TextMeshProOnEnablePatch
    {
        private static void Postfix(TextMeshPro __instance)
        {
            FontManager.Apply(__instance);
        }
    }

    [HarmonyPatch(typeof(TextMeshProUGUI), "OnEnable")]
    internal static class TextMeshProUguiOnEnablePatch
    {
        private static void Postfix(TextMeshProUGUI __instance)
        {
            FontManager.Apply(__instance);
        }
    }

    [HarmonyPatch(typeof(SpriteRenderer), "sprite", MethodType.Setter)]
    internal static class SpriteRendererPatch
    {
        private static void Prefix(SpriteRenderer __instance, ref Sprite value)
        {
            if (ImageReplacer.TryGetReplacement(__instance, value, out Sprite replacement))
                value = replacement;
        }
    }

    [HarmonyPatch(typeof(Image), "sprite", MethodType.Setter)]
    internal static class ImagePatch
    {
        private static void Prefix(Image __instance, ref Sprite value)
        {
            if (ImageReplacer.TryGetReplacement(__instance, value, out Sprite replacement))
                value = replacement;
        }
    }

    [HarmonyPatch(typeof(SteamAchievements), nameof(SteamAchievements.TryGetNameOfAchievement))]
    internal static class AchievementNamePatch
    {
        private static void Postfix(ref string __result)
        {
            __result = TranslationCatalog.Translate(__result, "Steam achievement name");
        }
    }

    [HarmonyPatch(typeof(SteamAchievements), nameof(SteamAchievements.TryGetDescriptionOfAchievement))]
    internal static class AchievementDescriptionPatch
    {
        private static void Postfix(ref string __result)
        {
            __result = TranslationCatalog.Translate(__result, "Steam achievement description");
        }
    }

    [HarmonyPatch(typeof(SettingsManager), nameof(SettingsManager.SetLocale))]
    internal static class SettingsLocalePatch
    {
        private static void Prefix(ref int localeID)
        {
            localeID = 0;
        }
    }

    [HarmonyPatch(typeof(RuleBookScreenManager), nameof(RuleBookScreenManager.Update))]
    internal static class RuleBookCompositePatch
    {
        private static void Prefix()
        {
            TranslationContext.EnterCompositeRule();
        }

        private static Exception Finalizer(Exception __exception)
        {
            TranslationContext.ExitCompositeRule();
            return __exception;
        }
    }
}
