#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameModeBase.h"
#include "TownAgeStamina.h"
#include "TownAgePlayer.generated.h"

UCLASS()
class TOWNAGE_API ATownAgePlayer : public ACharacter
{
    GENERATED_BODY()
public:
    ATownAgePlayer();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    // Used by the editor import pipeline to serialize valid Blend Space interpolation data.
    UFUNCTION(BlueprintCallable, Category="TownAge|Animation")
    static bool RebuildWalkBlendSpace(class UBlendSpace1D* BlendSpace);
    UFUNCTION(BlueprintPure, Category="TownAge|Animation")
    static FVector2D GetWalkBlendWeights(class UBlendSpace1D* BlendSpace, float Speed);
    UFUNCTION(BlueprintPure, Category="TownAge|Animation")
    static FVector GetLocomotionSampleWeights(class UBlendSpace1D* BlendSpace, float Speed);
    bool UsesTouchControls() const;
    bool IsSprintControlHeld() const;
    FVector2D TouchMove = FVector2D::ZeroVector;
private:
    void UpdateTouchControls(class APlayerController* PC);
    int32 MoveFinger = INDEX_NONE;
    int32 SprintFinger = INDEX_NONE;
    bool bTouchSprintHeld = false;
public:
    UPROPERTY(Replicated, BlueprintReadOnly, Category="Stamina")
    float Stamina = 100.f;
    UPROPERTY(Replicated, BlueprintReadOnly, Category="Stamina")
    bool bExhausted = false;
    UPROPERTY(Replicated, BlueprintReadOnly, Category="Stamina")
    bool bSprinting = false;
private:
    UFUNCTION(Server, Reliable)
    void ServerSetSprintRequested(bool bRequested);
    bool bSprintRequested = false;
    bool bLastSentSprintRequest = false;
    FTownAgeStamina StaminaState;
    bool bAnimationMoving = false;
    UPROPERTY()
    TObjectPtr<class UBlendSpace1D> WalkBlendSpace;
protected:
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Camera")
    TObjectPtr<class USpringArmComponent> CameraBoom;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Camera")
    TObjectPtr<class UCameraComponent> FollowCamera;
};

UCLASS()
class TOWNAGE_API ATownAgeGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    ATownAgeGameMode();
};
