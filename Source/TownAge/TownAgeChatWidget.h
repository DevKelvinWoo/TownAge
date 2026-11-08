#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateTypes.h"
#include "TownAgeChatWidget.generated.h"

UCLASS()
class TOWNAGE_API UTownAgeChatWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetChatOpen(bool bOpen);
    void FocusEntry();
    void ClearAcceptedDraft(const FString& Draft);
    void AppendMessage(const FString& Sender, const FString& Message, bool bNotify = true);
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaTime) override;
    virtual FReply NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
private:
    UFUNCTION() void OpenClicked();
    UFUNCTION() void CloseClicked();
    UFUNCTION() void SendClicked();
    UFUNCTION() void TextCommitted(const FText& Text, ETextCommit::Type Method);
    UFUNCTION() void TextChanged(const FText& Text);
    class ATownAgePlayerController* ChatController() const;
    UPROPERTY() TObjectPtr<class UBorder> Panel;
    UPROPERTY() TObjectPtr<class UVerticalBox> Lines;
    UPROPERTY() TObjectPtr<class UScrollBox> Scroll;
    UPROPERTY() TObjectPtr<class UEditableTextBox> Entry;
    UPROPERTY() TObjectPtr<class UHorizontalBox> Composer;
    UPROPERTY() TObjectPtr<class UButton> Launcher;
    UPROPERTY() TObjectPtr<class UTextBlock> LauncherLabel;
    UPROPERTY() TObjectPtr<class UButton> CloseButton;
    UPROPERTY() TObjectPtr<class UTextBlock> Counter;
    UPROPERTY() TArray<TObjectPtr<class USizeBox>> ButtonSizes;
    UPROPERTY() TArray<TObjectPtr<class UTextBlock>> Labels;
    TArray<int32> LabelFontSizes;
    // UE 5.8 SetWidgetStyle forwards the caller's address to Slate. Keep it alive.
    FEditableTextBoxStyle EntryStyle;
    bool bMobile = false;
    bool bOpen = false;
    int32 Unread = 0;
};
