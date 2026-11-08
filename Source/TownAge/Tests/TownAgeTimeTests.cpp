#include "../TownAgeTime.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTownAgeTimeTest, "TownAge.Time.Clock",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FTownAgeTimeTest::RunTest(const FString& Parameters)
{
    using namespace TownAgeTime;
    TestEqual(TEXT("Default one real second is one game minute"), TotalHours(8, 0, 60, 1440), 9.0);
    TestEqual(TEXT("Default full day takes 24 minutes"), TotalHours(8, 0, 1440, 1440), 32.0);
    TestEqual(TEXT("Midnight wraps without losing day count"), FormatClock(TotalHours(23, 0, 120, 1440)), FString(TEXT("01:00")));
    TestEqual(TEXT("Multi-day elapsed time is retained"), TotalHours(8, 10, 2890, 1440), 56.0);
    TestEqual(TEXT("Future epoch does not run backwards"), TotalHours(8, 10, 9, 1440), 8.0);
    TestEqual(TEXT("Invalid duration cannot divide by zero"), TotalHours(8, 0, 10, 0), 8.0);
    TestEqual(TEXT("Negative hours normalize"), WrapHours(-1), 23.0);
    TestEqual(TEXT("Minute boundary formats correctly"), FormatClock(8.0 + 1.0 / 60.0), FString(TEXT("08:01")));
    TestEqual(TEXT("No premature midnight rounding"), FormatClock(23.999), FString(TEXT("23:59")));
    TestEqual(TEXT("Midnight displays as 00:00"), FormatClock(24), FString(TEXT("00:00")));
    const double Before = TotalHours(8, 0, 75, 1440);
    TestEqual(TEXT("Changing speed keeps the current time"), TotalHours(Before, 75, 75, 720), Before);
    TestEqual(TEXT("New speed applies after rebasing"), TotalHours(Before, 75, 105, 720), Before + 1.0);
    TestEqual(TEXT("Late join evaluates the authority epoch"), FormatClock(TotalHours(8, 100, 400, 1440)), FString(TEXT("13:00")));
    TestEqual(TEXT("Morning boundary"), FString(PhaseName(5)), FString(TEXT("Morning")));
    TestEqual(TEXT("Noon boundary"), FString(PhaseName(11)), FString(TEXT("Noon")));
    TestEqual(TEXT("Evening boundary"), FString(PhaseName(17)), FString(TEXT("Evening")));
    TestEqual(TEXT("Night boundary"), FString(PhaseName(21)), FString(TEXT("Night")));
    return true;
}
#endif
