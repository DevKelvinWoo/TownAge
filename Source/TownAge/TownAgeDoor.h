#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Subsystems/WorldSubsystem.h"
#include "TownAgeDoor.generated.h"

class APawn;
class ACharacter;
class UAnimSequence;
class UAnimationAsset;
class UPrimitiveComponent;
class ULevelStreaming;
class UTownAgeDoorPortalComponent;
class UTownAgeDoorTraversalComponent;

DECLARE_LOG_CATEGORY_EXTERN(LogTownAgeDoor, Log, All);

USTRUCT(BlueprintType)
struct TOWNAGE_API FTownAgeDoorTiming
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float ActionDuration = 3.6f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float StepStart = .4f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float StepEnd = 1.05f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float StepDistance = 22.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float TraverseStart = 1.65f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float TraverseEnd = 3.2f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float DoorOpenStart = .38f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float DoorPartOpenEnd = .95f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float DoorFullyOpen = 1.55f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float OpenYaw = 82.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float CloseDuration = .35f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float FadeDuration = .22f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float LoadTimeout = 8.f;
};

namespace TownAgeDoor
{
    TOWNAGE_API float SmoothFraction(float Time, float Start, float End);
    TOWNAGE_API float OpenFraction(float ActionTime, const FTownAgeDoorTiming& Timing);
    TOWNAGE_API bool IsTimingValid(const FTownAgeDoorTiming& Timing);
    TOWNAGE_API bool UsesActionAnimation(float ActionTime, const FTownAgeDoorTiming& Timing, bool bWalkDuringCrossing);
}

UENUM(BlueprintType)
enum class ETownAgeDoorPhase : uint8
{
    Idle,
    Align,
    Action,
    WaitReady,
    Closing
};

USTRUCT()
struct FTownAgeDoorTraversalState
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<UTownAgeDoorPortalComponent> Portal;
    UPROPERTY() ETownAgeDoorPhase Phase = ETownAgeDoorPhase::Idle;
    UPROPERTY() uint32 SequenceId = 0;
    UPROPERTY() double PhaseStartTime = 0.;
    UPROPERTY() double ActionStartTime = 0.;
    UPROPERTY() float AlignDuration = 0.f;
    UPROPERTY() FTransform Origin;
    UPROPERTY() bool bOriginInteriorLighting = false;
};

USTRUCT()
struct FTownAgeDoorVisualState
{
    GENERATED_BODY()
    // A remote-side client may not have the participant pawn relevant at 500m.
    UPROPERTY() bool bReserved = false;
    UPROPERTY() TObjectPtr<APawn> Participant;
    UPROPERTY() double ActionStartTime = -1.;
    UPROPERTY() double CloseStartTime = -1.;
    UPROPERTY() uint32 SequenceId = 0;
};

// Reservation scope spans both sides of one authored doorway.
UCLASS()
class TOWNAGE_API UTownAgeDoorSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    void RegisterPortal(UTownAgeDoorPortalComponent* Portal);
    void UnregisterPortal(UTownAgeDoorPortalComponent* Portal);
    bool IsReserved(FName PortalId) const;
    bool Reserve(UTownAgeDoorPortalComponent* Portal, UTownAgeDoorTraversalComponent* Traversal);
    void StartAction(FName PortalId, UTownAgeDoorTraversalComponent* Traversal, double Time, uint32 SequenceId);
    void StartClose(FName PortalId, UTownAgeDoorTraversalComponent* Traversal, double Time);
    void Release(FName PortalId, UTownAgeDoorTraversalComponent* Traversal, double Time);
private:
    TArray<TWeakObjectPtr<UTownAgeDoorPortalComponent>> Portals;
    TMap<FName, TWeakObjectPtr<UTownAgeDoorTraversalComponent>> Reservations;
};

UCLASS(ClassGroup=(TownAge), meta=(BlueprintSpawnableComponent))
class TOWNAGE_API UTownAgeDoorPortalComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UTownAgeDoorPortalComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Door") FName PortalId = TEXT("CozyHouse01");
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Door") bool bInteriorSide = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Door") FName DoorHingeName = TEXT("DoorHinge");
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Door") FName DoorLeafName = TEXT("DoorLeaf");
    // Transforms are relative to the owner and refer to the capsule center.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Door") FTransform LocalAlignTransform;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Door") FTransform LocalEndTransform;
    // Authored absolute destination; never supplied by a client request.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Door") FTransform DestinationTransform;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Door") TSoftObjectPtr<UWorld> InteriorLevel;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Door") TSoftObjectPtr<UAnimSequence> ActionAnimation;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Door") FTownAgeDoorTiming Timing;
    // Release the opening pose directly into velocity-driven locomotion.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Door") bool bWalkDuringCrossing = false;

    UFUNCTION(BlueprintPure, Category="Door") bool CanUse(const APawn* Pawn) const;
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Door") bool TryStart(APawn* Pawn);
    FTransform GetWorldAlignTransform() const;
    FTransform GetWorldEndTransform() const;
    UPrimitiveComponent* GetDoorLeaf() const;
    ULevelStreaming* GetInteriorStreamingLevel() const;
    UAnimSequence* GetLoadedAnimation() const { return CachedActionAnimation; }
    UAnimSequence* LoadActionAnimation();
    void PrepareInterior();
    void SetVisualState(const FTownAgeDoorVisualState& NewState);
    const FTownAgeDoorVisualState& GetVisualState() const { return VisualState; }
private:
    UPROPERTY(Replicated) FTownAgeDoorVisualState VisualState;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> CachedActionAnimation;
    FQuat ClosedHingeRotation = FQuat::Identity;
    TWeakObjectPtr<class USceneComponent> Hinge;
};

UCLASS(ClassGroup=(TownAge), meta=(BlueprintSpawnableComponent))
class TOWNAGE_API UTownAgeDoorTraversalComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UTownAgeDoorTraversalComponent();
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UFUNCTION(BlueprintPure, Category="Door") bool IsBusy() const { return State.Phase != ETownAgeDoorPhase::Idle; }
    UFUNCTION(BlueprintPure, Category="Door") ETownAgeDoorPhase GetPhase() const { return State.Phase; }
    UFUNCTION(BlueprintPure, Category="Door") UAnimSequence* GetActiveAnimation() const;
    UFUNCTION(BlueprintPure, Category="Door") float GetAnimationTime() const;
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Door") bool ServerStart(UTownAgeDoorPortalComponent* Portal);
    void CancelTraversal(bool bRestoreOrigin = true);
    const FTownAgeDoorTraversalState& GetState() const { return State; }
private:
    UPROPERTY(ReplicatedUsing=OnRep_State) FTownAgeDoorTraversalState State;
    // Per-pawn lighting keeps village sunlight out of the streamed interior.
    UPROPERTY(Replicated) bool bInteriorLighting = false;
    UFUNCTION() void OnRep_State();
    UFUNCTION(Client, Reliable) void ClientTransfer(FTransform Destination, uint32 SequenceId);
    void SetPhase(ETownAgeDoorPhase Phase);
    void ApplyMove(FName Name, FVector Start, FVector Target, float Duration, float Elapsed);
    void StopMove();
    void UpdateMovement(float DeltaTime);
    void UpdateCosmetics();
    void RestoreAnimation();
    void UpdateLeafIgnore(bool bIgnore);
    bool IsRoomReady() const;
    void Finish();
    double ServerTime() const;
    uint16 MoveSourceId = 0;
    uint32 MovementSequenceId = 0;
    ETownAgeDoorPhase MovementPhase = ETownAgeDoorPhase::Idle;
    bool bStepStarted = false;
    bool bTraverseStarted = false;
    bool bSavedOrientToMovement = true;
    bool bSavedCameraLag = false;
    bool bSavedCameraCollision = true;
    bool bApplyingFade = false;
    bool bLightingInitialized = false;
    bool bAppliedInteriorLighting = false;
    int32 CameraLagResetFrames = 0;
    UPROPERTY() TObjectPtr<UAnimationAsset> SavedAnimation;
    bool bSavedLooping = true;
    float SavedPlayRate = 1.f;
    TWeakObjectPtr<UPrimitiveComponent> IgnoredLeaf;
};
