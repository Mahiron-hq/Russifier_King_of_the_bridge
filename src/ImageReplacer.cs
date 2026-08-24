using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using BepInEx.Logging;
using UnityEngine;
using UnityEngine.UI;

namespace KingOfTheBridge.Russian
{
    internal static class ImageReplacer
    {
        private static readonly Dictionary<string, string> Mapping =
            new Dictionary<string, string>(StringComparer.Ordinal);
        private static readonly Dictionary<string, Texture2D> Textures =
            new Dictionary<string, Texture2D>(StringComparer.Ordinal);
        private static readonly Dictionary<Sprite, Sprite> Sprites =
            new Dictionary<Sprite, Sprite>();
        private static ManualLogSource logger;

        public static void Initialize(string mappingPath, string imageDirectory, ManualLogSource log)
        {
            Dispose();
            logger = log;
            if (!File.Exists(mappingPath))
            {
                logger.LogError($"Image mapping file not found: {mappingPath}");
                return;
            }

            foreach (string rawLine in File.ReadAllLines(mappingPath, Encoding.UTF8))
            {
                if (string.IsNullOrWhiteSpace(rawLine) || rawLine.StartsWith("#", StringComparison.Ordinal))
                    continue;
                int separator = rawLine.IndexOf('=');
                if (separator < 1)
                    continue;
                Mapping[rawLine.Substring(0, separator).Trim()] = rawLine.Substring(separator + 1).Trim();
            }

            foreach (string fileName in new HashSet<string>(Mapping.Values, StringComparer.Ordinal))
            {
                string path = Path.Combine(imageDirectory, fileName);
                if (!File.Exists(path))
                {
                    logger.LogWarning($"Mapped image not found: {path}");
                    continue;
                }

                Texture2D texture = new Texture2D(2, 2, TextureFormat.RGBA32, false);
                texture.name = Path.GetFileNameWithoutExtension(fileName) + "__ru_texture";
                if (!texture.LoadImage(File.ReadAllBytes(path), false))
                {
                    UnityEngine.Object.Destroy(texture);
                    logger.LogWarning($"Could not decode image: {path}");
                    continue;
                }
                Textures[fileName] = texture;
            }

            logger.LogInfo($"Loaded {Textures.Count}/{Mapping.Count} localized images");
        }

        public static bool TryGetReplacement(Sprite original, out Sprite replacement)
        {
            replacement = null;
            if (original == null || !Mapping.TryGetValue(original.name, out string fileName))
                return false;
            if (Sprites.TryGetValue(original, out replacement))
                return replacement != null;
            if (!Textures.TryGetValue(fileName, out Texture2D texture))
                return false;

            if (original.texture != null)
            {
                texture.filterMode = original.texture.filterMode;
                texture.wrapMode = original.texture.wrapMode;
                texture.anisoLevel = original.texture.anisoLevel;
            }

            Vector2 pivot = new Vector2(
                original.rect.width > 0f ? original.pivot.x / original.rect.width : 0.5f,
                original.rect.height > 0f ? original.pivot.y / original.rect.height : 0.5f);
            float scaleX = original.rect.width > 0f ? texture.width / original.rect.width : 1f;
            float scaleY = original.rect.height > 0f ? texture.height / original.rect.height : 1f;
            Vector4 border = new Vector4(
                original.border.x * scaleX,
                original.border.y * scaleY,
                original.border.z * scaleX,
                original.border.w * scaleY);
            replacement = Sprite.Create(
                texture,
                new Rect(0f, 0f, texture.width, texture.height),
                pivot,
                original.pixelsPerUnit,
                0,
                SpriteMeshType.FullRect,
                border);
            replacement.name = original.name + "__ru";
            Sprites[original] = replacement;
            return true;
        }

        public static bool TryGetReplacement(Component owner, Sprite original, out Sprite replacement)
        {
            replacement = null;
            if (owner != null && owner.gameObject.scene.IsValid() && owner.gameObject.scene.name == "Menu")
                return false;
            return TryGetReplacement(original, out replacement);
        }

        public static void Apply(SpriteRenderer renderer)
        {
            if (renderer != null && TryGetReplacement(renderer, renderer.sprite, out Sprite replacement))
                renderer.sprite = replacement;
        }

        public static void Apply(Image image)
        {
            if (image != null && TryGetReplacement(image, image.sprite, out Sprite replacement))
                image.sprite = replacement;
        }

        public static void ApplyToLoadedScene()
        {
            foreach (SpriteRenderer renderer in Resources.FindObjectsOfTypeAll<SpriteRenderer>())
            {
                if (renderer != null && renderer.gameObject.scene.IsValid())
                    Apply(renderer);
            }
            foreach (Image image in Resources.FindObjectsOfTypeAll<Image>())
            {
                if (image != null && image.gameObject.scene.IsValid())
                    Apply(image);
            }
        }

        public static void Dispose()
        {
            foreach (Sprite sprite in Sprites.Values)
            {
                if (sprite != null)
                    UnityEngine.Object.Destroy(sprite);
            }
            foreach (Texture2D texture in Textures.Values)
            {
                if (texture != null)
                    UnityEngine.Object.Destroy(texture);
            }
            Sprites.Clear();
            Textures.Clear();
            Mapping.Clear();
            logger = null;
        }
    }
}
