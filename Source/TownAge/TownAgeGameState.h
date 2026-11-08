#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameStateBase.h"
#include "TownAgeGameState.generated.h"

USTRUCT()
struct FTownAgeClockSnapshot
{
    GENERATED_BODY()
    UPROPERTY() double EpochServerSeconds = 0.0;
    UPROPERTY() double EpochTotalHours = 8.0;
    UPROPERTY() double DayLengthSeconds = 1440.0;
    UPROPERTY() bool bInitialized = false;
};

UCLASS(Config=Game)
class TOWNAGE_API ATownAgeGameState : public AGameStateBase
{
    GENERATED_BODY()
public:
    ATownAgeGameState();
    virtual void BeginPlay() override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UFUNCTION(BlueprintPure, Category="TownAge|Time") double GetTimeOfDayHours() const;
    UFUNCTION(BlueprintPure, Category="TownAge|Time") double GetTotalWorldHours() const;
    UFUNCTION(BlueprintPure, Category="TownAge|Time") int32 GetDayNumber() const;
    UFUNCTION(BlueprintPure, Category="TownAge|Time") double GetDayLengthMinutes() const { return Clock.DayLengthSeconds / 60.0; }
    UFUNCTION(BlueprintPure, Category="TownAge|Time") bool IsClockReady() const { return Clock.bInitialized; }
    // These are authority-only functions, not client-callable server RPCs.
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="TownAge|Time") bool SetTimeOfDay(double Hours);
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="TownAge|Time") bool SetDayLengthMinutes(double Minutes);
protected:
    UPROPERTY(Config, EditDefaultsOnly, Category="TownAge|Time", meta=(ClampMin="0", ClampMax="23.99"))
    double StartHour = 8.0;
    UPROPERTY(Config, EditDefaultsOnly, Category="TownAge|Time", meta=(ClampMin="1", ClampMax="1440"))
    double RealMinutesPerDay = 24.0;
private:
    UPROPERTY(Replicated) FTownAgeClockSnapshot Clock;
};
