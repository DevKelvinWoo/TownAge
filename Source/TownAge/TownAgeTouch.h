#pragma once
#include "CoreMinimal.h"

struct FTownAgeTouchLayout
{
    FVector2D MoveCenter, SprintCenter;
    float MoveRadius, SprintRadius, UIScale;
    explicit FTownAgeTouchLayout(FVector2D Size)
    {
        UIScale = FMath::Clamp(FMath::Min(Size.X, Size.Y) / 720.f, .55f, 2.f);
        MoveRadius = 72.f * UIScale; SprintRadius = 48.f * UIScale;
        // Conservative landscape edge insets leave room for cutouts and system gestures.
        const float Edge = Size.X * .08f;
        MoveCenter = FVector2D(FMath::Max(120.f * UIScale, Edge + MoveRadius), Size.Y - 120.f * UIScale);
        SprintCenter = FVector2D(Size.X - FMath::Max(110.f * UIScale, Edge + SprintRadius), Size.Y - 120.f * UIScale);
    }
    FVector2D Movement(FVector2D Position) const
    {
        const FVector2D Delta = (Position - MoveCenter) / MoveRadius;
        return Delta.SizeSquared() < .0144f ? FVector2D::ZeroVector : Delta.GetClampedToMaxSize(1.f);
    }
};
