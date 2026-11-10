#include "../TownAgeAppearance.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTownAgeHairPaletteTest, "TownAge.Customization.HairPalette",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FTownAgeHairPaletteTest::RunTest(const FString& Parameters)
{
    for (uint8 Index = 0; Index <= 4; ++Index)
    {
        TestTrue(TEXT("Original and four supported dyes are valid"), TownAgeAppearance::IsValidHairColor(Index));
        const FLinearColor Color = TownAgeAppearance::HairColor(Index);
        TestTrue(TEXT("Dye colors remain finite and opaque"), Color.A == 1.f && !Color.Equals(FLinearColor::Transparent));
    }
    for (int32 Index = 5; Index <= 255; ++Index)
        TestFalse(TEXT("Unsupported network palette indices are rejected"), TownAgeAppearance::IsValidHairColor(uint8(Index)));
    const FLinearColor Red = TownAgeAppearance::HairColor(1);
    const FLinearColor Blue = TownAgeAppearance::HairColor(2);
    const FLinearColor Green = TownAgeAppearance::HairColor(3);
    const FLinearColor Yellow = TownAgeAppearance::HairColor(4);
    TestTrue(TEXT("Red chip is red dominant"), Red.R > Red.G && Red.R > Red.B);
    TestTrue(TEXT("Blue chip is blue dominant"), Blue.B > Blue.R && Blue.B > Blue.G);
    TestTrue(TEXT("Green chip is green dominant"), Green.G > Green.R && Green.G > Green.B);
    TestTrue(TEXT("Yellow chip combines red and green"), Yellow.R > .5f && Yellow.G > .5f && Yellow.B < .1f);
    TestFalse(TEXT("Missing meshes fail safely"), TownAgeAppearance::ApplyHairColor(nullptr, 1));
    return true;
}
#endif
