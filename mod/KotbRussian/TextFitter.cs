using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace KotbRussian
{
    /// <summary>
    /// Makes TextMeshPro labels shrink to fit their box instead of wrapping onto lines the layout has no room for.
    /// The original font size stays the upper bound, so text that already fits is unchanged.
    /// </summary>
    internal sealed class TextFitter : MonoBehaviour
    {
        private const float MinSizeRatio = 0.5f;
        private const float ScanInterval = 0.5f;
        // Longer text in a one-line box is a paragraph the game lets overflow on purpose (e.g. the speedrun note).
        private const int ParagraphLength = 80;

        private static readonly HashSet<int> Fitted = new HashSet<int>();

        private float nextScan;

        public static void Create()
        {
            var host = new GameObject("KotbRussian.TextFitter");
            DontDestroyOnLoad(host);
            host.AddComponent<TextFitter>();
        }

        private void OnEnable()
        {
            SceneManager.sceneLoaded += OnSceneLoaded;
            FitAll();
        }

        private void OnDisable()
        {
            SceneManager.sceneLoaded -= OnSceneLoaded;
        }

        private void OnSceneLoaded(Scene scene, LoadSceneMode mode)
        {
            Fitted.Clear();
            FitAll();
        }

        private void Update()
        {
            // Covers prefabs the game instantiates after a scene has loaded.
            if (Time.unscaledTime >= nextScan)
            {
                nextScan = Time.unscaledTime + ScanInterval;
                FitAll();
            }
        }

        private static void FitAll()
        {
            foreach (var text in Resources.FindObjectsOfTypeAll<TMP_Text>())
            {
                if (text != null && text.gameObject.scene.IsValid())
                {
                    Fit(text);
                }
            }
        }

        /// <summary>
        /// Enables auto-size once per text component. Short labels in boxes too low for two lines stop wrapping and
        /// shrink to the box width instead; paragraphs in such boxes keep the game's own overflow layout.
        /// </summary>
        public static void Fit(TMP_Text text)
        {
            if (!Fitted.Add(text.GetInstanceID()) || text.enableAutoSizing || text.font == null)
            {
                return;
            }
            float size = text.fontSize;
            if (text.enableWordWrapping)
            {
                var face = text.font.faceInfo;
                float lineHeight = face.lineHeight * size / face.pointSize;
                if (text.rectTransform.rect.height < lineHeight * 1.8f)
                {
                    if (text.text != null && text.text.Length > ParagraphLength)
                    {
                        return;
                    }
                    text.enableWordWrapping = false;
                }
            }
            text.fontSizeMax = size;
            text.fontSizeMin = size * MinSizeRatio;
            text.enableAutoSizing = true;
        }
    }
}
