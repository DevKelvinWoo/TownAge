#pragma once
#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "TownAgePlayerController.generated.h"

UCLASS()
class TOWNAGE_API ATownAgePlayerController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void SetupInputComponent() override;
    bool IsChatOpen() const { return bChatOpen; }
    void OpenChat();
    void CloseChat();
    bool SubmitChat(const FString& Message);
    UFUNCTION(Server, Reliable)
    void ServerSendChat(const FString& Message);
    UFUNCTION(Client, Reliable)
    void ClientReceiveChat(const FString& Sender, const FString& Message, bool bOwnMessage);
    UFUNCTION(Client, Reliable)
    void ClientChatResult(bool bAccepted, const FString& Notice);
private:
    UPROPERTY(Transient)
    TObjectPtr<class UTownAgeChatWidget> ChatWidget;
    bool bChatOpen = false;
    bool bPreviousCursor = false;
    double LastChatTime = -DBL_MAX;
    bool bChatPending = false;
    FString PendingDraft;
};
