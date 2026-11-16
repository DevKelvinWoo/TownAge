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
    virtual void PlayerTick(float DeltaTime) override;
    bool IsChatOpen() const { return bChatOpen; }
    bool IsLightingPreviewOpen() const { return LightingPreviewWidget != nullptr; }
    void OpenChat();
    void CloseChat();
    UFUNCTION(BlueprintCallable, Category="TownAge|Development")
    void ToggleLightingPreview();
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="TownAge|Development")
    bool SetLightingPreviewTime(ETownAgeLightingPreview Period);
    void CloseLightingPreview();
    // Development-only intent path shared by the mouse shortcut and editor verification.
    // True means accepted on authority, or submitted to authority on a client.
    UFUNCTION(BlueprintCallable, Category="TownAge|Development")
    bool RequestDebugTeleportAt(const FVector& SurfacePoint);
    UPROPERTY(Transient, BlueprintReadOnly, Category="TownAge|Development")
    bool bLastDebugTeleportSucceeded = false;
    UPROPERTY(Transient, BlueprintReadOnly, Category="TownAge|Development")
    FString LastDebugTeleportNotice;
    // UI owners release the temporary debug cursor before saving their own
    // previous-cursor state. False defers handoff until that owner is ready.
    void ReleaseDebugTeleportCursor(bool bRestoreInput = true);
    bool SubmitChat(const FString& Message);
    UFUNCTION(Server, Reliable)
    void ServerSendChat(const FString& Message);
    UFUNCTION(Client, Reliable)
    void ClientReceiveChat(const FString& Sender, const FString& Message, bool bOwnMessage);
    UFUNCTION(Client, Reliable)
    void ClientChatResult(bool bAccepted, const FString& Notice);
private:
    void HandleCameraWheel(float Delta);
    void HandleDebugTeleportClick();
    bool TryDebugTeleport(const FVector& SurfacePoint, FString& Notice);
    UFUNCTION(Server, Reliable)
    void ServerDebugTeleport(const FVector& SurfacePoint);
    UFUNCTION(Client, Reliable)
    void ClientDebugTeleportResult(bool bAccepted, const FString& Notice);
    bool bDebugTeleportCursor = false;
    bool bDebugPreviousCursor = false;
    double LastDebugTeleportTime = -DBL_MAX;
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
