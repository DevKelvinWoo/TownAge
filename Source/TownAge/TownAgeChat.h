#pragma once
#include "CoreMinimal.h"

namespace TownAgeChat
{
    constexpr int32 MaxLength = 200;
    constexpr int32 HistoryLimit = 80;
    inline FString Sanitize(const FString& Text, int32 Limit = MaxLength)
    {
        FString Result;
        for (int32 I = 0; I < Text.Len() && Result.Len() < Limit; ++I)
        {
            const TCHAR C = Text[I];
            if (C < 32 || (C >= 127 && C <= 159)) { Result += TEXT(' '); continue; }
            // Disallow directional overrides; chat is plain text, never rich markup.
            if ((C >= 0x202A && C <= 0x202E) || (C >= 0x2066 && C <= 0x2069)) continue;
            if (C >= 0xD800 && C <= 0xDBFF)
            {
                if (I + 1 < Text.Len() && Text[I + 1] >= 0xDC00 && Text[I + 1] <= 0xDFFF && Result.Len() + 2 <= Limit)
                { Result += C; Result += Text[++I]; }
                continue;
            }
            if (C >= 0xDC00 && C <= 0xDFFF) continue;
            Result += C;
        }
        return Result.TrimStartAndEnd();
    }
    inline bool CanSend(double Now, double LastSent) { return Now - LastSent >= 1.0; }
}
