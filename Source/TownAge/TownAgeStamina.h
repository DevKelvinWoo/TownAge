#pragma once
#include "CoreMinimal.h"

// Pure state transition shared by gameplay and automation tests.
struct FTownAgeStamina
{
    float Value = 100.f;
    float RecoveryDelayRemaining = 0.f;
    bool bExhausted = false;

    void Update(float DeltaSeconds, bool bConsume)
    {
        const float Dt = FMath::Max(0.f, DeltaSeconds);
        if (bConsume && !bExhausted)
        {
            Value = FMath::Max(0.f, Value - 20.f * Dt);
            RecoveryDelayRemaining = 1.5f;
            bExhausted = Value <= 0.f;
        }
        else
        {
            const float RecoveryTime = FMath::Max(0.f, Dt - RecoveryDelayRemaining);
            RecoveryDelayRemaining = FMath::Max(0.f, RecoveryDelayRemaining - Dt);
            Value = FMath::Min(100.f, Value + 15.f * RecoveryTime);
            if (Value >= 20.f) bExhausted = false;
        }
    }
};
