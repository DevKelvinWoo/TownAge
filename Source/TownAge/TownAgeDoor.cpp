#include "TownAgeDoor.h"

#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/LevelStreaming.h"
#include "Engine/NetConnection.h"
#include "Engine/LatentActionManager.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/RootMotionSource.h"
#include "GameFramework/SpringArmComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"

DEFINE_LOG_CATEGORY(LogTownAgeDoor);

namespace
{
double WorldServerTime(const UWorld* World)
{
    if (!World) return 0.;
    const AGameStateBase* GameState = World->GetGameState();
    return GameState ? GameState->GetServerWorldTimeSeconds() : World->GetTimeSeconds();
}

ACharacter* CharacterOwner(const UActorComponent* Component)
{
    return Cast<ACharacter>(Component->GetOwner());
}

UAnimSingleNodeInstance* SingleNode(ACharacter* Character)
{
    return Character && Character->GetMesh()
        ? Cast<UAnimSingleNodeInstance>(Character->GetMesh()->GetAnimInstance()) : nullptr;
}
}

float TownAgeDoor::SmoothFraction(float Time, float Start, float End)
{
    if (!FMath::IsFinite(Time) || End <= Start) return 0.f;
    const float X = FMath::Clamp((Time - Start) / (End - Start), 0.f, 1.f);
    return X * X * (3.f - 2.f * X);
}

float TownAgeDoor::OpenFraction(float ActionTime, const FTownAgeDoorTiming& T)
{
    return .27f * SmoothFraction(ActionTime, T.DoorOpenStart, T.DoorPartOpenEnd)
        + .73f * SmoothFraction(ActionTime, T.DoorPartOpenEnd, T.DoorFullyOpen);
}

bool TownAgeDoor::IsTimingValid(const FTownAgeDoorTiming& T)
{
    for (float Value : {T.ActionDuration, T.StepStart, T.StepEnd, T.StepDistance,
        T.TraverseStart, T.TraverseEnd, T.DoorOpenStart, T.DoorPartOpenEnd,
        T.DoorFullyOpen, T.OpenYaw, T.CloseDuration, T.FadeDuration, T.LoadTimeout})
        if (!FMath::IsFinite(Value)) return false;
    return T.ActionDuration > 0.f && T.StepStart >= 0.f && T.StepEnd > T.StepStart
        && T.StepDistance >= 0.f && T.TraverseStart >= T.StepEnd
        && T.TraverseEnd > T.TraverseStart && T.ActionDuration >= T.TraverseEnd
        && T.DoorOpenStart >= 0.f && T.DoorPartOpenEnd > T.DoorOpenStart
        && T.DoorFullyOpen > T.DoorPartOpenEnd && T.DoorFullyOpen <= T.TraverseStart
        && T.OpenYaw > 0.f && T.OpenYaw <= 120.f && T.CloseDuration > 0.f
        && T.FadeDuration > 0.f && T.FadeDuration < T.ActionDuration
        && T.LoadTimeout >= T.ActionDuration;
}

void UTownAgeDoorSubsystem::RegisterPortal(UTownAgeDoorPortalComponent* Portal)
{
    Portals.RemoveAll([](const auto& Entry) { return !Entry.IsValid(); });
    Portals.AddUnique(Portal);
    if (Portal && Portal->GetOwner()->HasAuthority())
        if (const auto* Reservation = Reservations.Find(Portal->PortalId))
            if (auto* Traversal = Reservation->Get())
            {
                if (const auto* Source = Traversal->GetState().Portal.Get())
                    Portal->SetVisualState(Source->GetVisualState());
            }
}

void UTownAgeDoorSubsystem::UnregisterPortal(UTownAgeDoorPortalComponent* Portal)
{
    Portals.RemoveAll([Portal](const auto& Entry) { return !Entry.IsValid() || Entry.Get() == Portal; });
}

bool UTownAgeDoorSubsystem::IsReserved(FName Id) const
{
    const auto* Entry = Reservations.Find(Id);
    return Entry && Entry->IsValid();
}

bool UTownAgeDoorSubsystem::Reserve(UTownAgeDoorPortalComponent* Portal, UTownAgeDoorTraversalComponent* Traversal)
{
    if (!Portal || !Traversal || IsReserved(Portal->PortalId)) return false;
    Reservations.Add(Portal->PortalId, Traversal);
    FTownAgeDoorVisualState Visual;
    Visual.bReserved = true;
    Visual.Participant = Cast<APawn>(Traversal->GetOwner());
    Visual.SequenceId = Traversal->GetState().SequenceId;
    for (const auto& Entry : Portals)
        if (auto* Other = Entry.Get(); Other && Other->PortalId == Portal->PortalId)
            Other->SetVisualState(Visual);
    return true;
}

void UTownAgeDoorSubsystem::StartAction(FName Id, UTownAgeDoorTraversalComponent* Traversal, double Time, uint32 SequenceId)
{
    const auto* Reservation = Reservations.Find(Id);
    if (!Reservation || Reservation->Get() != Traversal) return;
    for (const auto& Entry : Portals)
        if (auto* Portal = Entry.Get(); Portal && Portal->PortalId == Id)
        {
            FTownAgeDoorVisualState Visual = Portal->GetVisualState();
            Visual.ActionStartTime = Time;
            Visual.CloseStartTime = -1.;
            Visual.SequenceId = SequenceId;
            Portal->SetVisualState(Visual);
        }
}

void UTownAgeDoorSubsystem::StartClose(FName Id, UTownAgeDoorTraversalComponent* Traversal, double Time)
{
    const auto* Reservation = Reservations.Find(Id);
    if (!Reservation || Reservation->Get() != Traversal) return;
    for (const auto& Entry : Portals)
        if (auto* Portal = Entry.Get(); Portal && Portal->PortalId == Id)
        {
            FTownAgeDoorVisualState Visual = Portal->GetVisualState();
            Visual.CloseStartTime = Time;
            Portal->SetVisualState(Visual);
        }
}

void UTownAgeDoorSubsystem::Release(FName Id, UTownAgeDoorTraversalComponent* Traversal, double Time)
{
    const auto* Reservation = Reservations.Find(Id);
    if (!Reservation || Reservation->Get() != Traversal) return;
    Reservations.Remove(Id);
    for (const auto& Entry : Portals)
        if (auto* Portal = Entry.Get(); Portal && Portal->PortalId == Id)
        {
            FTownAgeDoorVisualState Visual = Portal->GetVisualState();
            Visual.Participant = nullptr;
            Visual.bReserved = false;
            if (Visual.CloseStartTime < 0.) Visual.CloseStartTime = Time;
            Portal->SetVisualState(Visual);
        }
}

UTownAgeDoorPortalComponent::UTownAgeDoorPortalComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    SetIsReplicatedByDefault(true);
}

void UTownAgeDoorPortalComponent::BeginPlay()
{
    Super::BeginPlay();
    TArray<USceneComponent*> SceneComponents;
    GetOwner()->GetComponents(SceneComponents);
    for (USceneComponent* Component : SceneComponents)
        if (Component->GetFName() == DoorHingeName)
        {
            Hinge = Component;
            ClosedHingeRotation = Component->GetRelativeRotation().Quaternion();
            break;
        }
    LoadActionAnimation();
    if (auto* Registry = GetWorld()->GetSubsystem<UTownAgeDoorSubsystem>()) Registry->RegisterPortal(this);
    if (GetOwner()->HasAuthority()) PrepareInterior();
}

void UTownAgeDoorPortalComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if (GetOwner()->HasAuthority() && IsValid(VisualState.Participant))
        if (auto* Traversal = VisualState.Participant->FindComponentByClass<UTownAgeDoorTraversalComponent>())
            Traversal->CancelTraversal();
    if (GetWorld())
        if (auto* Registry = GetWorld()->GetSubsystem<UTownAgeDoorSubsystem>()) Registry->UnregisterPortal(this);
    Super::EndPlay(Reason);
}

void UTownAgeDoorPortalComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* Function)
{
    Super::TickComponent(DeltaTime, TickType, Function);
    if (!Hinge.IsValid()) return;
    const double Now = WorldServerTime(GetWorld());
    float Fraction = VisualState.ActionStartTime >= 0.
        ? TownAgeDoor::OpenFraction(float(Now - VisualState.ActionStartTime), Timing) : 0.f;
    if (VisualState.CloseStartTime >= 0.)
    {
        // Close from the actual fraction reached, including an interrupted opening.
        const float Initial = VisualState.ActionStartTime >= 0.
            ? TownAgeDoor::OpenFraction(float(VisualState.CloseStartTime - VisualState.ActionStartTime), Timing) : 0.f;
        Fraction = Initial * (1.f - TownAgeDoor::SmoothFraction(float(Now - VisualState.CloseStartTime), 0.f, Timing.CloseDuration));
    }
    Hinge->SetRelativeRotation(ClosedHingeRotation * FQuat(FVector::UpVector, FMath::DegreesToRadians(Timing.OpenYaw * Fraction)));
}

void UTownAgeDoorPortalComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UTownAgeDoorPortalComponent, VisualState);
}

bool UTownAgeDoorPortalComponent::CanUse(const APawn* Pawn) const
{
    if (!IsValid(Pawn) || Pawn->GetWorld() != GetWorld() || PortalId.IsNone()
        || !Hinge.IsValid() || ActionAnimation.IsNull() || InteriorLevel.IsNull()
        || !TownAgeDoor::IsTimingValid(Timing) || LocalAlignTransform.ContainsNaN()
        || LocalEndTransform.ContainsNaN() || DestinationTransform.ContainsNaN()) return false;
    const auto* Traversal = Pawn->FindComponentByClass<UTownAgeDoorTraversalComponent>();
    const ACharacter* Character = Cast<ACharacter>(Pawn);
    if (!Traversal || Traversal->IsBusy() || VisualState.bReserved || !Character
        || !Character->GetCharacterMovement()->IsMovingOnGround()) return false;
    if (VisualState.CloseStartTime >= 0. && WorldServerTime(GetWorld()) - VisualState.CloseStartTime < Timing.CloseDuration) return false;
    const auto* Registry = GetWorld()->GetSubsystem<UTownAgeDoorSubsystem>();
    return Registry && !Registry->IsReserved(PortalId);
}

bool UTownAgeDoorPortalComponent::TryStart(APawn* Pawn)
{
    if (!GetOwner()->HasAuthority() || !CanUse(Pawn)) return false;
    auto* Traversal = Pawn->FindComponentByClass<UTownAgeDoorTraversalComponent>();
    return Traversal && Traversal->ServerStart(this);
}

FTransform UTownAgeDoorPortalComponent::GetWorldAlignTransform() const
{
    return LocalAlignTransform * GetOwner()->GetActorTransform();
}

FTransform UTownAgeDoorPortalComponent::GetWorldEndTransform() const
{
    return LocalEndTransform * GetOwner()->GetActorTransform();
}

UPrimitiveComponent* UTownAgeDoorPortalComponent::GetDoorLeaf() const
{
    TArray<UPrimitiveComponent*> PrimitiveComponents;
    GetOwner()->GetComponents(PrimitiveComponents);
    for (UPrimitiveComponent* Component : PrimitiveComponents)
        if (Component->GetFName() == DoorLeafName) return Component;
    return nullptr;
}

ULevelStreaming* UTownAgeDoorPortalComponent::GetInteriorStreamingLevel() const
{
    const FString Package = InteriorLevel.ToSoftObjectPath().GetLongPackageName();
    return Package.IsEmpty() ? nullptr : UGameplayStatics::GetStreamingLevel(this, FName(*Package));
}

UAnimSequence* UTownAgeDoorPortalComponent::LoadActionAnimation()
{
    CachedActionAnimation = ActionAnimation.LoadSynchronous();
    return CachedActionAnimation;
}

void UTownAgeDoorPortalComponent::PrepareInterior()
{
    if (!GetOwner()->HasAuthority() || InteriorLevel.IsNull()) return;
    if (ULevelStreaming* Level = GetInteriorStreamingLevel(); Level && Level->IsLevelVisible()) return;
    FLatentActionInfo Info;
    Info.CallbackTarget = this;
    Info.UUID = 1;
    Info.Linkage = INDEX_NONE;
    // Tiny prototype room is intentionally cached for all connections. This
    // API broadcasts streaming status; it is not a per-client unload system.
    UGameplayStatics::LoadStreamLevel(this, FName(*InteriorLevel.ToSoftObjectPath().GetLongPackageName()), true, false, Info);
}

void UTownAgeDoorPortalComponent::SetVisualState(const FTownAgeDoorVisualState& NewState)
{
    VisualState = NewState;
    GetOwner()->FlushNetDormancy();
    GetOwner()->ForceNetUpdate();
}

UTownAgeDoorTraversalComponent::UTownAgeDoorTraversalComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    SetIsReplicatedByDefault(true);
}

void UTownAgeDoorTraversalComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    CancelTraversal(false);
    Super::EndPlay(Reason);
}

double UTownAgeDoorTraversalComponent::ServerTime() const { return WorldServerTime(GetWorld()); }

UAnimSequence* UTownAgeDoorTraversalComponent::GetActiveAnimation() const
{
    return (State.Phase == ETownAgeDoorPhase::Action || State.Phase == ETownAgeDoorPhase::WaitReady)
        && IsValid(State.Portal) ? State.Portal->GetLoadedAnimation() : nullptr;
}

float UTownAgeDoorTraversalComponent::GetAnimationTime() const
{
    return IsValid(State.Portal) ? FMath::Clamp(float(ServerTime() - State.ActionStartTime), 0.f, State.Portal->Timing.ActionDuration) : 0.f;
}

bool UTownAgeDoorTraversalComponent::ServerStart(UTownAgeDoorPortalComponent* Portal)
{
    ACharacter* Character = CharacterOwner(this);
    if (!Character || !Character->HasAuthority() || !Character->GetController() || !Portal || !Portal->CanUse(Character)) return false;
    UAnimSequence* Animation = Portal->LoadActionAnimation();
    if (!Animation || !Portal->GetInteriorStreamingLevel())
    {
        UE_LOG(LogTownAgeDoor, Warning, TEXT("Door start rejected: missing animation or predefined room level"));
        return false;
    }
    auto* Registry = GetWorld()->GetSubsystem<UTownAgeDoorSubsystem>();
    if (!Registry) return false;
    ++State.SequenceId;
    if (!Registry->Reserve(Portal, this)) return false;
    State.Portal = Portal;
    State.Origin = Character->GetActorTransform();
    const FTransform Align = Portal->GetWorldAlignTransform();
    const float MoveDuration = float(FVector::Dist2D(State.Origin.GetLocation(), Align.GetLocation()) / 87.);
    const float TurnDuration = FMath::Abs(FMath::FindDeltaAngleDegrees(State.Origin.Rotator().Yaw, Align.Rotator().Yaw)) / 360.f;
    State.AlignDuration = FMath::Clamp(FMath::Max(MoveDuration, TurnDuration), .2f, 1.8f);
    State.ActionStartTime = ServerTime() + State.AlignDuration;
    Portal->PrepareInterior();
    SetPhase(ETownAgeDoorPhase::Align);
    UE_LOG(LogTownAgeDoor, Log, TEXT("Door traversal started: Door=%s Side=%s Player=%s Sequence=%u"),
        *Portal->PortalId.ToString(), Portal->bInteriorSide ? TEXT("Exit") : TEXT("Enter"), *Character->GetName(), State.SequenceId);
    return true;
}

void UTownAgeDoorTraversalComponent::SetPhase(ETownAgeDoorPhase Phase)
{
    State.Phase = Phase;
    State.PhaseStartTime = ServerTime();
    GetOwner()->ForceNetUpdate();
    OnRep_State();
}

void UTownAgeDoorTraversalComponent::OnRep_State()
{
    UpdateMovement(0.f);
    UpdateCosmetics();
}

void UTownAgeDoorTraversalComponent::ApplyMove(FName Name, FVector Start, FVector Target, float Duration, float Elapsed)
{
    ACharacter* Character = CharacterOwner(this);
    if (!Character) return;
    auto* Movement = Character->GetCharacterMovement();
    StopMove();
    if (const auto Existing = Movement->GetRootMotionSource(Name))
    {
        MoveSourceId = Existing->LocalID;
        return;
    }
    TSharedPtr<FRootMotionSource_MoveToForce> Source = MakeShared<FRootMotionSource_MoveToForce>();
    Source->InstanceName = Name;
    Source->Priority = 1000;
    Source->AccumulateMode = ERootMotionAccumulateMode::Override;
    Source->StartLocation = Start;
    Source->TargetLocation = Target;
    Source->Duration = FMath::Max(Duration, .01f);
    Source->SetTime(FMath::Clamp(Elapsed, 0.f, Source->Duration));
    Source->bRestrictSpeedToExpected = false;
    Source->FinishVelocityParams.Mode = ERootMotionFinishVelocityMode::SetVelocity;
    Source->FinishVelocityParams.SetVelocity = FVector::ZeroVector;
    MoveSourceId = Movement->ApplyRootMotionSource(Source);
}

void UTownAgeDoorTraversalComponent::StopMove()
{
    if (auto* Character = CharacterOwner(this); Character && MoveSourceId)
        Character->GetCharacterMovement()->RemoveRootMotionSourceByID(MoveSourceId);
    MoveSourceId = 0;
}

void UTownAgeDoorTraversalComponent::UpdateMovement(float DeltaTime)
{
    ACharacter* Character = CharacterOwner(this);
    if (!Character) return;
    if (!IsBusy())
    {
        StopMove();
        if (MovementSequenceId)
        {
            Character->GetCharacterMovement()->bOrientRotationToMovement = bSavedOrientToMovement;
            if (auto* SpringArm = Character->FindComponentByClass<USpringArmComponent>()) SpringArm->bDoCollisionTest = bSavedCameraCollision;
        }
        MovementSequenceId = 0;
        MovementPhase = ETownAgeDoorPhase::Idle;
        UpdateLeafIgnore(false);
        return;
    }
    if (!IsValid(State.Portal)) return;
    if (MovementSequenceId != State.SequenceId)
    {
        bSavedOrientToMovement = Character->GetCharacterMovement()->bOrientRotationToMovement;
        MovementSequenceId = State.SequenceId;
        MovementPhase = ETownAgeDoorPhase::Idle;
        bStepStarted = bTraverseStarted = false;
        Character->ConsumeMovementInputVector();
        Character->GetCharacterMovement()->StopMovementImmediately();
        if (auto* SpringArm = Character->FindComponentByClass<USpringArmComponent>())
        {
            bSavedCameraCollision = SpringArm->bDoCollisionTest;
            SpringArm->bDoCollisionTest = false;
        }
    }
    Character->GetCharacterMovement()->bOrientRotationToMovement = false;
    UpdateLeafIgnore(true);
    if (!Character->HasAuthority() && !Character->IsLocallyControlled()) return;
    const FTransform Align = State.Portal->GetWorldAlignTransform();
    const float PhaseTime = FMath::Max(0.f, float(ServerTime() - State.PhaseStartTime));
    if (State.Phase == ETownAgeDoorPhase::Align && MovementPhase != State.Phase)
        ApplyMove(FName(*FString::Printf(TEXT("DoorAlign_%u"), State.SequenceId)), State.Origin.GetLocation(), Align.GetLocation(), State.AlignDuration, PhaseTime);
    const FRotator Rotation = FMath::RInterpConstantTo(Character->GetActorRotation(), Align.Rotator(), DeltaTime, 360.f);
    if (DeltaTime > 0.f && (State.Phase == ETownAgeDoorPhase::Align || State.Phase == ETownAgeDoorPhase::Action))
        Character->SetActorRotation(Rotation);
    if (State.Phase == ETownAgeDoorPhase::Action)
    {
        const auto& T = State.Portal->Timing;
        const float Time = GetAnimationTime();
        const FVector StepTarget = Align.GetLocation() + Align.GetRotation().GetForwardVector() * T.StepDistance * (State.Portal->bInteriorSide ? -1.f : 1.f);
        if (!bStepStarted && Time >= T.StepStart)
        {
            bStepStarted = true;
            if (Time < T.StepEnd)
                ApplyMove(FName(*FString::Printf(TEXT("DoorStep_%u"), State.SequenceId)), Align.GetLocation(), StepTarget, T.StepEnd - T.StepStart, Time - T.StepStart);
        }
        if (!bTraverseStarted && Time >= T.TraverseStart)
        {
            bTraverseStarted = true;
            if (Time < T.TraverseEnd)
                ApplyMove(FName(*FString::Printf(TEXT("DoorCross_%u"), State.SequenceId)), StepTarget, State.Portal->GetWorldEndTransform().GetLocation(), T.TraverseEnd - T.TraverseStart, Time - T.TraverseStart);
        }
    }
    if (State.Phase == ETownAgeDoorPhase::WaitReady || State.Phase == ETownAgeDoorPhase::Closing)
    {
        StopMove();
        Character->GetCharacterMovement()->StopMovementImmediately();
    }
    MovementPhase = State.Phase;
}

void UTownAgeDoorTraversalComponent::UpdateLeafIgnore(bool bIgnore)
{
    ACharacter* Character = CharacterOwner(this);
    if (!Character) return;
    UPrimitiveComponent* Leaf = bIgnore && State.Portal ? State.Portal->GetDoorLeaf() : nullptr;
    if (IgnoredLeaf.Get() != Leaf)
    {
        if (IgnoredLeaf.IsValid())
        {
            Character->GetCapsuleComponent()->IgnoreComponentWhenMoving(IgnoredLeaf.Get(), false);
            IgnoredLeaf->IgnoreActorWhenMoving(Character, false);
        }
        IgnoredLeaf = Leaf;
        if (Leaf)
        {
            Character->GetCapsuleComponent()->IgnoreComponentWhenMoving(Leaf, true);
            Leaf->IgnoreActorWhenMoving(Character, true);
        }
    }
}

void UTownAgeDoorTraversalComponent::RestoreAnimation()
{
    if (auto* Animation = SingleNode(CharacterOwner(this)); Animation && SavedAnimation)
    {
        Animation->SetAnimationAsset(SavedAnimation, bSavedLooping, SavedPlayRate);
        Animation->SetBlendSpacePosition(FVector::ZeroVector);
        Animation->SetPlaying(true);
        SavedAnimation = nullptr;
    }
}

void UTownAgeDoorTraversalComponent::UpdateCosmetics()
{
    ACharacter* Character = CharacterOwner(this);
    if (!Character) return;
    UAnimSingleNodeInstance* Animation = SingleNode(Character);
    UAnimSequence* Clip = GetActiveAnimation();
    if (Animation && Clip)
    {
        if (Animation->GetCurrentAsset() != Clip)
        {
            if (!SavedAnimation)
            {
                SavedAnimation = Animation->GetCurrentAsset();
                bSavedLooping = Animation->IsLooping();
                SavedPlayRate = Animation->GetPlayRate();
            }
            Animation->SetAnimationAsset(Clip, false, 1.f);
        }
        Animation->SetPlaying(false);
        Animation->SetPosition(FMath::Min(GetAnimationTime(), Clip->GetPlayLength()), false);
    }
    else RestoreAnimation();
    if (auto* PC = Cast<APlayerController>(Character->GetController()); PC && PC->IsLocalController() && PC->PlayerCameraManager)
    {
        float Fade = 0.f;
        if (State.Portal)
        {
            const auto& T = State.Portal->Timing;
            if (State.Phase == ETownAgeDoorPhase::Action)
                Fade = TownAgeDoor::SmoothFraction(GetAnimationTime(), T.ActionDuration - T.FadeDuration, T.ActionDuration);
            else if (State.Phase == ETownAgeDoorPhase::WaitReady) Fade = 1.f;
            else if (State.Phase == ETownAgeDoorPhase::Closing)
                Fade = 1.f - TownAgeDoor::SmoothFraction(float(ServerTime() - State.PhaseStartTime), 0.f, T.FadeDuration);
        }
        if (IsBusy())
        {
            PC->PlayerCameraManager->SetManualCameraFade(Fade, FLinearColor::Black, false);
            bApplyingFade = true;
        }
        else if (bApplyingFade)
        {
            PC->PlayerCameraManager->StopCameraFade();
            bApplyingFade = false;
        }
    }
}

bool UTownAgeDoorTraversalComponent::IsRoomReady() const
{
    const ACharacter* Character = CharacterOwner(this);
    if (!Character || !State.Portal) return false;
    const ULevelStreaming* Streaming = State.Portal->GetInteriorStreamingLevel();
    if (!Streaming || !Streaming->IsLevelVisible() || !Streaming->GetLoadedLevel()) return false;
    const auto* PC = Cast<APlayerController>(Character->GetController());
    if (!PC) return false;
    const UNetConnection* Connection = PC->GetNetConnection();
    return !Connection || Connection->ClientHasInitializedLevel(Streaming->GetLoadedLevel());
}

void UTownAgeDoorTraversalComponent::ClientTransfer_Implementation(FTransform Destination, uint32 SequenceId)
{
    ACharacter* Character = CharacterOwner(this);
    if (!Character || (State.SequenceId && State.SequenceId != SequenceId)) return;
    StopMove();
    Character->TeleportTo(Destination.GetLocation(), Destination.Rotator(), false, true);
    Character->GetCharacterMovement()->StopMovementImmediately();
    if (auto* SpringArm = Character->FindComponentByClass<USpringArmComponent>())
    {
        bSavedCameraLag = SpringArm->bEnableCameraLag;
        SpringArm->bEnableCameraLag = false;
        CameraLagResetFrames = 2;
    }
}

void UTownAgeDoorTraversalComponent::CancelTraversal(bool bRestoreOrigin)
{
    ACharacter* Character = CharacterOwner(this);
    if (!Character) return;
    if (Character->HasAuthority() && IsBusy())
    {
        if (State.Portal)
            if (auto* Registry = GetWorld()->GetSubsystem<UTownAgeDoorSubsystem>())
            {
                Registry->StartClose(State.Portal->PortalId, this, ServerTime());
                Registry->Release(State.Portal->PortalId, this, ServerTime());
            }
        if (bRestoreOrigin && !Character->IsActorBeingDestroyed())
        {
            Character->TeleportTo(State.Origin.GetLocation(), State.Origin.Rotator(), false, false);
            if (Character->GetController()) ClientTransfer(Character->GetActorTransform(), State.SequenceId);
        }
        UE_LOG(LogTownAgeDoor, Warning, TEXT("Door traversal cancelled: Player=%s Sequence=%u"), *Character->GetName(), State.SequenceId);
        Finish();
    }
    StopMove();
    UpdateLeafIgnore(false);
    RestoreAnimation();
}

void UTownAgeDoorTraversalComponent::Finish()
{
    if (State.Portal)
        if (auto* Registry = GetWorld()->GetSubsystem<UTownAgeDoorSubsystem>())
            Registry->Release(State.Portal->PortalId, this, ServerTime());
    State.Portal = nullptr;
    SetPhase(ETownAgeDoorPhase::Idle);
    UE_LOG(LogTownAgeDoor, Log, TEXT("Door traversal finished: Player=%s Sequence=%u"), *GetOwner()->GetName(), State.SequenceId);
}

void UTownAgeDoorTraversalComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* Function)
{
    Super::TickComponent(DeltaTime, TickType, Function);
    ACharacter* Character = CharacterOwner(this);
    if (!Character) return;
    if (CameraLagResetFrames > 0 && --CameraLagResetFrames == 0)
        if (auto* SpringArm = Character->FindComponentByClass<USpringArmComponent>()) SpringArm->bEnableCameraLag = bSavedCameraLag;
    UpdateMovement(DeltaTime);
    UpdateCosmetics();
    if (!Character->HasAuthority() || !IsBusy()) return;
    if (!IsValid(State.Portal) || !Character->GetController())
    {
        CancelTraversal();
        return;
    }
    const auto& T = State.Portal->Timing;
    const double Now = ServerTime();
    if (State.Phase == ETownAgeDoorPhase::Align && Now - State.PhaseStartTime >= State.AlignDuration)
    {
        if (FVector::Dist2D(Character->GetActorLocation(), State.Portal->GetWorldAlignTransform().GetLocation()) > 5.f)
        {
            CancelTraversal();
            return;
        }
        StopMove();
        Character->GetCharacterMovement()->StopMovementImmediately();
        State.ActionStartTime = Now;
        if (auto* Registry = GetWorld()->GetSubsystem<UTownAgeDoorSubsystem>())
            Registry->StartAction(State.Portal->PortalId, this, Now, State.SequenceId);
        SetPhase(ETownAgeDoorPhase::Action);
    }
    else if (State.Phase == ETownAgeDoorPhase::Action && Now - State.ActionStartTime >= T.ActionDuration)
    {
        if (FVector::Dist2D(Character->GetActorLocation(), State.Portal->GetWorldEndTransform().GetLocation()) > 10.f)
        {
            CancelTraversal();
            return;
        }
        SetPhase(ETownAgeDoorPhase::WaitReady);
    }
    else if (State.Phase == ETownAgeDoorPhase::WaitReady)
    {
        if (Now - (State.ActionStartTime - State.AlignDuration) > T.LoadTimeout)
        {
            CancelTraversal();
            return;
        }
        if (!IsRoomReady()) return;
        FVector Destination = State.Portal->DestinationTransform.GetLocation();
        const FRotator Rotation = State.Portal->DestinationTransform.Rotator();
        if (!GetWorld()->FindTeleportSpot(Character, Destination, Rotation))
        {
            CancelTraversal();
            return;
        }
        StopMove();
        if (!Character->TeleportTo(Destination, Rotation, false, true))
        {
            CancelTraversal();
            return;
        }
        Character->GetCharacterMovement()->StopMovementImmediately();
        const FTransform FinalDestination(Rotation, Destination);
        ClientTransfer(FinalDestination, State.SequenceId);
        if (auto* Registry = GetWorld()->GetSubsystem<UTownAgeDoorSubsystem>())
            Registry->StartClose(State.Portal->PortalId, this, Now);
        UE_LOG(LogTownAgeDoor, Log, TEXT("Door transfer committed: Player=%s Side=%s Destination=%s Sequence=%u"),
            *Character->GetName(), State.Portal->bInteriorSide ? TEXT("Village") : TEXT("Interior"), *Destination.ToCompactString(), State.SequenceId);
        SetPhase(ETownAgeDoorPhase::Closing);
    }
    else if (State.Phase == ETownAgeDoorPhase::Closing && Now - State.PhaseStartTime >= T.CloseDuration) Finish();
}

void UTownAgeDoorTraversalComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UTownAgeDoorTraversalComponent, State);
}
