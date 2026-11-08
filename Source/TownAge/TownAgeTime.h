#pragma once
#include "CoreMinimal.h"

namespace TownAgeTime
{
    constexpr double HoursPerDay = 24.0;
    constexpr double DefaultDayMinutes = 24.0;
    inline double WrapHours(double Hours)
    {
        if (!FMath::IsFinite(Hours)) return 0.0;
        return FMath::Fmod(FMath::Fmod(Hours, HoursPerDay) + HoursPerDay, HoursPerDay);
    }
    inline double TotalHours(double EpochHours, double EpochSeconds, double Now, double DaySeconds)
    {
        if (!FMath::IsFinite(Now) || !FMath::IsFinite(EpochSeconds) || !FMath::IsFinite(DaySeconds) || DaySeconds <= 0.0)
            return EpochHours;
        return EpochHours + FMath::Max(0.0, Now - EpochSeconds) * HoursPerDay / DaySeconds;
    }
    inline FString FormatClock(double Hours)
    {
        const int32 Minutes = FMath::Clamp(FMath::FloorToInt(WrapHours(Hours) * 60.0 + 1.e-7), 0, 1439);
        return FString::Printf(TEXT("%02d:%02d"), Minutes / 60, Minutes % 60);
    }
    inline const TCHAR* PhaseName(double Hours)
    {
        const double H = WrapHours(Hours);
        if (H >= 5.0 && H < 11.0) return TEXT("Morning");
        if (H >= 11.0 && H < 17.0) return TEXT("Noon");
        if (H >= 17.0 && H < 21.0) return TEXT("Evening");
        return TEXT("Night");
    }
}
