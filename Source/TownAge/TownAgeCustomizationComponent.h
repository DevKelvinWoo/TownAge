#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "TownAgeCustomizationComponent.generated.h"

class UTownAgeInteractionTargetComponent;
class UTownAgeCustomizationWidget;
class ULevelStreamingDynamic;
class ATownAgeCustomizationPreview;
class AController;
class APlayerController;

DECLARE_LOG_CATEGORY_EXTERN(LogTownAgeCustomization, Log, All);

// Appearance is authoritative gameplay state; the streamed preview is local UI.
UCLASS(ClassGroup=(TownAge), meta=(BlueprintSpawnableComponent))
class TOWNAGE_API UTownAgeCustomizationComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UTownAgeCustomizationComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    bool ServerBegin(UTownAgeInteractionTargetComponent* Target);
    UFUNCTION(BlueprintPure, Category="TownAge|Customization")
    bool IsCustomizationOpen() const { return bLocalOpen || bServerSessionActive; }
    UFUNCTION(BlueprintPure, Category="TownAge|Customization")
    bool IsServerSessionActive() const { return bServerSessionActive; }
    UFUNCTION(BlueprintPure, Category="TownAge|Customization")
    uint8 GetHairColorIndex() const { return HairColorIndex; }
    UFUNCTION(BlueprintPure, Category="TownAge|Customization")
    ATownAgeCustomizationPreview* GetPreviewActor() const { return PreviewActor; }
    UFUNCTION(BlueprintPure, Category="TownAge|Customization")
    bool IsPreviewReady() const { return bPreviewPresented; }
    UFUNCTION(BlueprintCallable, Category="TownAge|Customization")
    void ChooseHairColor(uint8 ColorIndex);
    UFUNCTION(BlueprintCallable, Category="TownAge|Customization")
    void CloseCustomization();

private:
    UPROPERTY(ReplicatedUsing=OnRep_HairColorIndex)
    uint8 HairColorIndex = 0;
    UPROPERTY(Replicated)
    bool bServerSessionActive = false;
    UPROPERTY(Transient)
    TObjectPtr<UTownAgeCustomizationWidget> Widget;
    UPROPERTY(Transient)
    TObjectPtr<ULevelStreamingDynamic> PreviewLevel;
    UPROPERTY(Transient)
    TObjectPtr<ATownAgeCustomizationPreview> PreviewActor;
    TWeakObjectPtr<UTownAgeInteractionTargetComponent> SessionTarget;
    TWeakObjectPtr<AController> SessionController;
    TWeakObjectPtr<APlayerController> LocalController;
    bool bLocalOpen = false;
    bool bPreviewPresented = false;
    bool bPreviousCursor = false;
    EMovementMode PreviousMovementMode = MOVE_Walking;
    uint8 PreviousCustomMovementMode = 0;
    double PreviewLoadStarted = 0.;
    uint32 ServerSessionId = 0;
    uint32 LocalSessionId = 0;

    UFUNCTION() void OnRep_HairColorIndex();
    UFUNCTION(Client, Reliable) void ClientBeginCustomization(uint32 SessionId);
    UFUNCTION(Client, Reliable) void ClientEndCustomization(uint32 SessionId);
    UFUNCTION(Client, Reliable) void ClientConfirmHairColor(uint32 SessionId, uint8 ColorIndex);
    UFUNCTION(Server, Reliable) void ServerChooseHairColor(uint32 SessionId, uint8 ColorIndex);
    UFUNCTION(Server, Reliable) void ServerCloseCustomization(uint32 SessionId);
    bool IsSessionTargetValid() const;
    void EndServerSession();
    void CleanupLocalPreview();
    void UpdateLocalPreview();
};
