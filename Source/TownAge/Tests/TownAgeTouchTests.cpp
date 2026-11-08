#include "../TownAgeTouch.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTownAgeInteractionTouchLayoutTest,
    "TownAge.Interaction.TouchLayout", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FTownAgeInteractionTouchLayoutTest::RunTest(const FString& Parameters)
{
    for (const FVector2D Size : { FVector2D(640, 360), FVector2D(1280, 720), FVector2D(1920, 1080), FVector2D(2340, 1080) })
    {
        const FTownAgeTouchLayout Layout(Size);
        const FString Context = FString::Printf(TEXT("%.0fx%.0f"), Size.X, Size.Y);
        TestTrue(Context + TEXT(" interaction circle stays inside left/right safe margins"),
            Layout.InteractCenter.X - Layout.InteractRadius >= Size.X * .08f - .1f &&
            Layout.InteractCenter.X + Layout.InteractRadius <= Size.X * .92f + .1f);
        TestTrue(Context + TEXT(" interaction circle stays inside vertical edges"),
            Layout.InteractCenter.Y - Layout.InteractRadius >= 0 &&
            Layout.InteractCenter.Y + Layout.InteractRadius <= Size.Y);
        TestTrue(Context + TEXT(" interaction and sprint circles do not overlap"),
            FVector2D::Distance(Layout.InteractCenter, Layout.SprintCenter) > Layout.InteractRadius + Layout.SprintRadius);
        TestTrue(Context + TEXT(" interaction and movement circles do not overlap"),
            FVector2D::Distance(Layout.InteractCenter, Layout.MoveCenter) > Layout.InteractRadius + Layout.MoveRadius);
        TestTrue(Context + TEXT(" interaction touch diameter is at least 48 screen pixels"), Layout.InteractRadius * 2 >= 48);
        TestTrue(Context + TEXT(" center is a valid interaction hit"), Layout.IsInteractButton(Layout.InteractCenter));
        TestTrue(Context + TEXT(" circle edge is a valid interaction hit"),
            Layout.IsInteractButton(Layout.InteractCenter + FVector2D(Layout.InteractRadius - .01f, 0)));
        TestFalse(Context + TEXT(" a point outside the circle is not an interaction hit"),
            Layout.IsInteractButton(Layout.InteractCenter + FVector2D(Layout.InteractRadius + 1, 0)));
        TestFalse(Context + TEXT(" sprint tap does not activate interaction"), Layout.IsInteractButton(Layout.SprintCenter));
    }
    return true;
}

#endif
