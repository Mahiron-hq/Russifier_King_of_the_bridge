using System.Collections;
using System.IO;
using BepInEx;
using BepInEx.Configuration;
using HarmonyLib;
using UnityEngine.SceneManagement;

namespace KingOfTheBridge.Russian
{
    [BepInPlugin(PluginId, PluginName, PluginVersion)]
    public sealed class RussianTranslationPlugin : BaseUnityPlugin
    {
        public const string PluginId = "ru.translation.kingofthebridge";
        public const string PluginName = "King of the Bridge Russian Translation";
        public const string PluginVersion = "1.0.0";

        private Harmony harmony;
        private string pluginDirectory;

        private void Awake()
        {
            pluginDirectory = Path.GetDirectoryName(Info.Location);
            ConfigEntry<bool> logUntranslated = Config.Bind(
                "Diagnostics",
                "LogUntranslated",
                true,
                "Write strings not covered by translation.txt to untranslated.txt.");

            UntranslatedLog.Initialize(
                Path.Combine(pluginDirectory, "untranslated.txt"),
                logUntranslated.Value,
                Logger);
            TranslationCatalog.Load(Path.Combine(pluginDirectory, "translation.txt"), Logger);
            ImageReplacer.Initialize(
                Path.Combine(pluginDirectory, "image_mapping.txt"),
                Path.Combine(pluginDirectory, "images"),
                Logger);
            FontManager.Initialize(
                Path.Combine(pluginDirectory, "alagard-unicode-tmp"),
                Logger);

            harmony = new Harmony(PluginId);
            harmony.PatchAll();
            SceneManager.sceneLoaded += OnSceneLoaded;
            ApplyToLoadedScene();
            StartCoroutine(FlushDiagnosticsPeriodically());
            Logger.LogInfo($"{PluginName} {PluginVersion} loaded");
        }

        private void OnSceneLoaded(Scene scene, LoadSceneMode mode)
        {
            StartCoroutine(ApplyAfterSceneLoad());
            UntranslatedLog.Flush();
        }

        private IEnumerator ApplyAfterSceneLoad()
        {
            yield return null;
            ApplyToLoadedScene();
        }

        private static void ApplyToLoadedScene()
        {
            FontManager.ApplyToLoadedScene();
            ImageReplacer.ApplyToLoadedScene();
        }

        private static IEnumerator FlushDiagnosticsPeriodically()
        {
            while (true)
            {
                yield return new UnityEngine.WaitForSeconds(30f);
                UntranslatedLog.Flush();
            }
        }

        private void OnDestroy()
        {
            SceneManager.sceneLoaded -= OnSceneLoaded;
            UntranslatedLog.Flush();
            harmony?.UnpatchSelf();
            ImageReplacer.Dispose();
            FontManager.Dispose();
        }
    }
}
