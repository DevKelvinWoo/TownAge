#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "TownAgeCosmeticModules.h"
#include "TownAgeCustomizationComponent.generated.h"

class UTownAgeInteractionTargetComponent;
class UTownAgeCustomizationWidget;
class ULevelStreamingDynamic;
class ATownAgeCustomizationPreview;
class AController;
class APlayerController;
class UMaterialInterface;
class UAnimationAsset;

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
    // Each avatar can author its own masked dye parents; never reuse another
    // model's atlas merely because it shares a skeleton.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="TownAge|Customization")
    TMap<int32, TObjectPtr<UMaterialInterface>> HairDyeMaterials;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="TownAge|Customization")
    TSoftObjectPtr<UAnimationAsset> PreviewIdleAnimation;
    UFUNCTION(BlueprintCallable, Category="TownAge|Customization")
    void SetFaceView(bool bFaceView);
    UFUNCTION(BlueprintPure, Category="TownAge|Customization")
    bool CanDyeHair() const;
    UFUNCTION(BlueprintPure, Category="TownAge|Customization")
    bool CanApplyMakeup() const;
    UFUNCTION(BlueprintPure, Category="TownAge|Customization")
    FTownAgeMakeupState GetMakeupState() const { return MakeupState; }
    UFUNCTION(BlueprintPure, Category="TownAge|Customization")
    ETownAgeCosmeticCategory GetCategory() const;
    UFUNCTION(BlueprintCallable, Category="TownAge|Customization")
    void SetCategory(ETownAgeCosmeticCategory Category);
    UFUNCTION(BlueprintCallable, Category="TownAge|Customization")
    void ChooseMakeup(const FTownAgeMakeupState& State);
    UFUNCTION(BlueprintCallable, Category="TownAge|Customization")
    void ChooseHairColor(uint8 ColorIndex);
    UFUNCTION(BlueprintCallable, Category="TownAge|Customization")
    void CloseCustomization();

private:
    UPROPERTY(ReplicatedUsing=OnRep_HairColorIndex)
    uint8 HairColorIndex = 0;
    UPROPERTY(ReplicatedUsing=OnRep_MakeupState)
    FTownAgeMakeupState MakeupState;
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
    bool bFaceViewRequested = false;
    bool bPreviousCursor = false;
    EMovementMode PreviousMovementMode = MOVE_Walking;
    uint8 PreviousCustomMovementMode = 0;
    double PreviewLoadStarted = 0.;
    uint32 ServerSessionId = 0;
    uint32 LocalSessionId = 0;
    uint8 LocalAllowedCategories = 7;
    ETownAgeCosmeticCategory LocalCategory = ETownAgeCosmeticCategory::Dye;
    ETownAgeCosmeticCategory ServerCategory = ETownAgeCosmeticCategory::Dye;

    UFUNCTION() void OnRep_HairColorIndex();
    UFUNCTION() void OnRep_MakeupState();
    UFUNCTION(Client, Reliable) void ClientBeginCustomization(uint32 SessionId, uint8 AllowedCategories);
    UFUNCTION(Client, Reliable) void ClientEndCustomization(uint32 SessionId);
    UFUNCTION(Client, Reliable) void ClientConfirmHairColor(uint32 SessionId, uint8 ColorIndex);
    UFUNCTION(Server, Reliable) void ServerChooseHairColor(uint32 SessionId, uint8 ColorIndex);
    UFUNCTION(Server, Reliable) void ServerSelectCategory(uint32 SessionId, ETownAgeCosmeticCategory Category);
    UFUNCTION(Server, Reliable) void ServerChooseMakeup(uint32 SessionId, FTownAgeMakeupState State);
    UFUNCTION(Client, Reliable) void ClientConfirmMakeup(uint32 SessionId, FTownAgeMakeupState State);
    UFUNCTION(Server, Reliable) void ServerCloseCustomization(uint32 SessionId);
    bool IsSessionTargetValid() const;
    void EndServerSession();
    void CleanupLocalPreview();
    void UpdateLocalPreview();
    void ApplyCharacterHairColor();
    void ApplyCharacterMakeup();
    bool IsCategoryAllowed(ETownAgeCosmeticCategory Category) const;
};
