#include "TownAgeInteraction.h"

#include "GameFramework/Pawn.h"
#include "Net/UnrealNetwork.h"
#include "TownAgePlayer.h"
#include "TownAgeDoor.h"
#include "TownAgeCustomizationComponent.h"

DEFINE_LOG_CATEGORY(LogTownAgeInteraction);

bool TownAgeInteraction::EvaluateCandidate(const FVector& Origin, const FVector& Forward,
    const FVector& Point, const FTownAgeInteractionRow& Definition, FCandidateScore& Score)
{
    if (Origin.ContainsNaN() || Forward.ContainsNaN() || Point.ContainsNaN()
        || !FMath::IsFinite(Definition.InteractionDistance) || Definition.InteractionDistance <= 0.f
        || !FMath::IsFinite(Definition.MaxVerticalDistance) || Definition.MaxVerticalDistance < 0.f
        || !FMath::IsFinite(Definition.MaxFacingAngleDegrees)
        || Definition.MaxFacingAngleDegrees < 0.f || Definition.MaxFacingAngleDegrees > 180.f)
        return false;

    const FVector Delta = Point - Origin;
    if (FMath::Abs(Delta.Z) > Definition.MaxVerticalDistance)
        return false;

    Score.DistanceSquared = Delta.SizeSquared2D();
    if (Score.DistanceSquared > FMath::Square(double(Definition.InteractionDistance)))
        return false;

    const FVector Facing = Forward.GetSafeNormal2D();
    if (Facing.IsNearlyZero())
        return false;

    Score.FacingDot = Score.DistanceSquared <= UE_DOUBLE_SMALL_NUMBER
        ? 1. : FMath::Clamp(FVector::DotProduct(Facing, Delta.GetSafeNormal2D()), -1., 1.);
    const double MinimumDot = FMath::Cos(FMath::DegreesToRadians(double(Definition.MaxFacingAngleDegrees)));
    return Score.FacingDot + UE_DOUBLE_SMALL_NUMBER >= MinimumDot;
}

bool TownAgeInteraction::IsPreferred(const FCandidateScore& Candidate, const FString& CandidateKey,
    const FCandidateScore& Current, const FString& CurrentKey)
{
    if (!FMath::IsNearlyEqual(Candidate.FacingDot, Current.FacingDot, 1.e-6))
        return Candidate.FacingDot > Current.FacingDot;
    if (!FMath::IsNearlyEqual(Candidate.DistanceSquared, Current.DistanceSquared, 1.e-4))
        return Candidate.DistanceSquared < Current.DistanceSquared;
    return CandidateKey < CurrentKey;
}

bool TownAgeInteraction::IsApproachAllowed(const FVector& Point, const FVector& WorldApproachDirection,
    const FVector& InteractorLocation)
{
    if (Point.ContainsNaN() || WorldApproachDirection.ContainsNaN() || InteractorLocation.ContainsNaN())
        return false;
    const FVector Direction = WorldApproachDirection.GetSafeNormal2D();
    return Direction.IsNearlyZero()
        || FVector::DotProduct(InteractorLocation - Point, Direction) >= 0.;
}

void UTownAgeInteractionSubsystem::RegisterTarget(UTownAgeInteractionTargetComponent* Target)
{
    Targets.RemoveAll([](const auto& Entry) { return !Entry.IsValid(); });
    Targets.AddUnique(Target);
}

void UTownAgeInteractionSubsystem::UnregisterTarget(UTownAgeInteractionTargetComponent* Target)
{
    Targets.RemoveAll([Target](const auto& Entry) { return !Entry.IsValid() || Entry.Get() == Target; });
}

UTownAgeInteractionTargetComponent* UTownAgeInteractionSubsystem::SelectTarget(const APawn* Interactor) const
{
    if (!IsValid(Interactor))
        return nullptr;

    UTownAgeInteractionTargetComponent* Best = nullptr;
    TownAgeInteraction::FCandidateScore BestScore;
    FString BestKey;
    for (const auto& Entry : Targets)
    {
        auto* Target = Entry.Get();
        if (!Target || Target->GetWorld() != GetWorld() || Target->GetOwner() == Interactor
            || !Target->CanInteract(Interactor))
            continue;
        TownAgeInteraction::FCandidateScore Score;
        const auto* Definition = Target->GetDefinition();
        if (!Definition || !TownAgeInteraction::EvaluateCandidate(Interactor->GetActorLocation(),
            Interactor->GetActorForwardVector(), Target->GetInteractionPoint(), *Definition, Score))
            continue;
        const FString Key = Target->GetPathName();
        if (!Best || TownAgeInteraction::IsPreferred(Score, Key, BestScore, BestKey))
        {
            Best = Target;
            BestScore = Score;
            BestKey = Key;
        }
    }
    return Best;
}

UTownAgeInteractionTargetComponent::UTownAgeInteractionTargetComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
    SetIsReplicatedByDefault(true);
}

void UTownAgeInteractionTargetComponent::BeginPlay()
{
    Super::BeginPlay();
    if (auto* Registry = GetWorld()->GetSubsystem<UTownAgeInteractionSubsystem>())
        Registry->RegisterTarget(this);
}

void UTownAgeInteractionTargetComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    if (GetWorld())
        if (auto* Registry = GetWorld()->GetSubsystem<UTownAgeInteractionSubsystem>())
            Registry->UnregisterTarget(this);
    Super::EndPlay(EndPlayReason);
}

void UTownAgeInteractionTargetComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UTownAgeInteractionTargetComponent, bInteractionEnabled);
}

FVector UTownAgeInteractionTargetComponent::GetInteractionPoint() const
{
    return GetOwner() ? GetOwner()->GetActorTransform().TransformPosition(LocalInteractionPoint) : FVector::ZeroVector;
}

const FTownAgeInteractionRow* UTownAgeInteractionTargetComponent::GetDefinition() const
{
    if (!Definition.DataTable || Definition.RowName.IsNone()
        || Definition.DataTable->GetRowStruct() != FTownAgeInteractionRow::StaticStruct())
        return nullptr;
    return Definition.GetRow<FTownAgeInteractionRow>(TEXT("TownAgeInteraction"));
}

bool UTownAgeInteractionTargetComponent::CanInteract(const APawn* Interactor) const
{
    if (!bInteractionEnabled || !IsValid(GetOwner()) || !IsValid(Interactor)
        || GetOwner()->IsActorBeingDestroyed() || Interactor->GetWorld() != GetWorld())
        return false;
    if (const auto* Player = Cast<ATownAgePlayer>(Interactor); Player && (Player->IsDoorBusy() || Player->IsCustomizing()))
        return false;
    const auto* Row = GetDefinition();
    if (Row && Row->Action == ETownAgeInteractionAction::DoorTransition)
    {
        const auto* Portal = GetOwner()->FindComponentByClass<UTownAgeDoorPortalComponent>();
        if (!Portal || !Portal->CanUse(Interactor)) return false;
    }
    TownAgeInteraction::FCandidateScore Score;
    const FVector Point = GetInteractionPoint();
    const FVector Approach = GetOwner()->GetActorTransform().TransformVectorNoScale(LocalApproachDirection);
    return Row && TownAgeInteraction::IsApproachAllowed(Point, Approach, Interactor->GetActorLocation())
        && TownAgeInteraction::EvaluateCandidate(Interactor->GetActorLocation(),
        Interactor->GetActorForwardVector(), Point, *Row, Score);
}

void UTownAgeInteractionTargetComponent::ExecuteInteraction_Implementation(APawn* Interactor)
{
    if (!GetOwner() || !GetOwner()->HasAuthority() || !CanInteract(Interactor))
        return;
    const FTownAgeInteractionRow* Row = GetDefinition();
    if (Row && Row->Action == ETownAgeInteractionAction::OpenCustomization)
    {
        if (auto* Player = Cast<ATownAgePlayer>(Interactor))
            if (auto* Customization = Player->GetCustomizationComponent()) Customization->ServerBegin(this);
        return;
    }
    if (Row && Row->Action == ETownAgeInteractionAction::DoorTransition)
    {
        if (auto* Portal = GetOwner()->FindComponentByClass<UTownAgeDoorPortalComponent>())
            Portal->TryStart(Interactor);
        return;
    }
    if (Row && Row->Action == ETownAgeInteractionAction::LogOnly)
    {
        UE_LOG(LogTownAgeInteraction, Log, TEXT("Interaction executed: Event=%s Row=%s Target=%s Interactor=%s Action=LogOnly"),
            *Row->LogEvent.ToString(), *Definition.RowName.ToString(), *GetOwner()->GetName(), *Interactor->GetName());
    }
}

UTownAgeInteractionComponent::UTownAgeInteractionComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickInterval = .05f;
    SetIsReplicatedByDefault(true);
}

void UTownAgeInteractionComponent::TickComponent(float DeltaTime, ELevelTick TickType,
    FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    const auto* Pawn = Cast<APawn>(GetOwner());
    if (Pawn && Pawn->IsLocallyControlled())
        RefreshSelection();
    else
        SelectedTarget.Reset();
}

UTownAgeInteractionTargetComponent* UTownAgeInteractionComponent::GetSelectedTarget() const
{
    auto* Target = SelectedTarget.Get();
    return Target && Target->CanInteract(Cast<APawn>(GetOwner())) ? Target : nullptr;
}

bool UTownAgeInteractionComponent::HasInteractable() const
{
    return GetSelectedTarget() != nullptr;
}

FText UTownAgeInteractionComponent::GetPrompt() const
{
    const auto* Target = GetSelectedTarget();
    const auto* Row = Target ? Target->GetDefinition() : nullptr;
    return Row ? Row->Prompt : FText::GetEmpty();
}

void UTownAgeInteractionComponent::RefreshSelection()
{
    const auto* Pawn = Cast<APawn>(GetOwner());
    auto* Registry = GetWorld() ? GetWorld()->GetSubsystem<UTownAgeInteractionSubsystem>() : nullptr;
    SelectedTarget = Registry ? Registry->SelectTarget(Pawn) : nullptr;
}

void UTownAgeInteractionComponent::TryInteract()
{
    const auto* Pawn = Cast<APawn>(GetOwner());
    if (!Pawn || !Pawn->IsLocallyControlled())
    {
        UE_LOG(LogTownAgeInteraction, Verbose, TEXT("Interaction request ignored locally: Owner=%s World=%s Local=%d"),
            *GetNameSafe(GetOwner()), *GetPathNameSafe(GetWorld()), Pawn && Pawn->IsLocallyControlled());
        return;
    }
    RefreshSelection();
    if (auto* Target = GetSelectedTarget())
    {
        UE_LOG(LogTownAgeInteraction, Verbose, TEXT("Interaction request dispatch: Owner=%s World=%s Role=%d NetMode=%d ComponentReplicated=%d Target=%s TargetOwnerReplicated=%d"),
            *Pawn->GetName(), *GetPathNameSafe(GetWorld()), int32(Pawn->GetLocalRole()), int32(Pawn->GetNetMode()),
            GetIsReplicated(), *GetPathNameSafe(Target), Target->GetOwner() && Target->GetOwner()->GetIsReplicated());
        ServerInteract(Target);
    }
    else
    {
        UE_LOG(LogTownAgeInteraction, Verbose, TEXT("Interaction request has no eligible target: Owner=%s World=%s"),
            *Pawn->GetName(), *GetPathNameSafe(GetWorld()));
    }
}

void UTownAgeInteractionComponent::ServerInteract_Implementation(UTownAgeInteractionTargetComponent* RequestedTarget)
{
    auto* Pawn = Cast<APawn>(GetOwner());
    UE_LOG(LogTownAgeInteraction, Verbose, TEXT("Interaction RPC received: Owner=%s World=%s Requested=%s Authority=%d Controller=%s"),
        *GetNameSafe(Pawn), *GetPathNameSafe(GetWorld()), *GetPathNameSafe(RequestedTarget), Pawn && Pawn->HasAuthority(),
        *GetNameSafe(Pawn ? Pawn->GetController() : nullptr));
    if (!Pawn || !Pawn->HasAuthority() || !Pawn->GetController() || !GetWorld())
        return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (Now - LastServerRequestTime < .2)
    {
        UE_LOG(LogTownAgeInteraction, Verbose, TEXT("Interaction RPC rate limited: Owner=%s Elapsed=%.4f"),
            *Pawn->GetName(), Now - LastServerRequestTime);
        return;
    }
    LastServerRequestTime = Now;
    auto* Registry = GetWorld()->GetSubsystem<UTownAgeInteractionSubsystem>();
    auto* CanonicalTarget = Registry ? Registry->SelectTarget(Pawn) : nullptr;
    if (CanonicalTarget && CanonicalTarget == RequestedTarget && CanonicalTarget->CanInteract(Pawn))
        CanonicalTarget->ExecuteInteraction(Pawn);
    else
        UE_LOG(LogTownAgeInteraction, Verbose, TEXT("Interaction RPC rejected: Owner=%s Requested=%s Canonical=%s RequestedEligible=%d"),
            *Pawn->GetName(), *GetPathNameSafe(RequestedTarget), *GetPathNameSafe(CanonicalTarget),
            IsValid(RequestedTarget) && RequestedTarget->CanInteract(Pawn));
}
