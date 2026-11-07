using UnrealBuildTool;
public class TownAgeEditorTarget : TargetRules
{
    public TownAgeEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        ExtraModuleNames.Add("TownAge");
    }
}
