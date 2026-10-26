using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace KotbRussian
{
    /// <summary>
    /// Shows Russian versions of sprites that have English words drawn into them (table-of-contents links, the
    /// "OR" bridge tile) while Russian is selected, and puts the originals back for the other languages.
    /// Replacements are PNGs named after the original sprite, loaded from StreamingAssets/ru/sprites.
    /// </summary>
    internal sealed class SpriteSwapper : MonoBehaviour
    {
        private const float ScanInterval = 1f;

        private readonly Dictionary<string, Texture2D> textures = new Dictionary<string, Texture2D>();
        private readonly Dictionary<Sprite, Sprite> toRussian = new Dictionary<Sprite, Sprite>();
        private readonly Dictionary<Sprite, Sprite> toOriginal = new Dictionary<Sprite, Sprite>();

        private float nextScan;

        public static void Create(string directory)
        {
            if (!Directory.Exists(directory))
            {
                return;
            }
            var host = new GameObject("KotbRussian.SpriteSwapper");
            DontDestroyOnLoad(host);
            host.AddComponent<SpriteSwapper>().Load(directory);
        }

        private void Load(string directory)
        {
            foreach (var path in Directory.GetFiles(directory, "*.png"))
            {
                var texture = new Texture2D(2, 2, TextureFormat.RGBA32, false);
                if (texture.LoadImage(File.ReadAllBytes(path)))
                {
                    texture.name = Path.GetFileNameWithoutExtension(path);
                    textures[texture.name] = texture;
                }
            }
        }

        private void OnEnable()
        {
            SceneManager.sceneLoaded += OnSceneLoaded;
        }

        private void OnDisable()
        {
            SceneManager.sceneLoaded -= OnSceneLoaded;
        }

        private void OnSceneLoaded(Scene scene, LoadSceneMode mode)
        {
            nextScan = 0f;
        }

        private void Update()
        {
            // Polling also covers links the rulebook instantiates later and a language change in the settings menu.
            if (Time.unscaledTime >= nextScan)
            {
                nextScan = Time.unscaledTime + ScanInterval;
                SwapAll(Hooks.IsRussian);
            }
        }

        private void SwapAll(bool russian)
        {
            foreach (var renderer in Resources.FindObjectsOfTypeAll<SpriteRenderer>())
            {
                var sprite = renderer.sprite;
                if (sprite == null || !renderer.gameObject.scene.IsValid())
                {
                    continue;
                }
                var replacement = russian ? RussianFor(sprite) : OriginalFor(sprite);
                if (replacement != null)
                {
                    renderer.sprite = replacement;
                }
            }
        }

        private Sprite RussianFor(Sprite original)
        {
            if (toOriginal.ContainsKey(original))
            {
                return null;
            }
            if (toRussian.TryGetValue(original, out var cached))
            {
                return cached;
            }
            if (!textures.TryGetValue(original.name, out var texture))
            {
                return null;
            }
            texture.filterMode = original.texture.filterMode;
            var rect = original.rect;
            var pivot = new Vector2(original.pivot.x / rect.width, original.pivot.y / rect.height);
            var russian = Sprite.Create(texture, new Rect(0, 0, texture.width, texture.height), pivot,
                original.pixelsPerUnit, 0, SpriteMeshType.FullRect);
            russian.name = original.name;
            toRussian[original] = russian;
            toOriginal[russian] = original;
            return russian;
        }

        private Sprite OriginalFor(Sprite sprite)
        {
            return toOriginal.TryGetValue(sprite, out var original) ? original : null;
        }
    }
}
