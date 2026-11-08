#include "TownAgeChatWidget.h"
#include "TownAgePlayerController.h"
#include "TownAgePlayer.h"
#include "TownAgeChat.h"
#include "TownAgeTouch.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/EditableTextBox.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/SafeZone.h"
#include "Components/SizeBox.h"
#include "Components/SizeBoxSlot.h"
#include "Components/ScrollBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

ATownAgePlayerController* UTownAgeChatWidget::ChatController() const
{
    return Cast<ATownAgePlayerController>(GetOwningPlayer());
}

void UTownAgeChatWidget::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(true);
    SetVisibility(ESlateVisibility::SelfHitTestInvisible);
#if PLATFORM_ANDROID || PLATFORM_IOS
    bMobile = true;
#else
    bMobile = FParse::Param(FCommandLine::Get(), TEXT("faketouches"));
#endif
    auto Text = [&](const FString& Value, int32 Size)
    {
        UTextBlock* Label = WidgetTree->ConstructWidget<UTextBlock>();
        Label->SetText(FText::FromString(Value));
        FSlateFontInfo Font = Label->GetFont(); Font.Size = Size; Label->SetFont(Font);
        Label->SetColorAndOpacity(FSlateColor(FLinearColor(.95f, .96f, .91f)));
        Labels.Add(Label); LabelFontSizes.Add(Size);
        return Label;
    };
    auto Button = [&](const FString& Value, UTextBlock*& Label)
    {
        UButton* Result = WidgetTree->ConstructWidget<UButton>();
        Label = Text(Value, 15);
        USizeBox* Target = WidgetTree->ConstructWidget<USizeBox>();
        Target->SetMinDesiredWidth(64); Target->SetMinDesiredHeight(32);
        Label->SetJustification(ETextJustify::Center);
        Cast<USizeBoxSlot>(Target->AddChild(Label))->SetVerticalAlignment(VAlign_Center); Result->AddChild(Target);
        ButtonSizes.Add(Target);
        Result->SetBackgroundColor(FLinearColor(.25f, .34f, .29f, .9f));
        return Result;
    };
    USafeZone* Safe = WidgetTree->ConstructWidget<USafeZone>();
    Safe->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    WidgetTree->RootWidget = Safe;
    UCanvasPanel* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>();
    Canvas->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    Safe->AddChild(Canvas);
    Panel = WidgetTree->ConstructWidget<UBorder>();
    Panel->SetBrushColor(FLinearColor(.035f, .055f, .045f, .66f));
    Panel->SetPadding(FMargin(12));
    Canvas->AddChild(Panel);
    UVerticalBox* Content = WidgetTree->ConstructWidget<UVerticalBox>(); Panel->AddChild(Content);
    UHorizontalBox* Header = WidgetTree->ConstructWidget<UHorizontalBox>(); Content->AddChild(Header);
    UHorizontalBoxSlot* TitleSlot = Header->AddChildToHorizontalBox(Text(bMobile ? TEXT("Chat") : TEXT("Village chat"), 15));
    TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    UTextBlock* CloseLabel;
    CloseButton = Button(TEXT("Close"), CloseLabel); Header->AddChild(CloseButton);
    CloseButton->OnClicked.AddDynamic(this, &UTownAgeChatWidget::CloseClicked);
    Scroll = WidgetTree->ConstructWidget<UScrollBox>();
    Scroll->SetConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible);
    UVerticalBoxSlot* ScrollSlot = Content->AddChildToVerticalBox(Scroll);
    ScrollSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    ScrollSlot->SetPadding(FMargin(0, 8));
    Lines = WidgetTree->ConstructWidget<UVerticalBox>(); Scroll->AddChild(Lines);
    Composer = WidgetTree->ConstructWidget<UHorizontalBox>(); Content->AddChild(Composer);
    Entry = WidgetTree->ConstructWidget<UEditableTextBox>();
    Entry->SetHintText(FText::FromString(TEXT("Type a message...")));
    Entry->SetClearKeyboardFocusOnCommit(false);
    Entry->SetSelectAllTextWhenFocused(false);
    Entry->VirtualKeyboardTrigger = EVirtualKeyboardTrigger::OnAllFocusEvents;
    Entry->VirtualKeyboardDismissAction = EVirtualKeyboardDismissAction::TextChangeOnDismiss;
    EntryStyle = Entry->GetWidgetStyle();
    EntryStyle.TextStyle.Font.Size = 16;
    EntryStyle.BackgroundColor = FLinearColor(.06f, .085f, .07f, 1.f);
    EntryStyle.ForegroundColor = FLinearColor(.95f, .96f, .91f);
    EntryStyle.TextStyle.ColorAndOpacity = EntryStyle.ForegroundColor;
    Entry->SetWidgetStyle(EntryStyle);
    Entry->OnTextCommitted.AddDynamic(this, &UTownAgeChatWidget::TextCommitted);
    Entry->OnTextChanged.AddDynamic(this, &UTownAgeChatWidget::TextChanged);
    auto* EntrySlot = Composer->AddChildToHorizontalBox(Entry);
    EntrySlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    EntrySlot->SetPadding(FMargin(0, 0, 6, 0));
    UTextBlock* SendLabel;
    UButton* Send = Button(TEXT("Send"), SendLabel); Composer->AddChild(Send);
    Send->OnClicked.AddDynamic(this, &UTownAgeChatWidget::SendClicked);
    Counter = Text(TEXT("0 / 200"), 11); Content->AddChild(Counter);
    UTextBlock* NewLauncherLabel;
    Launcher = Button(bMobile ? TEXT("CHAT") : TEXT("Enter - chat"), NewLauncherLabel);
    LauncherLabel = NewLauncherLabel;
    Canvas->AddChild(Launcher);
    Launcher->OnClicked.AddDynamic(this, &UTownAgeChatWidget::OpenClicked);
    SetChatOpen(false);
}

void UTownAgeChatWidget::NativeTick(const FGeometry& Geometry, float DeltaTime)
{
    Super::NativeTick(Geometry, DeltaTime);
    // Local UMG units already include viewport DPI. SafeZone adds device cutout padding.
    const FVector2D Size = Geometry.GetLocalSize();
    const float ViewportScale = FMath::Max(.1f, UWidgetLayoutLibrary::GetViewportScale(this));
    const float TouchTarget = 48.f / ViewportScale;
    const float FontScale = bMobile ? TouchTarget / 48.f : 1.f;
    for (int32 I = 0; I < Labels.Num(); ++I)
    {
        FSlateFontInfo Font = Labels[I]->GetFont();
        const int32 Desired = FMath::RoundToInt(LabelFontSizes[I] * FontScale);
        if (Font.Size != Desired) { Font.Size = Desired; Labels[I]->SetFont(Font); }
    }
    const int32 InputSize = FMath::RoundToInt(16.f * FontScale);
    if (EntryStyle.TextStyle.Font.Size != InputSize)
    { EntryStyle.TextStyle.Font.Size = InputSize; Entry->SetWidgetStyle(EntryStyle); }
    for (USizeBox* ButtonSize : ButtonSizes)
    {
        ButtonSize->SetMinDesiredWidth(bMobile ? TouchTarget : 64.f);
        ButtonSize->SetMinDesiredHeight(bMobile ? TouchTarget : 32.f);
    }
    auto* PanelSlot = Cast<UCanvasPanelSlot>(Panel->Slot);
    auto* LauncherSlot = Cast<UCanvasPanelSlot>(Launcher->Slot);
    float Width = FMath::Min(430.f * FontScale, float(Size.X * (bMobile ? .65 : .6)));
    if (bMobile)
    {
        // Leave the top-center clock visible while the keyboard composer is open.
        const FTownAgeTouchLayout ScreenLayout(Size * ViewportScale);
        const float ClockHalfWidth = 90.f * FMath::Max(.85f, ScreenLayout.UIScale);
        Width = FMath::Min(Width, FMath::Max(0.f, float(Size.X * .42f) - (ClockHalfWidth + 12.f) / ViewportScale));
    }
    PanelSlot->SetAnchors(FAnchors(0, bMobile ? 0 : 1));
    PanelSlot->SetAlignment(FVector2D(0, bMobile ? 0 : 1));
    PanelSlot->SetPosition(FVector2D(bMobile ? Size.X * .08 : 20, bMobile ? 12 : -76));
    PanelSlot->SetSize(FVector2D(Width, FMath::Min(bMobile ? 340.f * FontScale : 260.f, float(Size.Y * (bMobile ? .48 : .65)))));
    LauncherSlot->SetAnchors(FAnchors(0, 1));
    LauncherSlot->SetAlignment(FVector2D(0, 1));
    // Above the joystick: movement controls occupy the bottom 228 screen pixels at 720p.
    const float Lift = bMobile ? Size.Y * .34f : 20.f;
    LauncherSlot->SetPosition(FVector2D(bMobile ? Size.X * .08f : 20.f, -Lift));
    LauncherSlot->SetSize(FVector2D(bMobile ? FMath::Max(112.f, TouchTarget * 1.7f) : 160.f, bMobile ? TouchTarget : 48.f));
}

void UTownAgeChatWidget::SetChatOpen(bool bInOpen)
{
    bOpen = bInOpen;
    Panel->SetVisibility(bMobile && !bOpen ? ESlateVisibility::Collapsed : ESlateVisibility::Visible);
    Composer->SetVisibility(bOpen ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    CloseButton->SetVisibility(bOpen ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    Counter->SetVisibility(bOpen ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
    Launcher->SetVisibility(bOpen ? ESlateVisibility::Collapsed : ESlateVisibility::Visible);
    if (bOpen) { Unread = 0; Scroll->ScrollToEnd(); }
    LauncherLabel->SetText(FText::FromString(bMobile ? TEXT("CHAT") : TEXT("Enter - chat")));
}

void UTownAgeChatWidget::FocusEntry() { Entry->SetUserFocus(GetOwningPlayer()); Entry->SetKeyboardFocus(); }
void UTownAgeChatWidget::OpenClicked() { if (auto* PC = ChatController()) PC->OpenChat(); }
void UTownAgeChatWidget::CloseClicked() { if (auto* PC = ChatController()) PC->CloseChat(); }

void UTownAgeChatWidget::SendClicked()
{
    if (auto* PC = ChatController())
    {
        if (PC->SubmitChat(Entry->GetText().ToString())) PC->CloseChat();
    }
}

void UTownAgeChatWidget::TextCommitted(const FText& Text, ETextCommit::Type Method)
{
    if (bOpen && Method == ETextCommit::OnEnter) SendClicked();
}

void UTownAgeChatWidget::ClearAcceptedDraft(const FString& Draft)
{
    if (Entry->GetText().ToString() == Draft)
    {
        Entry->SetText(FText::GetEmpty());
        TextChanged(FText::GetEmpty());
    }
}

void UTownAgeChatWidget::TextChanged(const FText& Text)
{
    const FString Value = Text.ToString();
    // Only truncate here: sanitizing each IME update would damage composition/spacing.
    if (Value.Len() > TownAgeChat::MaxLength)
    {
        FString Limited = Value.Left(TownAgeChat::MaxLength);
        if (Limited.Len() && Limited[Limited.Len() - 1] >= 0xD800 && Limited[Limited.Len() - 1] <= 0xDBFF)
            Limited.LeftChopInline(1);
        Entry->SetText(FText::FromString(Limited));
        TextChanged(FText::FromString(Limited));
        return;
    }
    Counter->SetText(FText::FromString(FString::Printf(TEXT("%d / 200"), Value.Len())));
}

FReply UTownAgeChatWidget::NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (bOpen && Event.GetKey() == EKeys::Escape) { CloseClicked(); return FReply::Handled(); }
    return Super::NativeOnPreviewKeyDown(Geometry, Event);
}

void UTownAgeChatWidget::AppendMessage(const FString& Sender, const FString& Message, bool bNotify)
{
    const bool bAtBottom = Scroll->GetScrollOffsetOfEnd() - Scroll->GetScrollOffset() < 20.f;
    UTextBlock* Line = WidgetTree->ConstructWidget<UTextBlock>();
    // Plain text avoids interpreting messages as rich text tags.
    Line->SetText(FText::FromString(Sender + TEXT(": ") + Message));
    Line->SetAutoWrapText(true);
    FSlateFontInfo Font = Line->GetFont();
    Font.Size = bMobile ? FMath::RoundToInt(15.f / FMath::Max(.1f, UWidgetLayoutLibrary::GetViewportScale(this))) : 15;
    Line->SetFont(Font);
    Line->SetColorAndOpacity(FSlateColor(FLinearColor(.95f, .96f, .91f)));
    Lines->AddChildToVerticalBox(Line)->SetPadding(FMargin(0, 2));
    if (Lines->GetChildrenCount() > TownAgeChat::HistoryLimit) Lines->RemoveChildAt(0);
    if (bAtBottom || !bOpen) Scroll->ScrollToEnd();
    if (bMobile && !bOpen && bNotify)
        LauncherLabel->SetText(FText::FromString(FString::Printf(TEXT("CHAT (%d)"), ++Unread)));
}
