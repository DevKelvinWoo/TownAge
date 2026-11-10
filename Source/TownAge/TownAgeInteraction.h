#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Engine/DataTable.h"
#include "Subsystems/WorldSubsystem.h"
#include "TownAgeInteraction.generated.h"

class APawn;
class UTownAgeInteractionTargetComponent;

DECLARE_LOG_CATEGORY_EXTERN(LogTownAgeInteraction, Log, All);

UENUM(BlueprintType)
enum class ETownAgeInteractionAction : uint8
{
    LogOnly,
    DoorTransition,
    OpenCustomization
};

USTRUCT(BlueprintType)
struct TOWNAGE_API FTownAgeInteractionRow : public FTableRowBase
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    FText Prompt = NSLOCTEXT("TownAge", "InteractionDefault", "Interact");

    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1.0", Units="cm"))
    float InteractionDistance = 200.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.0", Units="cm"))
    float MaxVerticalDistance = 150.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.0", ClampMax="180.0", Units="deg"))
    float MaxFacingAngleDegrees = 100.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    ETownAgeInteractionAction Action = ETownAgeInteractionAction::LogOnly;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    FName LogEvent = TEXT("Interact");
};

namespace TownAgeInteraction
{
    struct TOWNAGE_API FCandidateScore
    {
        double FacingDot = -1.;
        double DistanceSquared = 0.;
    };

    // Planar facing is independent of the elevated cozy camera and target height.
    TOWNAGE_API bool EvaluateCandidate(const FVector& Origin, const FVector& Forward,
        const FVector& Point, const FTownAgeInteractionRow& Definition, FCandidateScore& Score);
    TOWNAGE_API bool IsPreferred(const FCandidateScore& Candidate, const FString& CandidateKey,
        const FCandidateScore& Current, const FString& CurrentKey);
    TOWNAGE_API bool IsApproachAllowed(const FVector& Point, const FVector& WorldApproachDirection,
        const FVector& InteractorLocation);
}

// Only registered components are searched; no per-player world actor scans.
UCLASS()
class TOWNAGE_API UTownAgeInteractionSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    void RegisterTarget(UTownAgeInteractionTargetComponent* Target);
    void UnregisterTarget(UTownAgeInteractionTargetComponent* Target);
    UTownAgeInteractionTargetComponent* SelectTarget(const APawn* Interactor) const;
private:
    TArray<TWeakObjectPtr<UTownAgeInteractionTargetComponent>> Targets;
};

UCLASS(Blueprintable, ClassGroup=(TownAge), meta=(BlueprintSpawnableComponent))
class TOWNAGE_API UTownAgeInteractionTargetComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UTownAgeInteractionTargetComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Interaction")
    FDataTableRowHandle Definition;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Interaction")
    FVector LocalInteractionPoint = FVector(0, 0, 90);

    // Zero permits all sides. A door can use its outward normal to require
    // the player to stand in front of the authored interaction point.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Interaction")
    FVector LocalApproachDirection = FVector::ZeroVector;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Replicated, Category="Interaction")
    bool bInteractionEnabled = true;

    UFUNCTION(BlueprintPure, Category="Interaction")
    FVector GetInteractionPoint() const;

    const FTownAgeInteractionRow* GetDefinition() const;
    bool CanInteract(const APawn* Interactor) const;

    // Later target subclasses can implement their own server-side action.
    UFUNCTION(BlueprintNativeEvent, BlueprintAuthorityOnly, Category="Interaction")
    void ExecuteInteraction(APawn* Interactor);
    virtual void ExecuteInteraction_Implementation(APawn* Interactor);
};

UCLASS(ClassGroup=(TownAge), meta=(BlueprintSpawnableComponent))
class TOWNAGE_API UTownAgeInteractionComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UTownAgeInteractionComponent();
    virtual void TickComponent(float DeltaTime, ELevelTick TickType,
        FActorComponentTickFunction* ThisTickFunction) override;

    UFUNCTION(BlueprintPure, Category="Interaction")
    UTownAgeInteractionTargetComponent* GetSelectedTarget() const;

    UFUNCTION(BlueprintPure, Category="Interaction")
    bool HasInteractable() const;

    UFUNCTION(BlueprintPure, Category="Interaction")
    FText GetPrompt() const;

    UFUNCTION(BlueprintCallable, Category="Interaction")
    void RefreshSelection();

    UFUNCTION(BlueprintCallable, Category="Interaction")
    void TryInteract();

private:
    UFUNCTION(Server, Reliable)
    void ServerInteract(UTownAgeInteractionTargetComponent* RequestedTarget);

    TWeakObjectPtr<UTownAgeInteractionTargetComponent> SelectedTarget;
    double LastServerRequestTime = -1.e30;
};
