namespace BepInEx.Logging
{
    internal sealed class ManualLogSource
    {
        public int LoadedCount { get; private set; }

        public void LogInfo(object value)
        {
            if (value is string message && message.StartsWith("Loaded "))
                LoadedCount++;
        }

        public void LogWarning(object value)
        {
        }

        public void LogError(object value)
        {
        }
    }
}

namespace KingOfTheBridge.Russian
{
    internal static class UntranslatedLog
    {
        public static void Register(string source, string origin)
        {
        }
    }
}
