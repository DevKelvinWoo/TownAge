#include "TownAgeGameState.h"
#include "TownAgeTime.h"
#include "TownAgeTimeSky.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

ATownAgeGameState::ATownAgeGameState()
{
    ServerWorldTimeSecondsUpdateFrequency = 2.f;
}

void ATownAgeGameState::BeginPlay()
{
    Super::BeginPlay();
    if (HasAuthority())
    {
        double InitialHour = StartHour, DayMinutes = RealMinutesPerDay;
#if !UE_BUILD_SHIPPING
        // Authority-only development overrides for full-cycle and join-in-progress QA.
        FParse::Value(FCommandLine::Get(), TEXT("TownAgeStartHour="), InitialHour);
        FParse::Value(FCommandLine::Get(), TEXT("TownAgeDayMinutes="), DayMinutes);
#endif
        Clock.EpochServerSeconds = GetServerWorldTimeSeconds();
        Clock.EpochTotalHours = TownAgeTime::WrapHours(InitialHour);
        Clock.DayLengthSeconds = (FMath::IsFinite(DayMinutes) ? FMath::Clamp(DayMinutes, 1.0, 1440.0) : TownAgeTime::DefaultDayMinutes) * 60.0;
        Clock.bInitialized = true;
        ForceNetUpdate();
    }
    if (GetNetMode() != NM_DedicatedServer)
    {
        FActorSpawnParameters Params;
        Params.Owner = this;
        Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        GetWorld()->SpawnActor<ATownAgeTimeSky>(ATownAgeTimeSky::StaticClass(), FTransform::Identity, Params);
    }
}

double ATownAgeGameState::GetTotalWorldHours() const
{
    return TownAgeTime::TotalHours(Clock.EpochTotalHours, Clock.EpochServerSeconds, GetServerWorldTimeSeconds(), Clock.DayLengthSeconds);
}

double ATownAgeGameState::GetTimeOfDayHours() const { return TownAgeTime::WrapHours(GetTotalWorldHours()); }
int32 ATownAgeGameState::GetDayNumber() const { return FMath::FloorToInt(GetTotalWorldHours() / 24.0) + 1; }

bool ATownAgeGameState::SetTimeOfDay(double Hours)
{
    if (!HasAuthority() || !Clock.bInitialized || !FMath::IsFinite(Hours)) return false;
    const double Day = FMath::FloorToDouble(GetTotalWorldHours() / 24.0);
    Clock.EpochTotalHours = Day * 24.0 + TownAgeTime::WrapHours(Hours);
    Clock.EpochServerSeconds = GetServerWorldTimeSeconds();
    ForceNetUpdate();
    return true;
}

bool ATownAgeGameState::SetDayLengthMinutes(double Minutes)
{
    if (!HasAuthority() || !Clock.bInitialized || !FMath::IsFinite(Minutes) || Minutes < 1.0 || Minutes > 1440.0) return false;
    Clock.EpochTotalHours = GetTotalWorldHours();
    Clock.EpochServerSeconds = GetServerWorldTimeSeconds();
    Clock.DayLengthSeconds = Minutes * 60.0;
    ForceNetUpdate();
    return true;
}

void ATownAgeGameState::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ATownAgeGameState, Clock);
}
