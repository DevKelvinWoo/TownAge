#include "TownAgeCustomizationWidget.h"

#include "Blueprint/WidgetLayoutLibrary.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/SafeZone.h"
#include "Components/ScaleBox.h"
#include "Components/SizeBox.h"
#include "Components/SizeBoxSlot.h"
#include "Components/TextBlock.h"
#include "Components/UniformGridPanel.h"
#include "Components/UniformGridSlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/TextureRenderTarget2D.h"
#include "InputCoreTypes.h"

namespace
{
const TCHAR* ColorNames[] = {TEXT("RED"), TEXT("BLUE"), TEXT("GREEN"), TEXT("YELLOW")};
const FLinearColor ChipColors[] = {
    FLinearColor(.86f, .13f, .12f), FLinearColor(.12f, .35f, .90f),
    FLinearColor(.16f, .63f, .28f), FLinearColor(.95f, .72f, .12f)};
}

void UTownAgeCustomizationWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(true);
    auto Text = [&](const FString& Value, int32 Size, FLinearColor Color = FLinearColor(.94f, .93f, .86f))
    {
        auto* Label = WidgetTree->ConstructWidget<UTextBlock>();
        Label->SetText(FText::FromString(Value));
        auto Font = Label->GetFont();
        Font.Size = Size;
        Label->SetFont(Font);
        Label->SetColorAndOpacity(FSlateColor(Color));
        Label->SetAutoWrapText(true);
        return Label;
    };

    auto* Root = WidgetTree->ConstructWidget<UBorder>();
    Root->SetBrushColor(FLinearColor(.025f, .035f, .03f, 1.f));
    Root->SetPadding(FMargin(0));
    WidgetTree->RootWidget = Root;
    auto* Safe = WidgetTree->ConstructWidget<USafeZone>();
    Root->AddChild(Safe);
    auto* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>();
    Safe->AddChild(Canvas);
    Panel = WidgetTree->ConstructWidget<UBorder>();
    Panel->SetPadding(FMargin(0));
    Panel->SetBrushColor(FLinearColor(.065f, .085f, .072f));
    auto* PanelSlot = Canvas->AddChildToCanvas(Panel);
    PanelSlot->SetAnchors(FAnchors(0, 0, 1, 1));
    PanelSlot->SetOffsets(FMargin(32));
    auto* Columns = WidgetTree->ConstructWidget<UHorizontalBox>();
    Panel->AddChild(Columns);

    auto* Portrait = WidgetTree->ConstructWidget<UBorder>();
    Portrait->SetPadding(FMargin(8));
    Portrait->SetBrushColor(FLinearColor(.08f, .105f, .09f));
    auto* PortraitSlot = Columns->AddChildToHorizontalBox(Portrait);
    FSlateChildSize PortraitFill(ESlateSizeRule::Fill); PortraitFill.Value = 1.25f;
    PortraitSlot->SetSize(PortraitFill);
    auto* PortraitContent = WidgetTree->ConstructWidget<UVerticalBox>();
    Portrait->AddChild(PortraitContent);
    auto* PreviewTitle = Text(TEXT("YOUR CHARACTER"), 15, FLinearColor(.66f, .75f, .65f));
    PortraitContent->AddChildToVerticalBox(PreviewTitle)->SetPadding(FMargin(14, 10));
    auto* Scale = WidgetTree->ConstructWidget<UScaleBox>();
    Scale->SetStretch(EStretch::ScaleToFit);
    auto* ImageSlot = PortraitContent->AddChildToVerticalBox(Scale);
    ImageSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* ImageSize = WidgetTree->ConstructWidget<USizeBox>();
    ImageSize->SetWidthOverride(768); ImageSize->SetHeightOverride(1024);
    Scale->AddChild(ImageSize);
    PreviewImage = WidgetTree->ConstructWidget<UImage>();
    PreviewImage->SetVisibility(ESlateVisibility::HitTestInvisible);
    ImageSize->AddChild(PreviewImage);

    auto* Options = WidgetTree->ConstructWidget<UBorder>();
    Options->SetPadding(FMargin(24));
    Options->SetBrushColor(FLinearColor(.065f, .085f, .072f));
    auto* OptionsSlot = Columns->AddChildToHorizontalBox(Options);
    OptionsSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* Content = WidgetTree->ConstructWidget<UVerticalBox>();
    Options->AddChild(Content);
    auto* Header = WidgetTree->ConstructWidget<UHorizontalBox>();
    Content->AddChildToVerticalBox(Header)->SetPadding(FMargin(0, 0, 0, 16));
    Header->AddChildToHorizontalBox(Text(TEXT("Make it yours"), 26))->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* Close = WidgetTree->ConstructWidget<UButton>();
    Close->SetBackgroundColor(FLinearColor(.16f, .22f, .18f));
    CloseSize = WidgetTree->ConstructWidget<USizeBox>();
    CloseSize->SetMinDesiredWidth(72); CloseSize->SetMinDesiredHeight(48);
    auto* CloseLabel = Text(TEXT("Close"), 15);
    CloseLabel->SetJustification(ETextJustify::Center);
    auto* CloseLabelSlot = Cast<USizeBoxSlot>(CloseSize->AddChild(CloseLabel));
    CloseLabelSlot->SetVerticalAlignment(VAlign_Center);
    Close->AddChild(CloseSize);
    Header->AddChild(Close);
    Close->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::CloseClicked);

    auto* Tab = WidgetTree->ConstructWidget<UBorder>();
    Tab->SetPadding(FMargin(16, 12));
    Tab->SetBrushColor(FLinearColor(.24f, .34f, .23f));
    Tab->AddChild(Text(TEXT("Dye"), 21));
    Content->AddChildToVerticalBox(Tab)->SetPadding(FMargin(0, 0, 0, 22));
    Content->AddChildToVerticalBox(Text(TEXT("Hair color"), 22))->SetPadding(FMargin(0, 0, 0, 6));
    Content->AddChildToVerticalBox(Text(TEXT("Choose a color to try it on."), 15, FLinearColor(.68f, .75f, .67f)))
        ->SetPadding(FMargin(0, 0, 0, 18));
    auto* Grid = WidgetTree->ConstructWidget<UUniformGridPanel>();
    Grid->SetSlotPadding(FMargin(5));
    Content->AddChildToVerticalBox(Grid);
    for (int32 Index = 0; Index < 4; ++Index)
    {
        auto* Chip = WidgetTree->ConstructWidget<UButton>();
        Chip->SetBackgroundColor(ChipColors[Index]);
        auto* ChipSize = WidgetTree->ConstructWidget<USizeBox>();
        ChipSize->SetMinDesiredWidth(96); ChipSize->SetMinDesiredHeight(76);
        auto* Label = Text(ColorNames[Index], 16);
        Label->SetJustification(ETextJustify::Center);
        Label->SetShadowColorAndOpacity(FLinearColor(0, 0, 0, .8f));
        Label->SetShadowOffset(FVector2D(0, 1));
        auto* LabelSlot = Cast<USizeBoxSlot>(ChipSize->AddChild(Label));
        LabelSlot->SetVerticalAlignment(VAlign_Center);
        Chip->AddChild(ChipSize);
        auto* ChipSlot = Grid->AddChildToUniformGrid(Chip, Index / 2, Index % 2);
        ChipSlot->SetHorizontalAlignment(HAlign_Fill);
        ChipSlot->SetVerticalAlignment(VAlign_Fill);
        Chips.Add(Chip); ChipLabels.Add(Label); ChipSizes.Add(ChipSize);
    }
    Chips[0]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::RedClicked);
    Chips[1]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::BlueClicked);
    Chips[2]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::GreenClicked);
    Chips[3]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::YellowClicked);
    Status = Text(TEXT("Loading character..."), 14, FLinearColor(.68f, .75f, .67f));
    Content->AddChildToVerticalBox(Status)->SetPadding(FMargin(4, 20, 4, 0));
    SetPreviewTexture(PreviewTexture);
    SetReady(bReady);
    SetSelectedColor(SelectedColor);
}

void UTownAgeCustomizationWidget::NativeTick(const FGeometry& Geometry, float DeltaTime)
{
    Super::NativeTick(Geometry, DeltaTime);
    const float ViewportScale = FMath::Max(.1f, UWidgetLayoutLibrary::GetViewportScale(this));
    const float TouchTarget = FMath::Max(56.f, 48.f / ViewportScale);
    for (const auto& Size : ChipSizes) Size->SetMinDesiredHeight(FMath::Max(76.f, TouchTarget));
    if (CloseSize) CloseSize->SetMinDesiredHeight(FMath::Max(48.f, TouchTarget));
    if (Panel)
    {
        const float Margin = FMath::Clamp(float(Geometry.GetLocalSize().Y) * .04f, 10.f, 32.f);
        Cast<UCanvasPanelSlot>(Panel->Slot)->SetOffsets(FMargin(Margin));
    }
}

void UTownAgeCustomizationWidget::SetPreviewTexture(UTextureRenderTarget2D* Texture)
{
    PreviewTexture = Texture;
    if (!PreviewImage) return;
    FSlateBrush Brush;
    Brush.SetResourceObject(Texture);
    Brush.ImageSize = FVector2D(768, 1024);
    Brush.DrawAs = ESlateBrushDrawType::Image;
    PreviewImage->SetBrush(Brush);
}

void UTownAgeCustomizationWidget::SetSelectedColor(uint8 Index)
{
    SelectedColor = Index;
    for (int32 I = 0; I < Chips.Num(); ++I)
    {
        ChipLabels[I]->SetText(FText::FromString(FString(ColorNames[I]) + (Index == I + 1 ? TEXT("  / SELECTED") : TEXT(""))));
        Chips[I]->SetRenderOpacity(Index == I + 1 || Index == 0 ? 1.f : .78f);
    }
}

void UTownAgeCustomizationWidget::SetReady(bool bInReady)
{
    bReady = bInReady;
    for (const auto& Chip : Chips) Chip->SetIsEnabled(bReady);
    if (Status) Status->SetText(FText::FromString(bReady
        ? TEXT("Changes are applied to your character.") : TEXT("Loading character...")));
}

void UTownAgeCustomizationWidget::SelectColor(uint8 Index)
{
    if (!bReady) return;
    SetSelectedColor(Index);
    OnColorSelected.Broadcast(Index);
}

void UTownAgeCustomizationWidget::RedClicked() { SelectColor(1); }
void UTownAgeCustomizationWidget::BlueClicked() { SelectColor(2); }
void UTownAgeCustomizationWidget::GreenClicked() { SelectColor(3); }
void UTownAgeCustomizationWidget::YellowClicked() { SelectColor(4); }
void UTownAgeCustomizationWidget::CloseClicked() { OnCloseRequested.Broadcast(); }

FReply UTownAgeCustomizationWidget::NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (Event.GetKey() == EKeys::Escape)
    {
        CloseClicked();
        return FReply::Handled();
    }
    return Super::NativeOnPreviewKeyDown(Geometry, Event);
}
