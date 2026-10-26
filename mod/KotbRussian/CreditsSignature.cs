using System.Collections;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace KotbRussian
{
    /// <summary>
    /// Adds the translator's signature to the bottom-right corner of the Credits scene while the last card
    /// (the thanks for playing) is shown, and keeps that card on screen longer. Russian only.
    /// </summary>
    internal sealed class CreditsSignature : MonoBehaviour
    {
        private const string Signature = "Перевёл игру ваш любимый Mahiron";
        private const float Delay = 1f;
        private const float FadeTime = 1f;
        private const float LastCardTime = 7f;
        private const float PauseBeforeMenu = 2f;
        private const float SizeRatio = 1.25f;
        private const float Margin = 24f;

        public static void Create()
        {
            var host = new GameObject("KotbRussian.CreditsSignature");
            DontDestroyOnLoad(host);
            host.AddComponent<CreditsSignature>();
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
            if (scene.name == "Credits")
            {
                StartCoroutine(ShowWithLastCard());
            }
        }

        private IEnumerator ShowWithLastCard()
        {
            // CreditsManager.Start runs after sceneLoaded, so wait a frame for its fields to be in use.
            yield return null;
            var manager = FindObjectOfType<CreditsManager>();
            if (manager == null || manager.creditsText == null || manager.creditsList == null || manager.creditsList.Count == 0)
            {
                yield break;
            }
            var card = manager.creditsText;
            string lastCard = manager.creditsList[manager.creditsList.Count - 1].GetLocalizedString();
            while (card != null && !(card.gameObject.activeInHierarchy && card.text == lastCard))
            {
                yield return null;
            }
            if (card == null || !Hooks.IsRussian)
            {
                yield break;
            }

            // The game's own coroutine hides the last card after 4 seconds; from here on this one runs the ending.
            manager.StopAllCoroutines();
            float shownAt = Time.time;
            yield return new WaitForSeconds(Delay);
            if (card == null)
            {
                yield break;
            }

            var signature = Build(card);
            for (float t = 0f; t < FadeTime && signature != null; t += Time.deltaTime)
            {
                signature.alpha = t / FadeTime;
                yield return null;
            }
            if (signature != null)
            {
                signature.alpha = 1f;
            }

            yield return new WaitForSeconds(Mathf.Max(0f, LastCardTime - (Time.time - shownAt)));
            if (card != null)
            {
                card.gameObject.SetActive(false);
            }
            if (signature != null)
            {
                Destroy(signature.gameObject);
            }
            yield return new WaitForSeconds(PauseBeforeMenu);
            SceneManager.LoadScene("Menu");
        }

        private static TextMeshProUGUI Build(TMP_Text source)
        {
            var canvas = source.canvas != null ? source.canvas.rootCanvas.transform : source.transform.parent;
            var host = new GameObject("RussianTranslationCredit", typeof(RectTransform));
            host.transform.SetParent(canvas, false);

            var rect = (RectTransform)host.transform;
            rect.anchorMin = rect.anchorMax = rect.pivot = new Vector2(1f, 0f);
            rect.anchoredPosition = new Vector2(-Margin, Margin);
            rect.sizeDelta = new Vector2(1800f, source.fontSize * SizeRatio * 2f);

            var text = host.AddComponent<TextMeshProUGUI>();
            text.font = source.font;
            text.fontSharedMaterial = source.fontSharedMaterial;
            text.fontStyle = source.fontStyle;
            text.fontSize = source.fontSize * SizeRatio;
            text.color = source.color;
            text.enableWordWrapping = false;
            text.alignment = TextAlignmentOptions.BottomRight;
            text.raycastTarget = false;
            text.text = Signature;
            text.alpha = 0f;
            return text;
        }
    }
}
