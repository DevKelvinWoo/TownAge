#include "TownAgeLightingPreviewWidget.h"

#include "TownAgePlayerController.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/SafeZone.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "InputCoreTypes.h"

void UTownAgeLightingPreviewWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(true);
    SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    auto* SafeArea = WidgetTree->ConstructWidget<USafeZone>();
    SafeArea->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    WidgetTree->RootWidget = SafeArea;
    auto* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>();
    Canvas->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    SafeArea->AddChild(Canvas);
    auto* Background = WidgetTree->ConstructWidget<UBorder>();
    Background->SetBrushColor(FLinearColor(.035f, .062f, .048f, .96f));
    Background->SetPadding(FMargin(12.f));
    auto* PanelSlot = Canvas->AddChildToCanvas(Background);
    PanelSlot->SetAnchors(FAnchors(1.f, 0.f));
    PanelSlot->SetAlignment(FVector2D(1.f, 0.f));
    PanelSlot->SetPosition(FVector2D(-18.f, 18.f));
    PanelSlot->SetAutoSize(true);
    auto* Rows = WidgetTree->ConstructWidget<UVerticalBox>();
    Background->SetContent(Rows);

    auto Label = [&](const FText& Text, int32 Size)
    {
        auto* Widget = WidgetTree->ConstructWidget<UTextBlock>();
        Widget->SetText(Text);
        Widget->SetColorAndOpacity(FSlateColor(FLinearColor(.96f, .94f, .86f)));
        auto Font = Widget->GetFont();
        Font.Size = Size;
        Widget->SetFont(Font);
        return Widget;
    };
    Rows->AddChildToVerticalBox(Label(NSLOCTEXT("TownAge", "LightingPreviewTitle", "조명 테스트"), 18))
        ->SetPadding(FMargin(2.f, 0.f, 2.f, 8.f));
    auto AddButton = [&](const FText& Text, const FLinearColor& Tint)
    {
        auto* Button = WidgetTree->ConstructWidget<UButton>();
        Button->SetBackgroundColor(Tint);
        Button->SetContent(Label(Text, 14));
        auto* Size = WidgetTree->ConstructWidget<USizeBox>();
        Size->SetMinDesiredWidth(152.f);
        Size->SetMinDesiredHeight(44.f);
        Size->SetContent(Button);
        Rows->AddChildToVerticalBox(Size)->SetPadding(FMargin(0.f, 2.f));
        return Button;
    };
    const FLinearColor PresetTint(.27f, .39f, .30f);
    AddButton(NSLOCTEXT("TownAge", "LightingMorning", "아침  08:00"), PresetTint)
        ->OnClicked.AddDynamic(this, &ThisClass::SelectMorning);
    AddButton(NSLOCTEXT("TownAge", "LightingNoon", "점심  12:00"), PresetTint)
        ->OnClicked.AddDynamic(this, &ThisClass::SelectNoon);
    AddButton(NSLOCTEXT("TownAge", "LightingEvening", "저녁  17:30"), PresetTint)
        ->OnClicked.AddDynamic(this, &ThisClass::SelectEvening);
    AddButton(NSLOCTEXT("TownAge", "LightingNight", "밤  22:00"), PresetTint)
        ->OnClicked.AddDynamic(this, &ThisClass::SelectNight);
    AddButton(NSLOCTEXT("TownAge", "LightingPreviewClose", "닫기  (F7)"), FLinearColor(.18f, .23f, .19f))
        ->OnClicked.AddDynamic(this, &ThisClass::CloseClicked);
}

FReply UTownAgeLightingPreviewWidget::NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (Event.GetKey() == EKeys::Escape || Event.GetKey() == EKeys::F7)
    {
        CloseClicked();
        return FReply::Handled();
    }
    return Super::NativeOnPreviewKeyDown(Geometry, Event);
}

void UTownAgeLightingPreviewWidget::SelectMorning()
{
    if (auto* PC = GetOwningPlayer<ATownAgePlayerController>())
        PC->SetLightingPreviewTime(ETownAgeLightingPreview::Morning);
}

void UTownAgeLightingPreviewWidget::SelectNoon()
{
    if (auto* PC = GetOwningPlayer<ATownAgePlayerController>())
        PC->SetLightingPreviewTime(ETownAgeLightingPreview::Noon);
}

void UTownAgeLightingPreviewWidget::SelectEvening()
{
    if (auto* PC = GetOwningPlayer<ATownAgePlayerController>())
        PC->SetLightingPreviewTime(ETownAgeLightingPreview::Evening);
}

void UTownAgeLightingPreviewWidget::SelectNight()
{
    if (auto* PC = GetOwningPlayer<ATownAgePlayerController>())
        PC->SetLightingPreviewTime(ETownAgeLightingPreview::Night);
}

void UTownAgeLightingPreviewWidget::CloseClicked()
{
    if (auto* PC = GetOwningPlayer<ATownAgePlayerController>()) PC->CloseLightingPreview();
}
