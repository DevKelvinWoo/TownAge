#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "TownAgeStamina.h"
#include "TownAgeTouch.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTownAgeStaminaTest, "TownAge.Gameplay.Stamina", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FTownAgeStaminaTest::RunTest(const FString& Parameters)
{
    FTownAgeStamina State;
    State.Update(1.f, true);
    TestEqual(TEXT("One second sprint consumes 20"), State.Value, 80.f);
    State.Update(1.f, false);
    TestEqual(TEXT("No regeneration during recovery delay"), State.Value, 80.f);
    State.Update(1.f, false);
    TestEqual(TEXT("Only time after delay regenerates"), State.Value, 87.5f);
    State.Update(20.f, false);
    TestEqual(TEXT("Recovery clamps to full"), State.Value, 100.f);
    State.Update(10.f, true);
    TestEqual(TEXT("Drain clamps at zero"), State.Value, 0.f);
    TestTrue(TEXT("Exhaustion locks sprint"), State.bExhausted);
    State.Update(2.f, false);
    TestTrue(TEXT("Remains exhausted below 20"), State.bExhausted);
    State.Update(1.f, false);
    TestFalse(TEXT("Unlocks after recovering 20"), State.bExhausted);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTownAgeTouchTest, "TownAge.Input.TouchLayout", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FTownAgeTouchTest::RunTest(const FString& Parameters)
{
    for (FVector2D Size : {FVector2D(1280,720), FVector2D(2340,1080), FVector2D(1024,768)})
    {
        const FTownAgeTouchLayout L(Size);
        TestTrue(TEXT("Joystick stays in viewport"), L.MoveCenter.X > L.MoveRadius && L.MoveCenter.Y + L.MoveRadius < Size.Y);
        TestTrue(TEXT("Sprint button stays in viewport"), L.SprintCenter.X + L.SprintRadius < Size.X && L.SprintCenter.Y + L.SprintRadius < Size.Y);
        TestTrue(TEXT("Touch regions do not overlap"), FVector2D::Distance(L.MoveCenter,L.SprintCenter) > L.MoveRadius * 1.5f + L.SprintRadius * 1.3f);
        TestTrue(TEXT("Joystick at center is idle"), L.Movement(L.MoveCenter).IsNearlyZero());
        TestTrue(TEXT("Dragging beyond pad clamps movement"), FMath::IsNearlyEqual(L.Movement(L.MoveCenter + FVector2D(2000,2000)).Size(),1.f));
        TestTrue(TEXT("Screen-up touch has negative Y"), L.Movement(L.MoveCenter - FVector2D(0,L.MoveRadius)).Y < -.99f);
    }
    return true;
}
#endif
