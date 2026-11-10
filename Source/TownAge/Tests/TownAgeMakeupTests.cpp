#include "../TownAgeCosmeticModules.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTownAgeMakeupBoundsTest, "TownAge.Customization.MakeupBounds",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FTownAgeMakeupBoundsTest::RunTest(const FString& Parameters)
{
    FTownAgeMakeupState State;
    TestTrue(TEXT("Default no-makeup state is valid"), UTownAgeMakeupModule::Validate(State));
    State.BlushColor = 3; State.IrisColor = 4;
    State.BlushAmount = State.LinerAmount = State.IrisAmount = State.AegyoAmount = State.JawAmount = State.NoseAmount = 100;
    TestTrue(TEXT("All exact supported upper bounds are accepted"), UTownAgeMakeupModule::Validate(State));
    for (uint8 FTownAgeMakeupState::* Field : {&FTownAgeMakeupState::BlushAmount, &FTownAgeMakeupState::LinerAmount,
        &FTownAgeMakeupState::IrisAmount, &FTownAgeMakeupState::AegyoAmount, &FTownAgeMakeupState::JawAmount, &FTownAgeMakeupState::NoseAmount})
    {
        State.*Field = 101;
        TestFalse(TEXT("Every out-of-range intensity is rejected"), UTownAgeMakeupModule::Validate(State));
        State.*Field = 100;
    }
    State.BlushColor = 4;
    TestFalse(TEXT("Invalid blush palette is rejected"), UTownAgeMakeupModule::Validate(State));
    State.BlushColor = 3; State.IrisColor = 5;
    TestFalse(TEXT("Invalid iris palette is rejected"), UTownAgeMakeupModule::Validate(State));
    TestFalse(TEXT("Surgery module exposes no unimplemented mutation"), UTownAgeSurgeryModule::IsAvailable());
    TestFalse(TEXT("Unconfigured models are safe"), UTownAgeMakeupModule::SupportsMesh(nullptr));
    TestFalse(TEXT("Missing mesh cannot be mutated"), UTownAgeMakeupModule::Apply(nullptr, FTownAgeMakeupState()));
    return true;
}
#endif
