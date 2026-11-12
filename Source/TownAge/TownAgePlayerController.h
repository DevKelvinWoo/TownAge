#pragma once
#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "TownAgePlayerController.generated.h"

UENUM(BlueprintType)
enum class ETownAgeLightingPreview : uint8
{
    Morning,
    Noon,
    Evening,
    Night
};

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
    UFUNCTION(BlueprintCallable, Category="TownAge|Development")
    void ToggleLightingPreview();
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="TownAge|Development")
    bool SetLightingPreviewTime(ETownAgeLightingPreview Period);
    void CloseLightingPreview();
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
    UPROPERTY(Transient)
    TObjectPtr<class UTownAgeLightingPreviewWidget> LightingPreviewWidget;
    bool bLightingPreviousCursor = false;
    bool bChatOpen = false;
    bool bPreviousCursor = false;
    double LastChatTime = -DBL_MAX;
    bool bChatPending = false;
    FString PendingDraft;
};
