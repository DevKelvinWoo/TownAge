using UnrealBuildTool;
public class TownAge : ModuleRules
{
    public TownAge(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore" });
        PublicDependencyModuleNames.Add("UMG");
        PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });
    }
}
