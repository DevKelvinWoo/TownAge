#include "../TownAgeDoor.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTownAgeDoorTimingTest, "TownAge.Door.Timing",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FTownAgeDoorTimingTest::RunTest(const FString& Parameters)
{
    FTownAgeDoorTiming Timing;
    TestTrue(TEXT("Approved draft timing is valid"), TownAgeDoor::IsTimingValid(Timing));
    TestEqual(TEXT("Door stays closed before contact"), TownAgeDoor::OpenFraction(.2f, Timing), 0.f);
    TestEqual(TEXT("Door stays closed exactly at contact"), TownAgeDoor::OpenFraction(Timing.DoorOpenStart, Timing), 0.f);
    TestTrue(TEXT("First push reaches 27 percent before release"), FMath::IsNearlyEqual(TownAgeDoor::OpenFraction(Timing.DoorPartOpenEnd, Timing), .27f));
    TestEqual(TEXT("Leaf is open before traversal starts"), TownAgeDoor::OpenFraction(Timing.TraverseStart, Timing), 1.f);
    TestEqual(TEXT("Open curve cannot overshoot"), TownAgeDoor::OpenFraction(100.f, Timing), 1.f);
    float Previous = 0.f;
    for (int32 Index = 0; Index <= 360; ++Index)
    {
        const float Value = TownAgeDoor::OpenFraction(Index / 100.f, Timing);
        TestTrue(TEXT("Opening is monotonic"), Value >= Previous - KINDA_SMALL_NUMBER);
        Previous = Value;
    }
    TestEqual(TEXT("Closing starts without jumping"), TownAgeDoor::SmoothFraction(0.f, 0.f, Timing.CloseDuration), 0.f);
    TestEqual(TEXT("Closing reaches its endpoint"), TownAgeDoor::SmoothFraction(Timing.CloseDuration, 0.f, Timing.CloseDuration), 1.f);
    Timing.TraverseStart = .1f;
    TestFalse(TEXT("Traversal before opening is invalid"), TownAgeDoor::IsTimingValid(Timing));
    Timing = FTownAgeDoorTiming();
    Timing.ActionDuration = 1.f;
    TestFalse(TEXT("Clip ending before crossing is invalid"), TownAgeDoor::IsTimingValid(Timing));
    Timing = FTownAgeDoorTiming();
    Timing.LoadTimeout = -1.f;
    TestFalse(TEXT("Nonpositive timeout is invalid"), TownAgeDoor::IsTimingValid(Timing));
    return true;
}
#endif
