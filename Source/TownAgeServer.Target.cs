using UnrealBuildTool;

[SupportedPlatforms("Win64", "Linux")]
public class TownAgeServerTarget : TargetRules
{
    public TownAgeServerTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Server;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        ExtraModuleNames.Add("TownAge");
    }
}
