#include "TownAgePlayerController.h"
#include "TownAgeChatWidget.h"
#include "TownAgeChat.h"
#include "GameFramework/PlayerState.h"
#include "Engine/World.h"
#include "Components/InputComponent.h"
#include "InputCoreTypes.h"

void ATownAgePlayerController::BeginPlay()
{
    Super::BeginPlay();
    if (IsLocalController() && GetNetMode() != NM_DedicatedServer)
    {
        ChatWidget = CreateWidget<UTownAgeChatWidget>(this);
        if (ChatWidget) ChatWidget->AddToPlayerScreen(20);
    }
}

void ATownAgePlayerController::EndPlay(const EEndPlayReason::Type Reason)
{
    if (ChatWidget) ChatWidget->RemoveFromParent();
    Super::EndPlay(Reason);
}

void ATownAgePlayerController::SetupInputComponent()
{
    Super::SetupInputComponent();
    InputComponent->BindKey(EKeys::Enter, IE_Pressed, this, &ATownAgePlayerController::OpenChat);
}

void ATownAgePlayerController::OpenChat()
{
    if (!ChatWidget || bChatOpen) return;
    bChatOpen = true;
    bPreviousCursor = bShowMouseCursor;
    bShowMouseCursor = true;
    SetIgnoreMoveInput(true);
    SetIgnoreLookInput(true);
    ChatWidget->SetChatOpen(true);
    FInputModeUIOnly Mode;
    Mode.SetWidgetToFocus(ChatWidget->TakeWidget());
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    SetInputMode(Mode);
    ChatWidget->FocusEntry();
}

void ATownAgePlayerController::CloseChat()
{
    if (!bChatOpen) return;
    bChatOpen = false;
    SetIgnoreMoveInput(false);
    SetIgnoreLookInput(false);
    bShowMouseCursor = bPreviousCursor;
    SetInputMode(FInputModeGameOnly());
    FlushPressedKeys();
    if (ChatWidget) ChatWidget->SetChatOpen(false);
}

bool ATownAgePlayerController::SubmitChat(const FString& Message)
{
    const FString Clean = TownAgeChat::Sanitize(Message);
    if (Clean.IsEmpty() || bChatPending) return false;
    PendingDraft = Message;
    bChatPending = true;
    ServerSendChat(Clean);
    return true;
}

void ATownAgePlayerController::ServerSendChat_Implementation(const FString& Message)
{
    if (!PlayerState || !GetWorld())
    { ClientChatResult(false, TEXT("Chat is not ready yet.")); return; }
    // Oversized requests are rejected rather than allocating unbounded display history.
    if (Message.Len() > TownAgeChat::MaxLength)
    { ClientChatResult(false, TEXT("Message too long (200 characters maximum).")); return; }
    const FString Clean = TownAgeChat::Sanitize(Message);
    if (Clean.IsEmpty()) { ClientChatResult(false, TEXT("Message is empty.")); return; }
    const double Now = GetWorld()->GetTimeSeconds();
    if (!TownAgeChat::CanSend(Now, LastChatTime))
    { ClientChatResult(false, TEXT("Please wait a moment before sending again. Your draft was kept.")); return; }
    LastChatTime = Now;
    ClientChatResult(true, FString());
    FString Sender = TownAgeChat::Sanitize(PlayerState->GetPlayerName(), 32);
    if (Sender.IsEmpty()) Sender = FString::Printf(TEXT("Player %d"), PlayerState->GetPlayerId());
    for (FConstPlayerControllerIterator It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (ATownAgePlayerController* Recipient = Cast<ATownAgePlayerController>(It->Get()))
            Recipient->ClientReceiveChat(Sender, Clean, Recipient == this);
}

void ATownAgePlayerController::ClientReceiveChat_Implementation(const FString& Sender, const FString& Message, bool bOwnMessage)
{
    if (ChatWidget) ChatWidget->AppendMessage(Sender, Message, !bOwnMessage);
}

void ATownAgePlayerController::ClientChatResult_Implementation(bool bAccepted, const FString& Notice)
{
    if (ChatWidget)
    {
        if (bAccepted) ChatWidget->ClearAcceptedDraft(PendingDraft);
        else if (!Notice.IsEmpty()) ChatWidget->AppendMessage(TEXT("TownAge"), Notice);
    }
    PendingDraft.Reset();
    bChatPending = false;
}
