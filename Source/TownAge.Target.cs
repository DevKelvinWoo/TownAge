using UnrealBuildTool;
public class TownAgeTarget : TargetRules
{
    public TownAgeTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        ExtraModuleNames.Add("TownAge");
    }
}
