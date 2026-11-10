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
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/SafeZone.h"
#include "Components/ScaleBox.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/SizeBoxSlot.h"
#include "Components/Slider.h"
#include "Components/TextBlock.h"
#include "Components/Throbber.h"
#include "Components/UniformGridPanel.h"
#include "Components/UniformGridSlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/WidgetSwitcher.h"
#include "Engine/TextureRenderTarget2D.h"
#include "InputCoreTypes.h"

namespace
{
const TCHAR* ColorNames[] = {TEXT("RED"), TEXT("BLUE"), TEXT("GREEN"), TEXT("YELLOW")};
const FLinearColor ChipColors[] = {
    FLinearColor(.86f, .13f, .12f), FLinearColor(.12f, .35f, .90f),
    FLinearColor(.16f, .63f, .28f), FLinearColor(.95f, .72f, .12f)};
uint8 Amount(const FTownAgeMakeupState& State, int32 Index)
{
    switch (Index)
    {
        case 0: return State.BlushAmount;
        case 1: return State.LinerAmount;
        case 2: return State.IrisAmount;
        case 3: return State.AegyoAmount;
        case 4: return State.JawAmount;
        default: return State.NoseAmount;
    }
}
}

void UTownAgeCustomizationWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(true);
    auto Text = [&](const FText& Value, int32 Size, FLinearColor Color = FLinearColor(.94f, .93f, .86f))
    {
        auto* Label = WidgetTree->ConstructWidget<UTextBlock>();
        Label->SetText(Value);
        auto Font = Label->GetFont(); Font.Size = Size; Label->SetFont(Font);
        Label->SetColorAndOpacity(FSlateColor(Color));
        Label->SetAutoWrapText(true);
        return Label;
    };
    auto Button = [&](const FText& Value, FLinearColor Color, int32 Size = 15)
    {
        auto* Result = WidgetTree->ConstructWidget<UButton>();
        Result->SetBackgroundColor(Color);
        auto* Target = WidgetTree->ConstructWidget<USizeBox>();
        Target->SetMinDesiredWidth(64); Target->SetMinDesiredHeight(48);
        auto* Label = Text(Value, Size); Label->SetJustification(ETextJustify::Center);
        Cast<USizeBoxSlot>(Target->AddChild(Label))->SetVerticalAlignment(VAlign_Center);
        Result->AddChild(Target); TouchSizes.Add(Target);
        return Result;
    };

    auto* Root = WidgetTree->ConstructWidget<UBorder>();
    Root->SetBrushColor(FLinearColor(.025f, .035f, .03f, 1.f));
    Root->SetPadding(FMargin(0)); WidgetTree->RootWidget = Root;
    auto* Safe = WidgetTree->ConstructWidget<USafeZone>(); Root->AddChild(Safe);
    auto* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>(); Safe->AddChild(Canvas);
    Panel = WidgetTree->ConstructWidget<UBorder>();
    Panel->SetPadding(FMargin(0)); Panel->SetBrushColor(FLinearColor(.065f, .085f, .072f));
    auto* PanelSlot = Canvas->AddChildToCanvas(Panel);
    PanelSlot->SetAnchors(FAnchors(0, 0, 1, 1)); PanelSlot->SetOffsets(FMargin(32));
    auto* Columns = WidgetTree->ConstructWidget<UHorizontalBox>(); Panel->AddChild(Columns);

    auto* Portrait = WidgetTree->ConstructWidget<UBorder>();
    Portrait->SetPadding(FMargin(8)); Portrait->SetBrushColor(FLinearColor(.08f, .105f, .09f));
    auto* PortraitSlot = Columns->AddChildToHorizontalBox(Portrait);
    FSlateChildSize PortraitFill(ESlateSizeRule::Fill); PortraitFill.Value = 1.25f; PortraitSlot->SetSize(PortraitFill);
    auto* PortraitContent = WidgetTree->ConstructWidget<UVerticalBox>(); Portrait->AddChild(PortraitContent);
    PortraitContent->AddChildToVerticalBox(Text(NSLOCTEXT("TownAge", "YourCharacter", "나의 캐릭터"), 15,
        FLinearColor(.66f, .75f, .65f)))->SetPadding(FMargin(14, 10));
    auto* Scale = WidgetTree->ConstructWidget<UScaleBox>(); Scale->SetStretch(EStretch::ScaleToFit);
    PortraitContent->AddChildToVerticalBox(Scale)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* ImageSize = WidgetTree->ConstructWidget<USizeBox>();
    ImageSize->SetWidthOverride(768); ImageSize->SetHeightOverride(1024); Scale->AddChild(ImageSize);
    auto* PreviewLayers = WidgetTree->ConstructWidget<UOverlay>(); ImageSize->AddChild(PreviewLayers);
    PreviewImage = WidgetTree->ConstructWidget<UImage>(); PreviewImage->SetVisibility(ESlateVisibility::Hidden);
    auto* PreviewSlot = PreviewLayers->AddChildToOverlay(PreviewImage);
    PreviewSlot->SetHorizontalAlignment(HAlign_Fill); PreviewSlot->SetVerticalAlignment(VAlign_Fill);
    LoadingPanel = WidgetTree->ConstructWidget<UBorder>();
    LoadingPanel->SetBrushColor(FLinearColor(.08f, .105f, .09f, 1.f));
    LoadingPanel->SetHorizontalAlignment(HAlign_Center); LoadingPanel->SetVerticalAlignment(VAlign_Center);
    auto* LoadingSlot = PreviewLayers->AddChildToOverlay(LoadingPanel);
    LoadingSlot->SetHorizontalAlignment(HAlign_Fill); LoadingSlot->SetVerticalAlignment(VAlign_Fill);
    auto* LoadingContent = WidgetTree->ConstructWidget<UVerticalBox>(); LoadingPanel->AddChild(LoadingContent);
    auto* LoadingLabel = Text(NSLOCTEXT("TownAge", "VanityOpening", "화장대 여는 중…"), 28);
    LoadingLabel->SetJustification(ETextJustify::Center);
    LoadingContent->AddChildToVerticalBox(LoadingLabel)->SetPadding(FMargin(16, 8));
    auto* LoadingDots = WidgetTree->ConstructWidget<UThrobber>(); LoadingDots->SetNumberOfPieces(3);
    auto* DotsSlot = LoadingContent->AddChildToVerticalBox(LoadingDots);
    DotsSlot->SetHorizontalAlignment(HAlign_Center); DotsSlot->SetPadding(FMargin(16));

    auto* Options = WidgetTree->ConstructWidget<UBorder>();
    Options->SetPadding(FMargin(20)); Options->SetBrushColor(FLinearColor(.065f, .085f, .072f));
    Columns->AddChildToHorizontalBox(Options)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* Content = WidgetTree->ConstructWidget<UVerticalBox>(); Options->AddChild(Content);
    auto* Header = WidgetTree->ConstructWidget<UHorizontalBox>();
    Content->AddChildToVerticalBox(Header)->SetPadding(FMargin(0, 0, 0, 12));
    Header->AddChildToHorizontalBox(Text(NSLOCTEXT("TownAge", "CustomizationTitle", "나만의 스타일"), 24))
        ->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    auto* Close = Button(NSLOCTEXT("TownAge", "CloseCustomization", "닫기"), FLinearColor(.16f, .22f, .18f));
    Header->AddChild(Close); Close->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::CloseClicked);
    auto* Tabs = WidgetTree->ConstructWidget<UHorizontalBox>();
    Content->AddChildToVerticalBox(Tabs)->SetPadding(FMargin(0, 0, 0, 14));
    for (const FText& Label : {NSLOCTEXT("TownAge", "DyeCategory", "염색"),
        NSLOCTEXT("TownAge", "SurgeryCategory", "성형"), NSLOCTEXT("TownAge", "MakeupCategory", "화장")})
    {
        auto* Tab = Button(Label, FLinearColor(.12f, .18f, .14f), 18);
        auto* TabSlot = Tabs->AddChildToHorizontalBox(Tab); TabSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        TabSlot->SetPadding(FMargin(3, 0)); CategoryButtons.Add(Tab);
    }
    CategoryButtons[0]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::DyeClicked);
    CategoryButtons[1]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::SurgeryClicked);
    CategoryButtons[2]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::MakeupClicked);
    CategoryPanels = WidgetTree->ConstructWidget<UWidgetSwitcher>();
    Content->AddChildToVerticalBox(CategoryPanels)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));

    auto* DyePanel = WidgetTree->ConstructWidget<UVerticalBox>(); CategoryPanels->AddChild(DyePanel);
    DyePanel->AddChildToVerticalBox(Text(NSLOCTEXT("TownAge", "HairColor", "헤어 색상"), 21))->SetPadding(FMargin(0, 0, 0, 6));
    DyePanel->AddChildToVerticalBox(Text(NSLOCTEXT("TownAge", "DyeHint", "원하는 색상을 선택하세요."), 14,
        FLinearColor(.68f, .75f, .67f)))->SetPadding(FMargin(0, 0, 0, 14));
    auto* Grid = WidgetTree->ConstructWidget<UUniformGridPanel>(); Grid->SetSlotPadding(FMargin(5)); DyePanel->AddChild(Grid);
    for (int32 Index = 0; Index < 4; ++Index)
    {
        auto* Chip = WidgetTree->ConstructWidget<UButton>(); Chip->SetBackgroundColor(ChipColors[Index]);
        auto* ChipSize = WidgetTree->ConstructWidget<USizeBox>(); ChipSize->SetMinDesiredWidth(96); ChipSize->SetMinDesiredHeight(76);
        auto* Label = Text(FText::FromString(ColorNames[Index]), 16); Label->SetJustification(ETextJustify::Center);
        Label->SetShadowColorAndOpacity(FLinearColor(0, 0, 0, .8f)); Label->SetShadowOffset(FVector2D(0, 1));
        Cast<USizeBoxSlot>(ChipSize->AddChild(Label))->SetVerticalAlignment(VAlign_Center); Chip->AddChild(ChipSize);
        auto* ChipSlot = Grid->AddChildToUniformGrid(Chip, Index / 2, Index % 2);
        ChipSlot->SetHorizontalAlignment(HAlign_Fill); ChipSlot->SetVerticalAlignment(VAlign_Fill);
        Chips.Add(Chip); ChipLabels.Add(Label); ChipSizes.Add(ChipSize);
    }
    Chips[0]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::RedClicked);
    Chips[1]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::BlueClicked);
    Chips[2]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::GreenClicked);
    Chips[3]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::YellowClicked);
    auto* Surgery = WidgetTree->ConstructWidget<UBorder>(); Surgery->SetPadding(FMargin(16));
    Surgery->SetBrushColor(FLinearColor(.08f, .105f, .09f));
    Surgery->AddChild(Text(NSLOCTEXT("TownAge", "SurgeryPending", "성형 기능은 준비 중입니다.\n얼굴 미리보기만 제공됩니다."), 18));
    CategoryPanels->AddChild(Surgery);

    auto* MakeupScroll = WidgetTree->ConstructWidget<UScrollBox>();
    MakeupScroll->SetConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible); CategoryPanels->AddChild(MakeupScroll);
    auto* MakeupContent = WidgetTree->ConstructWidget<UVerticalBox>(); MakeupScroll->AddChild(MakeupContent);
    auto* MakeupActions = WidgetTree->ConstructWidget<UUniformGridPanel>();
    MakeupActions->SetSlotPadding(FMargin(3));
    MakeupContent->AddChildToVerticalBox(MakeupActions)->SetPadding(FMargin(0, 0, 0, 12));
    auto* Natural = Button(NSLOCTEXT("TownAge", "NaturalMakeup", "자연스럽게"), FLinearColor(.27f, .37f, .24f));
    auto* Strong = Button(NSLOCTEXT("TownAge", "StrongMakeupComparison", "강하게 비교"), FLinearColor(.35f, .26f, .19f));
    auto* Original = Button(NSLOCTEXT("TownAge", "HoldOriginalMakeup", "원본 보기 (누르기)"), FLinearColor(.18f, .25f, .23f));
    auto* Reset = Button(NSLOCTEXT("TownAge", "ResetMakeup", "화장 초기화"), FLinearColor(.16f, .20f, .17f));
    auto* NaturalActionSlot = MakeupActions->AddChildToUniformGrid(Natural, 0, 0);
    auto* StrongActionSlot = MakeupActions->AddChildToUniformGrid(Strong, 0, 1);
    auto* OriginalActionSlot = MakeupActions->AddChildToUniformGrid(Original, 1, 0);
    auto* ResetActionSlot = MakeupActions->AddChildToUniformGrid(Reset, 1, 1);
    for (UUniformGridSlot* ActionSlot : {NaturalActionSlot, StrongActionSlot, OriginalActionSlot, ResetActionSlot})
    {
        ActionSlot->SetHorizontalAlignment(HAlign_Fill);
        ActionSlot->SetVerticalAlignment(VAlign_Fill);
    }
    Natural->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::NaturalMakeupClicked);
    Strong->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::StrongMakeupClicked);
    Original->OnPressed.AddDynamic(this, &UTownAgeCustomizationWidget::OriginalPreviewPressed);
    Original->OnReleased.AddDynamic(this, &UTownAgeCustomizationWidget::OriginalPreviewReleased);
    Reset->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::ResetMakeupClicked);
    MakeupControls.Add(Natural); MakeupControls.Add(Strong); MakeupControls.Add(Original); MakeupControls.Add(Reset);

    auto Palette = [&](const TArray<FText>& Labels, const TArray<FLinearColor>& Colors, TArray<TObjectPtr<UButton>>& Buttons)
    {
        auto* PaletteGrid = WidgetTree->ConstructWidget<UUniformGridPanel>(); PaletteGrid->SetSlotPadding(FMargin(3));
        MakeupContent->AddChildToVerticalBox(PaletteGrid)->SetPadding(FMargin(0, 0, 0, 8));
        for (int32 Index = 0; Index < Labels.Num(); ++Index)
        {
            auto* Choice = Button(Labels[Index], Colors[Index], 13);
            auto* ChoiceSlot = PaletteGrid->AddChildToUniformGrid(Choice, Index / 3, Index % 3);
            ChoiceSlot->SetHorizontalAlignment(HAlign_Fill); Buttons.Add(Choice); MakeupControls.Add(Choice);
        }
    };
    auto AmountRow = [&](const FText& Label, int32 Index)
    {
        auto* Heading = WidgetTree->ConstructWidget<UHorizontalBox>();
        MakeupContent->AddChildToVerticalBox(Heading)->SetPadding(FMargin(3, 8, 3, 0));
        Heading->AddChildToHorizontalBox(Text(Label, 17))->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        auto* Number = Text(FText::FromString(TEXT("0")), 14, FLinearColor(.7f, .79f, .69f));
        Heading->AddChild(Number); AmountLabels.Add(Number);
        auto* Target = WidgetTree->ConstructWidget<USizeBox>(); Target->SetMinDesiredHeight(48); TouchSizes.Add(Target);
        auto* Slider = WidgetTree->ConstructWidget<USlider>();
        Slider->SetMinValue(0.f); Slider->SetMaxValue(1.f); Slider->SetStepSize(.05f);
        Slider->SetSliderBarColor(FLinearColor(.22f, .31f, .25f));
        Slider->SetSliderHandleColor(FLinearColor(.77f, .86f, .67f));
        Target->AddChild(Slider); MakeupContent->AddChildToVerticalBox(Target)->SetPadding(FMargin(3, 0, 3, 6));
        Slider->OnMouseCaptureBegin.AddDynamic(this, &UTownAgeCustomizationWidget::SliderCaptureBegin);
        Slider->OnMouseCaptureEnd.AddDynamic(this, &UTownAgeCustomizationWidget::SliderCaptureEnd);
        AmountSliders.Add(Slider); MakeupControls.Add(Slider);
    };
    AmountRow(NSLOCTEXT("TownAge", "BlushAmount", "볼터치"), 0);
    Palette({NSLOCTEXT("TownAge", "Rose", "로즈"), NSLOCTEXT("TownAge", "Peach", "피치"),
        NSLOCTEXT("TownAge", "Coral", "코랄"), NSLOCTEXT("TownAge", "Mauve", "모브")},
        {FLinearColor(.66f,.28f,.32f), FLinearColor(.76f,.44f,.29f), FLinearColor(.78f,.34f,.27f), FLinearColor(.50f,.30f,.45f)}, BlushButtons);
    AmountRow(NSLOCTEXT("TownAge", "LinerAmount", "아이라인"), 1);
    AmountRow(NSLOCTEXT("TownAge", "IrisAmount", "렌즈 색상"), 2);
    Palette({NSLOCTEXT("TownAge", "Brown", "브라운"), NSLOCTEXT("TownAge", "Hazel", "헤이즐"),
        NSLOCTEXT("TownAge", "Sage", "세이지"), NSLOCTEXT("TownAge", "BlueGray", "블루그레이"), NSLOCTEXT("TownAge", "LavenderGray", "라벤더그레이")},
        {FLinearColor(.28f,.18f,.10f), FLinearColor(.43f,.34f,.18f), FLinearColor(.28f,.40f,.29f),
        FLinearColor(.26f,.36f,.46f), FLinearColor(.40f,.34f,.45f)}, IrisButtons);
    AmountRow(NSLOCTEXT("TownAge", "AegyoAmount", "애굣살"), 3);
    AmountRow(NSLOCTEXT("TownAge", "JawAmount", "턱 쉐딩"), 4);
    AmountRow(NSLOCTEXT("TownAge", "NoseAmount", "코 쉐딩"), 5);
    AmountSliders[0]->OnValueChanged.AddDynamic(this, &UTownAgeCustomizationWidget::BlushChanged);
    AmountSliders[1]->OnValueChanged.AddDynamic(this, &UTownAgeCustomizationWidget::LinerChanged);
    AmountSliders[2]->OnValueChanged.AddDynamic(this, &UTownAgeCustomizationWidget::IrisChanged);
    AmountSliders[3]->OnValueChanged.AddDynamic(this, &UTownAgeCustomizationWidget::AegyoChanged);
    AmountSliders[4]->OnValueChanged.AddDynamic(this, &UTownAgeCustomizationWidget::JawChanged);
    AmountSliders[5]->OnValueChanged.AddDynamic(this, &UTownAgeCustomizationWidget::NoseChanged);
    BlushButtons[0]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::RoseClicked);
    BlushButtons[1]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::PeachClicked);
    BlushButtons[2]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::CoralClicked);
    BlushButtons[3]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::MauveClicked);
    IrisButtons[0]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::BrownClicked);
    IrisButtons[1]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::HazelClicked);
    IrisButtons[2]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::SageClicked);
    IrisButtons[3]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::BlueGrayClicked);
    IrisButtons[4]->OnClicked.AddDynamic(this, &UTownAgeCustomizationWidget::LavenderClicked);
    Status = Text(NSLOCTEXT("TownAge", "LoadingCharacter", "캐릭터를 준비하고 있어요."), 13, FLinearColor(.68f,.75f,.67f));
    Content->AddChildToVerticalBox(Status)->SetPadding(FMargin(3, 12, 3, 0));
    SetPreviewTexture(PreviewTexture); SetSelectedColor(SelectedColor); SetCategory(Category); SetMakeupState(MakeupState);
}

void UTownAgeCustomizationWidget::NativeTick(const FGeometry& Geometry, float DeltaTime)
{
    Super::NativeTick(Geometry, DeltaTime);
    const float ViewportScale = FMath::Max(.1f, UWidgetLayoutLibrary::GetViewportScale(this));
    const float TouchTarget = FMath::Max(48.f, 48.f / ViewportScale);
    for (const auto& Size : ChipSizes) Size->SetMinDesiredHeight(FMath::Max(76.f, TouchTarget));
    for (const auto& Size : TouchSizes) Size->SetMinDesiredHeight(TouchTarget);
    if (Panel)
    {
        const float Margin = FMath::Clamp(float(Geometry.GetLocalSize().Y) * .04f, 10.f, 32.f);
        Cast<UCanvasPanelSlot>(Panel->Slot)->SetOffsets(FMargin(Margin));
    }
    if (bMakeupPending)
    {
        MakeupPendingAge += DeltaTime;
        if (MakeupPendingAge >= .1f) FlushMakeupChange();
    }
}

void UTownAgeCustomizationWidget::SetPreviewTexture(UTextureRenderTarget2D* Texture)
{
    PreviewTexture = Texture;
    if (!PreviewImage) return;
    FSlateBrush Brush; Brush.SetResourceObject(Texture); Brush.ImageSize = FVector2D(768,1024);
    Brush.DrawAs = Texture ? ESlateBrushDrawType::Image : ESlateBrushDrawType::NoDrawType;
    PreviewImage->SetBrush(Brush); SetReady(bReady);
}
void UTownAgeCustomizationWidget::SetSelectedColor(uint8 Index)
{
    SelectedColor = Index;
    for (int32 I = 0; I < Chips.Num(); ++I)
    {
        ChipLabels[I]->SetText(FText::FromString(FString(ColorNames[I]) + (Index == I + 1 ? TEXT(" / SELECTED") : TEXT(""))));
        Chips[I]->SetRenderOpacity(Index == I + 1 || Index == 0 ? 1.f : .78f);
    }
}
void UTownAgeCustomizationWidget::SetReady(bool bInReady)
{
    bReady = bInReady;
    const bool bShowPreview = bReady && IsValid(PreviewTexture);
    if (PreviewImage) PreviewImage->SetVisibility(bShowPreview ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Hidden);
    if (LoadingPanel) LoadingPanel->SetVisibility(bShowPreview ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
    for (int32 I=0; I<CategoryButtons.Num(); ++I) CategoryButtons[I]->SetIsEnabled(bShowPreview && (AllowedCategories & (1 << I)) != 0);
    for (const auto& Chip : Chips) Chip->SetIsEnabled(bShowPreview && bDyeAvailable);
    for (const auto& Control : MakeupControls) Control->SetIsEnabled(bShowPreview && bMakeupAvailable);
    if (!Status) return;
    FText Notice = NSLOCTEXT("TownAge", "AppliedAppearance", "변경 사항은 캐릭터에 바로 적용됩니다.");
    if (!bShowPreview) Notice = NSLOCTEXT("TownAge", "LoadingCharacter", "캐릭터를 준비하고 있어요.");
    else if (Category == ETownAgeCosmeticCategory::Surgery) Notice = NSLOCTEXT("TownAge", "SurgeryPreviewOnly", "성형은 얼굴 미리보기만 제공됩니다.");
    else if (Category == ETownAgeCosmeticCategory::Dye && !bDyeAvailable) Notice = NSLOCTEXT("TownAge", "DyeUnavailable", "이 캐릭터의 염색 설정이 아직 준비되지 않았어요.");
    else if (Category == ETownAgeCosmeticCategory::Makeup && !bMakeupAvailable) Notice = NSLOCTEXT("TownAge", "MakeupUnavailable", "이 캐릭터의 화장 설정이 아직 준비되지 않았어요.");
    Status->SetText(Notice);
}
void UTownAgeCustomizationWidget::SetCategory(ETownAgeCosmeticCategory InCategory)
{
    Category = InCategory;
    const int32 Active = int32(Category);
    if (CategoryPanels) CategoryPanels->SetActiveWidgetIndex(FMath::Clamp(Active,0,2));
    for (int32 I=0; I<CategoryButtons.Num(); ++I)
        CategoryButtons[I]->SetBackgroundColor(I==Active ? FLinearColor(.28f,.42f,.27f) : FLinearColor(.11f,.16f,.13f));
    SetReady(bReady);
}
void UTownAgeCustomizationWidget::SetAllowedCategories(uint8 Mask)
{
    AllowedCategories = Mask & 7; SetReady(bReady);
}
void UTownAgeCustomizationWidget::SetDyeAvailable(bool bAvailable) { bDyeAvailable=bAvailable; SetReady(bReady); }
void UTownAgeCustomizationWidget::SetMakeupAvailable(bool bAvailable) { bMakeupAvailable=bAvailable; SetReady(bReady); }
void UTownAgeCustomizationWidget::SetMakeupState(const FTownAgeMakeupState& InState)
{
    if (bSliderCaptured || bMakeupPending) return;
    MakeupState = InState; bSyncingMakeup=true;
    for (int32 I=0; I<AmountSliders.Num(); ++I)
    {
        AmountSliders[I]->SetValue(Amount(MakeupState,I)/100.f);
        AmountLabels[I]->SetText(FText::AsNumber(Amount(MakeupState,I)));
    }
    for (int32 I=0; I<BlushButtons.Num(); ++I) BlushButtons[I]->SetRenderOpacity(I==MakeupState.BlushColor ? 1.f : .65f);
    for (int32 I=0; I<IrisButtons.Num(); ++I) IrisButtons[I]->SetRenderOpacity(I==MakeupState.IrisColor ? 1.f : .65f);
    bSyncingMakeup=false;
}
void UTownAgeCustomizationWidget::SelectCategory(ETownAgeCosmeticCategory Value)
{
    if (!bReady || !IsValid(PreviewTexture) || !(AllowedCategories & (1 << int32(Value)))) return;
    FlushMakeupChange(); SetCategory(Value); OnCategorySelected.Broadcast(Value);
}
void UTownAgeCustomizationWidget::SelectColor(uint8 Index)
{
    if (!bReady || !bDyeAvailable || !IsValid(PreviewTexture)) return;
    SetSelectedColor(Index); OnColorSelected.Broadcast(Index);
}
void UTownAgeCustomizationWidget::QueueMakeupChange()
{
    if (!bMakeupPending) MakeupPendingAge=0.f;
    bMakeupPending=true;
}
void UTownAgeCustomizationWidget::FlushMakeupChange()
{
    if (!bMakeupPending || !bReady || !bMakeupAvailable) return;
    bMakeupPending=false; MakeupPendingAge=0.f; OnMakeupChanged.Broadcast(MakeupState);
}
void UTownAgeCustomizationWidget::SetAmount(int32 Index, float Value)
{
    if (bSyncingMakeup || !bReady || !bMakeupAvailable) return;
    const uint8 ValueByte=uint8(FMath::Clamp(FMath::RoundToInt(Value*100.f),0,100));
    switch (Index)
    {
        case 0: MakeupState.BlushAmount=ValueByte; break;
        case 1: MakeupState.LinerAmount=ValueByte; break;
        case 2: MakeupState.IrisAmount=ValueByte; break;
        case 3: MakeupState.AegyoAmount=ValueByte; break;
        case 4: MakeupState.JawAmount=ValueByte; break;
        case 5: MakeupState.NoseAmount=ValueByte; break;
        default: return;
    }
    if (AmountLabels.IsValidIndex(Index)) AmountLabels[Index]->SetText(FText::AsNumber(ValueByte));
    QueueMakeupChange();
}
void UTownAgeCustomizationWidget::SelectBlush(uint8 Index)
{
    if (!bReady || !bMakeupAvailable) return;
    MakeupState.BlushColor=Index; if (!MakeupState.BlushAmount) MakeupState.BlushAmount=35;
    bMakeupPending=false; SetMakeupState(MakeupState); QueueMakeupChange(); FlushMakeupChange();
}
void UTownAgeCustomizationWidget::SelectIris(uint8 Index)
{
    if (!bReady || !bMakeupAvailable) return;
    MakeupState.IrisColor=Index; if (!MakeupState.IrisAmount) MakeupState.IrisAmount=55;
    bMakeupPending=false; SetMakeupState(MakeupState); QueueMakeupChange(); FlushMakeupChange();
}
void UTownAgeCustomizationWidget::NaturalMakeupClicked()
{
    if (!bReady || !bMakeupAvailable) return;
    FTownAgeMakeupState Natural; Natural.BlushColor=0; Natural.BlushAmount=30; Natural.LinerAmount=25;
    Natural.IrisColor=1; Natural.IrisAmount=35; Natural.AegyoAmount=30; Natural.JawAmount=20; Natural.NoseAmount=20;
    bMakeupPending=false; SetMakeupState(Natural); QueueMakeupChange(); FlushMakeupChange();
}
void UTownAgeCustomizationWidget::StrongMakeupClicked()
{
    if (!bReady || !bMakeupAvailable) return;
    FTownAgeMakeupState Strong; Strong.BlushColor=2; Strong.IrisColor=3;
    Strong.BlushAmount=Strong.LinerAmount=Strong.IrisAmount=Strong.AegyoAmount=Strong.JawAmount=Strong.NoseAmount=100;
    bMakeupPending=false; SetMakeupState(Strong); QueueMakeupChange(); FlushMakeupChange();
}
void UTownAgeCustomizationWidget::OriginalPreviewPressed()
{
    if (bReady && bMakeupAvailable && Category==ETownAgeCosmeticCategory::Makeup)
        OnOriginalPreview.Broadcast(true);
}
void UTownAgeCustomizationWidget::OriginalPreviewReleased() { OnOriginalPreview.Broadcast(false); }
void UTownAgeCustomizationWidget::ResetMakeupClicked()
{
    if (!bReady || !bMakeupAvailable) return;
    bMakeupPending=false; SetMakeupState(FTownAgeMakeupState()); QueueMakeupChange(); FlushMakeupChange();
}
void UTownAgeCustomizationWidget::SliderCaptureBegin() { bSliderCaptured=true; }
void UTownAgeCustomizationWidget::SliderCaptureEnd() { bSliderCaptured=false; FlushMakeupChange(); }
void UTownAgeCustomizationWidget::RedClicked() { SelectColor(1); }
void UTownAgeCustomizationWidget::BlueClicked() { SelectColor(2); }
void UTownAgeCustomizationWidget::GreenClicked() { SelectColor(3); }
void UTownAgeCustomizationWidget::YellowClicked() { SelectColor(4); }
void UTownAgeCustomizationWidget::CloseClicked() { FlushMakeupChange(); OnCloseRequested.Broadcast(); }
void UTownAgeCustomizationWidget::DyeClicked() { SelectCategory(ETownAgeCosmeticCategory::Dye); }
void UTownAgeCustomizationWidget::SurgeryClicked() { SelectCategory(ETownAgeCosmeticCategory::Surgery); }
void UTownAgeCustomizationWidget::MakeupClicked() { SelectCategory(ETownAgeCosmeticCategory::Makeup); }
void UTownAgeCustomizationWidget::RoseClicked() { SelectBlush(0); }
void UTownAgeCustomizationWidget::PeachClicked() { SelectBlush(1); }
void UTownAgeCustomizationWidget::CoralClicked() { SelectBlush(2); }
void UTownAgeCustomizationWidget::MauveClicked() { SelectBlush(3); }
void UTownAgeCustomizationWidget::BrownClicked() { SelectIris(0); }
void UTownAgeCustomizationWidget::HazelClicked() { SelectIris(1); }
void UTownAgeCustomizationWidget::SageClicked() { SelectIris(2); }
void UTownAgeCustomizationWidget::BlueGrayClicked() { SelectIris(3); }
void UTownAgeCustomizationWidget::LavenderClicked() { SelectIris(4); }
void UTownAgeCustomizationWidget::BlushChanged(float Value) { SetAmount(0,Value); }
void UTownAgeCustomizationWidget::LinerChanged(float Value) { SetAmount(1,Value); }
void UTownAgeCustomizationWidget::IrisChanged(float Value) { SetAmount(2,Value); }
void UTownAgeCustomizationWidget::AegyoChanged(float Value) { SetAmount(3,Value); }
void UTownAgeCustomizationWidget::JawChanged(float Value) { SetAmount(4,Value); }
void UTownAgeCustomizationWidget::NoseChanged(float Value) { SetAmount(5,Value); }
FReply UTownAgeCustomizationWidget::NativeOnPreviewKeyDown(const FGeometry& Geometry,const FKeyEvent& Event)
{
    if (Event.GetKey()==EKeys::Escape) { CloseClicked(); return FReply::Handled(); }
    return Super::NativeOnPreviewKeyDown(Geometry,Event);
}
