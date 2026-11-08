#include "../TownAgeChat.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTownAgeChatRulesTest, "TownAge.Chat.Rules",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FTownAgeChatRulesTest::RunTest(const FString& Parameters)
{
    TestEqual(TEXT("Whitespace-only messages are empty"), TownAgeChat::Sanitize(TEXT(" \r\n\t ")), FString());
    TestEqual(TEXT("Controls cannot forge new chat rows"), TownAgeChat::Sanitize(TEXT("  hello\r\nworld\t ")), FString(TEXT("hello  world")));
    TestEqual(TEXT("Korean survives sanitation"), TownAgeChat::Sanitize(TEXT("  안녕하세요 마을 친구들  ")), FString(TEXT("안녕하세요 마을 친구들")));
    TestEqual(TEXT("Rich text remains literal"), TownAgeChat::Sanitize(TEXT("<b>hello</>")), FString(TEXT("<b>hello</>")));
    TestEqual(TEXT("Body is bounded"), TownAgeChat::Sanitize(FString::ChrN(220, TEXT('a'))).Len(), 200);
    TestEqual(TEXT("Name is bounded separately"), TownAgeChat::Sanitize(FString::ChrN(60, TEXT('a')), 32).Len(), 32);
    TestEqual(TEXT("Directional override removed"), TownAgeChat::Sanitize(FString(TEXT("a")) + TCHAR(0x202E) + TEXT("b")), FString(TEXT("ab")));
    FString Pair; Pair += TCHAR(0xD83D); Pair += TCHAR(0xDE00);
    TestEqual(TEXT("Emoji pair survives"), TownAgeChat::Sanitize(Pair), Pair);
    TestEqual(TEXT("Emoji pair is not split at boundary"), TownAgeChat::Sanitize(FString::ChrN(199, TEXT('a')) + Pair).Len(), 199);
    TestEqual(TEXT("Lone low surrogate removed"), TownAgeChat::Sanitize(FString::ChrN(1, TCHAR(0xDE00))), FString());
    TestTrue(TEXT("First message accepted"), TownAgeChat::CanSend(0, -DBL_MAX));
    TestFalse(TEXT("Burst rejected"), TownAgeChat::CanSend(5.99, 5));
    TestTrue(TEXT("Exact cooldown boundary accepted"), TownAgeChat::CanSend(6, 5));
    return true;
}
#endif
