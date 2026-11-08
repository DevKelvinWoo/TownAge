using UnrealBuildTool;

public class TownAgeMapEditor : ModuleRules
{
    public TownAgeMapEditor(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "TownAge" });
        PrivateDependencyModuleNames.AddRange(new[] {
            "UnrealEd", "Slate", "SlateCore", "InputCore", "LevelEditor", "ToolMenus",
            "EditorFramework", "DesktopPlatform", "Projects", "ApplicationCore"
        });
    }
}
