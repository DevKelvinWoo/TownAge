#include "../TownAgeInteraction.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTownAgeInteractionSelectionTest, "TownAge.Interaction.Selection",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FTownAgeInteractionSelectionTest::RunTest(const FString& Parameters)
{
    using namespace TownAgeInteraction;
    FTownAgeInteractionRow Row;
    Row.InteractionDistance = 200;
    Row.MaxVerticalDistance = 100;
    Row.MaxFacingAngleDegrees = 90;
    const FVector Origin(0, 0, 88), Forward(1, 0, 0);
    FCandidateScore Front, NearSide, Other;
    TestTrue(TEXT("Farther front target is eligible"), EvaluateCandidate(Origin, Forward, FVector(180, 0, 90), Row, Front));
    TestTrue(TEXT("Closer side target is eligible"), EvaluateCandidate(Origin, Forward, FVector(20, 60, 90), Row, NearSide));
    TestTrue(TEXT("Facing angle takes priority over distance"), IsPreferred(Front, TEXT("Far"), NearSide, TEXT("Near")));
    TestFalse(TEXT("Behind-facing target is excluded"), EvaluateCandidate(Origin, Forward, FVector(-20, 0, 90), Row, Other));
    TestFalse(TEXT("Out-of-range target is excluded"), EvaluateCandidate(Origin, Forward, FVector(201, 0, 90), Row, Other));
    TestFalse(TEXT("Other-floor target is excluded"), EvaluateCandidate(Origin, Forward, FVector(10, 0, 189), Row, Other));
    TestTrue(TEXT("Range boundary is inclusive"), EvaluateCandidate(Origin, Forward, FVector(200, 0, 90), Row, Other));
    TestTrue(TEXT("Coincident planar point is eligible"), EvaluateCandidate(Origin, Forward, FVector(0, 0, 90), Row, Other));
    TestTrue(TEXT("Coincident point scores as facing"), FMath::IsNearlyEqual(Other.FacingDot, 1.));
    TestTrue(TEXT("Same angle uses closer target"), EvaluateCandidate(Origin, Forward, FVector(90, 0, 90), Row, Other));
    TestTrue(TEXT("Distance resolves equal angles"), IsPreferred(Other, TEXT("Z"), Front, TEXT("A")));
    TestTrue(TEXT("Exact tie has stable lexical choice"), IsPreferred(Other, TEXT("A"), Other, TEXT("B")));
    TestFalse(TEXT("Exact tie does not reverse choice"), IsPreferred(Other, TEXT("B"), Other, TEXT("A")));
    TestFalse(TEXT("Zero forward vector is rejected"), EvaluateCandidate(Origin, FVector::ZeroVector, Origin, Row, Other));
    Row.InteractionDistance = -1;
    TestFalse(TEXT("Invalid data disables interaction"), EvaluateCandidate(Origin, Forward, Origin, Row, Other));
    Row.InteractionDistance = 200;
    Row.MaxFacingAngleDegrees = 181;
    TestFalse(TEXT("Invalid angle data disables interaction"), EvaluateCandidate(Origin, Forward, Origin, Row, Other));
    TestTrue(TEXT("Unrestricted targets accept every approach side"), IsApproachAllowed(FVector::ZeroVector, FVector::ZeroVector, FVector(0, -100, 0)));
    TestTrue(TEXT("Door accepts its outward approach"), IsApproachAllowed(FVector(0, 205, 90), FVector(0, 1, 0), FVector(0, 300, 88)));
    TestFalse(TEXT("Door rejects approach through house wall"), IsApproachAllowed(FVector(0, 205, 90), FVector(0, 1, 0), FVector(0, 100, 88)));
    TestTrue(TEXT("Approach boundary is inclusive"), IsApproachAllowed(FVector(0, 205, 90), FVector(0, 1, 0), FVector(20, 205, 88)));
    return true;
}
#endif
