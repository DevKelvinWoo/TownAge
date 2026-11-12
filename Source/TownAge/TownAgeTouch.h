#pragma once
#include "CoreMinimal.h"

struct FTownAgePinchZoom
{
    static constexpr int32 MaxFingers = 10;
    int32 First = INDEX_NONE;
    int32 Second = INDEX_NONE;
    double PreviousDistance = 0.;

    bool Owns(int32 Finger) const { return Finger == First || Finger == Second; }

    double Update(uint16 Eligible, const FVector2D* Positions)
    {
        if (First == INDEX_NONE || Second == INDEX_NONE
            || !(Eligible & (1u << First)) || !(Eligible & (1u << Second)))
        {
            *this = FTownAgePinchZoom();
            for (int32 Finger = 0; Finger < MaxFingers; ++Finger)
            {
                if (!(Eligible & (1u << Finger))) continue;
                if (First == INDEX_NONE) First = Finger;
                else { Second = Finger; break; }
            }
            if (Second == INDEX_NONE) First = INDEX_NONE;
        }
        if (Second == INDEX_NONE) return 1.;
        const double Distance = FVector2D::Distance(Positions[First], Positions[Second]);
        const double Ratio = PreviousDistance >= 24. && Distance >= 24.
            ? FMath::Clamp(PreviousDistance / Distance, .5, 2.) : 1.;
        PreviousDistance = Distance;
        return Ratio;
    }
};

struct FTownAgeTouchLayout
{
    FVector2D MoveCenter, SprintCenter, InteractCenter;
    float MoveRadius, SprintRadius, InteractRadius, UIScale;
    explicit FTownAgeTouchLayout(FVector2D Size)
    {
        UIScale = FMath::Clamp(FMath::Min(Size.X, Size.Y) / 720.f, .55f, 2.f);
        MoveRadius = 72.f * UIScale; SprintRadius = InteractRadius = 48.f * UIScale;
        // Conservative landscape edge insets leave room for cutouts and system gestures.
        const float Edge = Size.X * .08f;
        MoveCenter = FVector2D(FMath::Max(120.f * UIScale, Edge + MoveRadius), Size.Y - 120.f * UIScale);
        SprintCenter = FVector2D(Size.X - FMath::Max(110.f * UIScale, Edge + SprintRadius), Size.Y - 120.f * UIScale);
        InteractCenter = SprintCenter - FVector2D(0, SprintRadius + InteractRadius + 16.f * UIScale);
    }
    FVector2D Movement(FVector2D Position) const
    {
        const FVector2D Delta = (Position - MoveCenter) / MoveRadius;
        return Delta.SizeSquared() < .0144f ? FVector2D::ZeroVector : Delta.GetClampedToMaxSize(1.f);
    }
    bool IsInteractButton(FVector2D Position) const
    {
        return FVector2D::DistSquared(Position, InteractCenter) <= FMath::Square(InteractRadius);
    }
};
