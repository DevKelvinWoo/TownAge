#include "TownAgeHUD.h"
#include "TownAgePlayer.h"
#include "GameFramework/PlayerController.h"
#include "Engine/Canvas.h"
#include "InputCoreTypes.h"
#include "TownAgeTouch.h"
#include "Components/SkeletalMeshComponent.h"
#include "TownAgeInteraction.h"

void ATownAgeHUD::DrawHUD()
{
    Super::DrawHUD();
    const ATownAgePlayer* Player = PlayerOwner ? Cast<ATownAgePlayer>(PlayerOwner->GetPawn()) : nullptr;
    if (!Canvas || !Player) return;
    const FTownAgeTouchLayout Layout(FVector2D(Canvas->SizeX, Canvas->SizeY));
    auto Outline = [&](FVector2D C, float Radius, FLinearColor Color)
    {
        for (int32 I = 0; I < 64; ++I)
        {
            const float A = I * 2.f * PI / 64, B = (I + 1) * 2.f * PI / 64;
            DrawLine(C.X + Radius * FMath::Cos(A), C.Y + Radius * FMath::Sin(A), C.X + Radius * FMath::Cos(B), C.Y + Radius * FMath::Sin(B), Color, 3.f * Layout.UIScale);
        }
    };
    auto InteractionButton = [&](FVector2D Center, float Radius, bool bEnabled, const FString& Label)
    {
        const FLinearColor Fill = bEnabled ? FLinearColor(.25f, .44f, .20f, .95f) : FLinearColor(.13f, .15f, .13f, .65f);
        const FLinearColor Foreground = bEnabled ? FLinearColor::White : FLinearColor(.58f, .61f, .58f, .8f);
        TArray<FCanvasUVTri> Disc;
        Disc.Reserve(64);
        for (int32 I = 0; I < 64; ++I)
        {
            const float A = I * 2.f * PI / 64, B = (I + 1) * 2.f * PI / 64;
            FCanvasUVTri Triangle;
            Triangle.V0_Pos = Center;
            Triangle.V1_Pos = Center + FVector2D(FMath::Cos(A), FMath::Sin(A)) * Radius;
            Triangle.V2_Pos = Center + FVector2D(FMath::Cos(B), FMath::Sin(B)) * Radius;
            Triangle.V0_Color = Triangle.V1_Color = Triangle.V2_Color = Fill;
            Disc.Add(Triangle);
        }
        Canvas->K2_DrawTriangle(nullptr, Disc);
        Outline(Center, Radius, Foreground);
        float Width, Height;
        GetTextSize(Label, Width, Height, nullptr, Layout.UIScale);
        DrawText(Label, Foreground, Center.X - Width * .5f, Center.Y - Height * .5f, nullptr, Layout.UIScale);
    };
    const UTownAgeInteractionComponent* Interaction = Player->GetInteractionComponent();
    const bool bCanInteract = Interaction && Interaction->HasInteractable();
    if (Player->UsesTouchControls())
    {
        Outline(Layout.MoveCenter, Layout.MoveRadius, FLinearColor(1, 1, 1, .6f));
        Outline(Layout.MoveCenter + Player->TouchMove * Layout.MoveRadius * .7f, 23.f * Layout.UIScale, FLinearColor(1, 1, 1, .8f));
        Outline(Layout.SprintCenter, Layout.SprintRadius, Player->IsSprintControlHeld() ? FLinearColor(.62f,.86f,.28f) : FLinearColor(1,1,1,.65f));
        DrawText(TEXT("RUN"), FLinearColor::White, Layout.SprintCenter.X - 18.f * Layout.UIScale, Layout.SprintCenter.Y - 8.f * Layout.UIScale, nullptr, Layout.UIScale);
        InteractionButton(Layout.InteractCenter, Layout.InteractRadius, bCanInteract, TEXT("USE"));
    }
    else if (bCanInteract)
    {
        FVector2D PromptCenter;
        if (PlayerOwner->ProjectWorldLocationToScreen(Interaction->GetSelectedTarget()->GetInteractionPoint() + FVector(0, 0, 35), PromptCenter, true))
        {
            const float Radius = 25.f * Layout.UIScale;
            const float Margin = 8.f * Layout.UIScale;
            if (PromptCenter.X - Radius >= Margin && PromptCenter.X + Radius <= Canvas->SizeX - Margin &&
                PromptCenter.Y - Radius >= Margin && PromptCenter.Y + Radius <= Canvas->SizeY - Margin)
            {
                InteractionButton(PromptCenter, Radius, true, TEXT("G"));
                const FString Prompt = Interaction->GetPrompt().ToString();
                float Width, Height;
                GetTextSize(Prompt, Width, Height, nullptr, Layout.UIScale);
                DrawText(Prompt, FLinearColor::White, PromptCenter.X - Width * .5f, PromptCenter.Y + Radius + 5.f * Layout.UIScale, nullptr, Layout.UIScale);
            }
        }
    }
    if (!Player->IsSprintControlHeld() || Player->IsDoorBusy()) return;
    FVector2D Center;
    if (!PlayerOwner->ProjectWorldLocationToScreen(Player->GetActorLocation() + FVector(0, 0, 25), Center, true)) return;
    const float Radius = 16.f * Layout.UIScale;
    const float Gap = 12.f * Layout.UIScale;
    const float Margin = 8.f * Layout.UIScale;
    // Use the visible mesh bounds, including the wide hair, instead of a fixed offset.
    const FBox Bounds = Player->GetMesh()->Bounds.GetBox();
    float Left = TNumericLimits<float>::Max();
    float Right = TNumericLimits<float>::Lowest();
    for (int32 Corner = 0; Corner < 8; ++Corner)
    {
        const FVector Point((Corner & 1) ? Bounds.Max.X : Bounds.Min.X,
                            (Corner & 2) ? Bounds.Max.Y : Bounds.Min.Y,
                            (Corner & 4) ? Bounds.Max.Z : Bounds.Min.Z);
        FVector2D Screen;
        if (!PlayerOwner->ProjectWorldLocationToScreen(Point, Screen, true)) return;
        Left = FMath::Min(Left, float(Screen.X));
        Right = FMath::Max(Right, float(Screen.X));
    }
    const float RightCenter = Right + Gap + Radius;
    const float LeftCenter = Left - Gap - Radius;
    if (RightCenter - Radius >= Margin && RightCenter + Radius <= Canvas->SizeX - Margin)
        Center.X = RightCenter;
    else if (LeftCenter - Radius >= Margin && LeftCenter + Radius <= Canvas->SizeX - Margin)
        Center.X = LeftCenter;
    else
        return; // Avoid clamping the ring back over the character at a screen edge.
    Center.Y = FMath::Clamp(Center.Y, double(Margin + Radius), double(Canvas->SizeY - Margin - Radius));
    constexpr int32 Segments = 96;
    const float Fraction = FMath::Clamp(Player->Stamina / 100.f, 0.f, 1.f);
    const FLinearColor Fill(0.62f, 0.86f, 0.28f, 1.f);
    TArray<FCanvasUVTri> Triangles;
    auto AddArc = [&](float A, float B, FLinearColor Color)
    {
        const FVector2D OuterA = Center + FVector2D(FMath::Cos(A), FMath::Sin(A)) * Radius;
        const FVector2D OuterB = Center + FVector2D(FMath::Cos(B), FMath::Sin(B)) * Radius;
        const FVector2D InnerA = Center + FVector2D(FMath::Cos(A), FMath::Sin(A)) * (Radius - 4.f * Layout.UIScale);
        const FVector2D InnerB = Center + FVector2D(FMath::Cos(B), FMath::Sin(B)) * (Radius - 4.f * Layout.UIScale);
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
