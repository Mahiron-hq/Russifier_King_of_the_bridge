using System.Collections.Generic;
using BepInEx.Logging;
using TMPro;
using UnityEngine;

namespace KingOfTheBridge.Russian
{
    internal static class FontManager
    {
        private static readonly HashSet<TMP_FontAsset> ModifiedFonts = new HashSet<TMP_FontAsset>();
        private static TMP_FontAsset fallbackFont;
        private static AssetBundle fontBundle;

        public static void Initialize(string bundlePath, ManualLogSource logger)
        {
            fontBundle = AssetBundle.LoadFromFile(bundlePath);
            if (fontBundle == null)
            {
                logger.LogError($"Font bundle could not be loaded: {bundlePath}");
                return;
            }

            TMP_FontAsset[] fonts = fontBundle.LoadAllAssets<TMP_FontAsset>();
            if (fonts.Length == 0)
            {
                logger.LogError("The font bundle contains no TMP_FontAsset");
                fontBundle.Unload(true);
                fontBundle = null;
                return;
            }

            fallbackFont = fonts[0];
            logger.LogInfo($"Loaded Cyrillic fallback font: {fallbackFont.name}");
        }

        public static void Apply(TMP_Text text)
        {
            if (fallbackFont == null || text == null)
                return;

            TMP_FontAsset originalFont = text.font;
            if (originalFont == null)
            {
                text.font = fallbackFont;
                return;
            }
            if (originalFont == fallbackFont || ModifiedFonts.Contains(originalFont))
                return;

            List<TMP_FontAsset> fallbacks = originalFont.fallbackFontAssetTable;
            if (fallbacks == null)
            {
                fallbacks = new List<TMP_FontAsset>();
                originalFont.fallbackFontAssetTable = fallbacks;
            }
            if (!fallbacks.Contains(fallbackFont))
                fallbacks.Add(fallbackFont);
            ModifiedFonts.Add(originalFont);
        }

        public static void ApplyToLoadedScene()
        {
            foreach (TMP_Text text in Resources.FindObjectsOfTypeAll<TMP_Text>())
            {
                if (text != null && text.gameObject.scene.IsValid())
                    Apply(text);
            }
        }

        public static void Dispose()
        {
            foreach (TMP_FontAsset font in ModifiedFonts)
                font?.fallbackFontAssetTable?.Remove(fallbackFont);
            ModifiedFonts.Clear();
            fallbackFont = null;
            if (fontBundle != null)
                fontBundle.Unload(true);
            fontBundle = null;
        }
    }
}
