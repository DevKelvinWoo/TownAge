#include "TownAgeHUD.h"
#include "TownAgePlayer.h"
#include "GameFramework/PlayerController.h"
#include "Engine/Canvas.h"
#include "InputCoreTypes.h"
#include "TownAgeTouch.h"

void ATownAgeHUD::DrawHUD()
{
    Super::DrawHUD();
    const ATownAgePlayer* Player = PlayerOwner ? Cast<ATownAgePlayer>(PlayerOwner->GetPawn()) : nullptr;
    if (!Canvas || !Player) return;
    const FTownAgeTouchLayout Layout(FVector2D(Canvas->SizeX, Canvas->SizeY));
    if (Player->UsesTouchControls())
    {
        auto Outline = [&](FVector2D C, float Radius, FLinearColor Color)
        {
            for (int32 I = 0; I < 64; ++I)
            {
                const float A = I * 2.f * PI / 64, B = (I + 1) * 2.f * PI / 64;
                DrawLine(C.X + Radius * FMath::Cos(A), C.Y + Radius * FMath::Sin(A), C.X + Radius * FMath::Cos(B), C.Y + Radius * FMath::Sin(B), Color, 3.f * Layout.UIScale);
            }
        };
        Outline(Layout.MoveCenter, Layout.MoveRadius, FLinearColor(1, 1, 1, .6f));
        Outline(Layout.MoveCenter + Player->TouchMove * Layout.MoveRadius * .7f, 23.f * Layout.UIScale, FLinearColor(1, 1, 1, .8f));
        Outline(Layout.SprintCenter, Layout.SprintRadius, Player->IsSprintControlHeld() ? FLinearColor(.62f,.86f,.28f) : FLinearColor(1,1,1,.65f));
        DrawText(TEXT("RUN"), FLinearColor::White, Layout.SprintCenter.X - 18.f * Layout.UIScale, Layout.SprintCenter.Y - 8.f * Layout.UIScale, nullptr, Layout.UIScale);
    }
    if (!Player->IsSprintControlHeld()) return;
    FVector2D Center;
    if (!PlayerOwner->ProjectWorldLocationToScreen(Player->GetActorLocation() + FVector(0, 0, 25), Center)) return;
    Center.X = FMath::Clamp(Center.X + 55.f * Layout.UIScale, 25.f * Layout.UIScale, Canvas->SizeX - 25.f * Layout.UIScale);
    constexpr int32 Segments = 96;
    const float Radius = 21.f * Layout.UIScale;
    const float Fraction = FMath::Clamp(Player->Stamina / 100.f, 0.f, 1.f);
    const FLinearColor Fill(0.62f, 0.86f, 0.28f, 1.f);
    TArray<FCanvasUVTri> Triangles;
    auto AddArc = [&](float A, float B, FLinearColor Color)
    {
        const FVector2D OuterA = Center + FVector2D(FMath::Cos(A), FMath::Sin(A)) * Radius;
        const FVector2D OuterB = Center + FVector2D(FMath::Cos(B), FMath::Sin(B)) * Radius;
        const FVector2D InnerA = Center + FVector2D(FMath::Cos(A), FMath::Sin(A)) * (Radius - 5.f * Layout.UIScale);
        const FVector2D InnerB = Center + FVector2D(FMath::Cos(B), FMath::Sin(B)) * (Radius - 5.f * Layout.UIScale);
        FCanvasUVTri T;
        T.V0_Color = T.V1_Color = T.V2_Color = Color;
        T.V0_Pos = OuterA; T.V1_Pos = OuterB; T.V2_Pos = InnerB; Triangles.Add(T);
        T.V0_Pos = OuterA; T.V1_Pos = InnerB; T.V2_Pos = InnerA; Triangles.Add(T);
    };
    for (int32 I = 0; I < Segments; ++I)
    {
        const float A = -HALF_PI + 2.f * PI * I / Segments;
        const float B = -HALF_PI + 2.f * PI * (I + 1) / Segments;
        AddArc(A, B, FLinearColor(0.08f, 0.10f, 0.06f, 1.f));
        if (float(I) / Segments < Fraction)
        {
            const float End = FMath::Min(B, -HALF_PI + 2.f * PI * Fraction);
            AddArc(A, End, Fill);
        }
    }
    Canvas->K2_DrawTriangle(nullptr, Triangles);
}
