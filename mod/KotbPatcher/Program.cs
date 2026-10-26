using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

namespace KotbPatcher;

/// <summary>
/// Redirects a handful of call sites in King of the Bridge's Assembly-CSharp.dll to KotbRussian.Hooks.
/// Usage: KotbPatcher &lt;original Assembly-CSharp.dll&gt; &lt;KotbRussian.dll&gt; &lt;output path&gt;
/// Exit code 0 on success; any missing or ambiguous call site aborts without writing.
/// </summary>
internal static class Program
{
    private const string SetText = "System.Void TMPro.TMP_Text::set_text(System.String)";

    private static int Main(string[] args)
    {
        if (args.Length != 3)
        {
            Console.Error.WriteLine("usage: KotbPatcher <Assembly-CSharp.dll> <KotbRussian.dll> <output>");
            return 2;
        }
        try
        {
            Patch(args[0], args[1], args[2]);
            return 0;
        }
        catch (PatchException e)
        {
            Console.Error.WriteLine("patch failed: " + e.Message);
            return 1;
        }
    }

    private static void Patch(string gamePath, string helperPath, string outputPath)
    {
        var resolver = new DefaultAssemblyResolver();
        resolver.AddSearchDirectory(Path.GetDirectoryName(Path.GetFullPath(gamePath)));
        resolver.AddSearchDirectory(Path.GetDirectoryName(Path.GetFullPath(helperPath)));
        var readerParams = new ReaderParameters { AssemblyResolver = resolver, InMemory = true };

        using var game = AssemblyDefinition.ReadAssembly(gamePath, readerParams);
        using var helper = AssemblyDefinition.ReadAssembly(helperPath, readerParams);
        var module = game.MainModule;
        if (module.AssemblyReferences.Any(r => r.Name == helper.Name.Name))
        {
            throw new PatchException("assembly is already patched; start from the original file");
        }

        var hooks = helper.MainModule.GetType("KotbRussian.Hooks") ?? throw new PatchException("KotbRussian.Hooks not found");
        MethodReference Hook(string name) => module.ImportReference(hooks.Methods.Single(m => m.Name == name));

        // 1. Initialise the helper as soon as the settings manager wakes up in the menu.
        var awake = FindType(module, "SettingsManager").Methods.Single(m => m.Name == "Awake");
        var il = awake.Body.GetILProcessor();
        il.InsertBefore(awake.Body.Instructions[0], il.Create(OpCodes.Call, Hook("Init")));
        Console.WriteLine("hook: SettingsManager.Awake -> Init");

        // 2. Credits time line ("It took you ...").
        Redirect(module, "OverworldTrollManager", Hook("SetCreditsTimeText"), 1,
            (method, i) => IsCall(i, SetText) && LoadsFieldBefore(i, "timeCountTextString"));

        // 3. Accusation line built from colour + piece + broken rule.
        Redirect(module, "RuleBookScreenManager", Hook("SetAccusationText"), 1,
            (method, i) => IsCall(i, SetText) && LoadsFieldBefore(i, "cheatGuessText")
                           && Previous(i).Any(p => p.OpCode == OpCodes.Callvirt || p.OpCode == OpCodes.Call
                                                   ? ((MethodReference)p.Operand).Name == "ToUpper" : false)
                           && method.Body.Instructions.Any(x => (x.OpCode == OpCodes.Callvirt || x.OpCode == OpCodes.Call)
                                                                && ((MethodReference)x.Operand).Name == "ToUpper"));

        // 4. Achievement names and descriptions come from Steam in English.
        Redirect(module, "AchievementDisplayManager", Hook("AchievementName"), 1,
            (method, i) => IsCall(i, "System.String SteamAchievements::TryGetNameOfAchievement(System.String)"));
        Redirect(module, "AchievementDisplayManager", Hook("AchievementDescription"), 1,
            (method, i) => IsCall(i, "System.String SteamAchievements::TryGetDescriptionOfAchievement(System.String)"));

        // 5. Troll dialog line, fitted before the typewriter starts.
        Redirect(module, "TrollDialogManager", Hook("SetDialogText"), 1,
            (method, i) => IsCall(i, SetText) && LoadsFieldBefore(i, "dialogString"));

        game.Write(outputPath);
        Console.WriteLine("written " + outputPath);
    }

    private static TypeDefinition FindType(ModuleDefinition module, string name)
    {
        return module.Types.SingleOrDefault(t => t.Name == name) ?? throw new PatchException("type not found: " + name);
    }

    private static IEnumerable<MethodDefinition> MethodsWithNested(TypeDefinition type)
    {
        foreach (var method in type.Methods.Where(m => m.HasBody))
        {
            yield return method;
        }
        foreach (var nested in type.NestedTypes)
        {
            foreach (var method in MethodsWithNested(nested))
            {
                yield return method;
            }
        }
    }

    private static void Redirect(ModuleDefinition module, string typeName, MethodReference hook, int expected,
                                 Func<MethodDefinition, Instruction, bool> match)
    {
        var hits = MethodsWithNested(FindType(module, typeName))
            .SelectMany(m => m.Body.Instructions.Where(i => match(m, i)).Select(i => (m, i)))
            .ToList();
        if (hits.Count != expected)
        {
            throw new PatchException($"{typeName} -> {hook.Name}: expected {expected} call site(s), found {hits.Count}");
        }
        foreach (var (method, instruction) in hits)
        {
            instruction.OpCode = OpCodes.Call;
            instruction.Operand = hook;
            Console.WriteLine($"hook: {method.DeclaringType.Name}.{method.Name} -> {hook.Name}");
        }
    }

    private static bool IsCall(Instruction i, string fullName)
    {
        return (i.OpCode == OpCodes.Callvirt || i.OpCode == OpCodes.Call)
               && i.Operand is MethodReference m && m.FullName == fullName;
    }

    /// <summary>Instructions between the previous text assignment (or method start) and this one.</summary>
    private static IEnumerable<Instruction> Previous(Instruction i)
    {
        for (var p = i.Previous; p != null && !IsCall(p, SetText); p = p.Previous)
        {
            yield return p;
        }
    }

    private static bool LoadsFieldBefore(Instruction i, string field)
    {
        return Previous(i).Any(p => (p.OpCode == OpCodes.Ldfld || p.OpCode == OpCodes.Ldsfld)
                                    && p.Operand is FieldReference f && f.Name == field);
    }
}

internal sealed class PatchException : Exception
{
    public PatchException(string message) : base(message)
    {
    }
}
