#include "TownAgePlayer.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "UObject/ConstructorHelpers.h"
#include "InputCoreTypes.h"
#include "TownAgeHUD.h"
#include "Net/UnrealNetwork.h"
#include "TownAgeTouch.h"
#include "TownAgeInteraction.h"
#include "TownAgeDoor.h"
#include "TownAgeDoorAnimInstance.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Animation/BlendSpace1D.h"
#include "Animation/AnimSingleNodeInstance.h"

namespace
{
    // Rounded stance-foot speeds measured on the Meshy provider cycles.
    constexpr float WalkSpeed = 87.f;
    constexpr float RunSpeed = 304.f;
}

ATownAgePlayer::ATownAgePlayer()
{
    PrimaryActorTick.bCanEverTick = true;
    bReplicates = true;
    Interaction = CreateDefaultSubobject<UTownAgeInteractionComponent>(TEXT("Interaction"));
    DoorTraversal = CreateDefaultSubobject<UTownAgeDoorTraversalComponent>(TEXT("DoorTraversal"));
    GetCapsuleComponent()->InitCapsuleSize(38.f, 88.f);
    bUseControllerRotationYaw = false;
    GetCharacterMovement()->bOrientRotationToMovement = true;
    GetCharacterMovement()->RotationRate = FRotator(0.f, 480.f, 0.f);
    GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
    GetCharacterMovement()->MaxAcceleration = 1000.f;
    GetCharacterMovement()->BrakingDecelerationWalking = 1400.f;
    static ConstructorHelpers::FObjectFinder<USkeletalMesh> Model(TEXT("/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/SK_TownKeeper_Meshy.SK_TownKeeper_Meshy"));
    if (Model.Succeeded()) GetMesh()->SetSkeletalMesh(Model.Object);
    GetMesh()->SetRelativeLocation(FVector(0.f, 0.f, -88.f));
    GetMesh()->SetRelativeRotation(FRotator(0.f, -90.f, 0.f));
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    static ConstructorHelpers::FObjectFinder<UBlendSpace1D> Locomotion(TEXT("/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/Animations/Locomotion01/BS_TownKeeper_Meshy_Locomotion.BS_TownKeeper_Meshy_Locomotion"));
    WalkBlendSpace = Locomotion.Object;
    CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
    CameraBoom->SetupAttachment(RootComponent);
    CameraBoom->SetUsingAbsoluteRotation(true);
    CameraBoom->SetRelativeRotation(FRotator(-32.f, -90.f, 0.f));
    // Wider village-life framing: the avatar occupies roughly a quarter of a 16:9 view.
    CameraBoom->TargetArmLength = 1500.f;
    CameraBoom->TargetOffset = FVector(0.f, 0.f, 45.f);
    CameraBoom->bUsePawnControlRotation = false;
    CameraBoom->bEnableCameraLag = true;
    CameraBoom->CameraLagSpeed = 7.f;
    FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
    FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
    FollowCamera->FieldOfView = 38.f;
    FollowCamera->bConstrainAspectRatio = false;
}

void ATownAgePlayer::BeginPlay()
{
    Super::BeginPlay();
    GetMesh()->SetAnimInstanceClass(UTownAgeDoorAnimInstance::StaticClass());
    if (WalkBlendSpace)
    {
        if (UAnimSingleNodeInstance* Animation = Cast<UAnimSingleNodeInstance>(GetMesh()->GetAnimInstance()))
        {
            Animation->SetAnimationAsset(WalkBlendSpace, true, 1.f);
            Animation->SetLooping(true);
            Animation->SetPlaying(true);
            Animation->SetPlayRate(1.f);
        }
    }
}

bool ATownAgePlayer::RebuildWalkBlendSpace(UBlendSpace1D* BlendSpace)
{
#if WITH_EDITOR
    if (!BlendSpace) return false;
    BlendSpace->ValidateSampleData();
    BlendSpace->ResampleData();
    BlendSpace->MarkPackageDirty();
    return true;
#else
    return false;
#endif
}

FVector2D ATownAgePlayer::GetWalkBlendWeights(UBlendSpace1D* BlendSpace, float Speed)
{
    const FVector Weights = GetLocomotionSampleWeights(BlendSpace, Speed);
    return FVector2D(Weights.X, Weights.Y);
}

FVector ATownAgePlayer::GetLocomotionSampleWeights(UBlendSpace1D* BlendSpace, float Speed)
{
    FVector Weights = FVector::ZeroVector;
    if (!BlendSpace) return Weights;
    TArray<FBlendSampleData> Samples;
    int32 CachedIndex = INDEX_NONE;
    BlendSpace->GetSamplesFromBlendInput(FVector(Speed, 0, 0), Samples, CachedIndex, true);
    for (const FBlendSampleData& Sample : Samples)
    {
        if (Sample.SampleDataIndex == 0) Weights.X += Sample.TotalWeight;
        if (Sample.SampleDataIndex == 1) Weights.Y += Sample.TotalWeight;
        if (Sample.SampleDataIndex == 2) Weights.Z += Sample.TotalWeight;
    }
    return Weights;
}

bool ATownAgePlayer::UsesTouchControls() const
{
#if PLATFORM_ANDROID || PLATFORM_IOS
    return true;
#else
    return FParse::Param(FCommandLine::Get(), TEXT("faketouches"));
#endif
}

bool ATownAgePlayer::IsSprintControlHeld() const
{
    const APlayerController* PC = Cast<APlayerController>(Controller);
    return bTouchSprintHeld || (PC && (PC->IsInputKeyDown(EKeys::LeftShift) || PC->IsInputKeyDown(EKeys::RightShift)));
}

void ATownAgePlayer::RequestInteraction()
{
    if (!IsDoorBusy() && Interaction) Interaction->TryInteract();
}

bool ATownAgePlayer::IsDoorBusy() const
{
    return DoorTraversal && DoorTraversal->IsBusy();
}

void ATownAgePlayer::UpdateTouchControls(APlayerController* PC)
{
    TouchMove = FVector2D::ZeroVector; bTouchSprintHeld = false;
    if (!UsesTouchControls()) return;
    int32 Width, Height; PC->GetViewportSize(Width, Height);
    if (Width <= 0 || Height <= 0) return;
    const FTownAgeTouchLayout Layout(FVector2D(Width, Height));
    for (int32 Finger = 0; Finger < 10; ++Finger)
    {
        float X, Y; bool bDown;
        PC->GetInputTouchState(ETouchIndex::Type(Finger), X, Y, bDown);
        const bool bNewPress = bDown && !TouchWasDown[Finger];
        TouchWasDown[Finger] = bDown;
        if (!bDown)
        {
            if (MoveFinger == Finger) MoveFinger = INDEX_NONE;
            if (SprintFinger == Finger) SprintFinger = INDEX_NONE;
            if (InteractionFinger == Finger) InteractionFinger = INDEX_NONE;
            continue;
        }
        const FVector2D Position(X, Y);
        // Consume a new press even when disabled. Holding a disabled button
        // must not fire later merely because a target enters range.
        if (bNewPress && InteractionFinger == INDEX_NONE && Finger != MoveFinger && Finger != SprintFinger && Layout.IsInteractButton(Position))
        {
            InteractionFinger = Finger;
            RequestInteraction();
        }
        if (Finger == InteractionFinger) continue;
        if (MoveFinger == INDEX_NONE && Finger != SprintFinger && FVector2D::Distance(Position, Layout.MoveCenter) < Layout.MoveRadius * 1.5f) MoveFinger = Finger;
        if (SprintFinger == INDEX_NONE && Finger != MoveFinger && FVector2D::Distance(Position, Layout.SprintCenter) < Layout.SprintRadius * 1.3f) SprintFinger = Finger;
        if (Finger == MoveFinger) TouchMove = Layout.Movement(Position);
        if (Finger == SprintFinger) bTouchSprintHeld = FVector2D::Distance(Position, Layout.SprintCenter) < Layout.SprintRadius * 1.6f;
    }
}

void ATownAgePlayer::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (HasAuthority())
    {
        if (IsDoorBusy()) bSprintRequested = false;
        bSprinting = !IsDoorBusy() && bSprintRequested && !StaminaState.bExhausted && StaminaState.Value > 0.f
            && GetVelocity().SizeSquared2D() > 100.f && GetCharacterMovement()->IsMovingOnGround();
        StaminaState.Update(DeltaSeconds, bSprinting);
        Stamina = StaminaState.Value;
        bExhausted = StaminaState.bExhausted;
        bSprinting = bSprinting && !bExhausted;
    }
    GetCharacterMovement()->MaxWalkSpeed = bSprinting ? RunSpeed : WalkSpeed;
    // All roles animate from actual movement, including replicated simulated proxies.
    const float PlanarSpeed = GetCharacterMovement()->IsMovingOnGround() ? GetVelocity().Size2D() : 0.f;
    // The Blend Space smooths sample weights once. Avoid filtering velocity a second time.
    // Separate enter/exit thresholds keep tiny replicated or analog velocity noise at idle.
    bAnimationMoving = PlanarSpeed > (bAnimationMoving ? 2.f : 4.f);
    if (!DoorTraversal || !DoorTraversal->GetActiveAnimation())
    if (UAnimSingleNodeInstance* Animation = Cast<UAnimSingleNodeInstance>(GetMesh()->GetAnimInstance()))
    {
        Animation->SetBlendSpacePosition(FVector(bAnimationMoving ? FMath::Clamp(PlanarSpeed, 0.f, RunSpeed) : 0.f, 0, 0));
    }
    APlayerController* PC = Cast<APlayerController>(Controller);
    if (!PC || !IsLocallyControlled()) return;
    UpdateTouchControls(PC);
    if (IsDoorBusy())
    {
        // Continue sampling touches so a held disabled interaction button
        // cannot become a new press as the traversal finishes.
        TouchMove = FVector2D::ZeroVector;
        bTouchSprintHeld = false;
        if (bLastSentSprintRequest)
        {
            bLastSentSprintRequest = false;
            ServerSetSprintRequested(false);
        }
        return;
    }
    if (PC->WasInputKeyJustPressed(EKeys::G)) RequestInteraction();
    // Fixed camera yaw -90: screen up is -Y and screen right is +X.
    const float Up = float(PC->IsInputKeyDown(EKeys::W)) - float(PC->IsInputKeyDown(EKeys::S));
    const float Right = float(PC->IsInputKeyDown(EKeys::D)) - float(PC->IsInputKeyDown(EKeys::A));
    const FVector Input = FVector(Right + TouchMove.X, -Up + TouchMove.Y, 0.f).GetClampedToMaxSize(1.f);
    const bool bRequested = !Input.IsNearlyZero() && IsSprintControlHeld();
    if (bRequested != bLastSentSprintRequest)
    {
        bLastSentSprintRequest = bRequested;
        ServerSetSprintRequested(bRequested);
    }
    // Predict the owning client's speed; authority owns stamina and exhaustion.
    if (!HasAuthority()) GetCharacterMovement()->MaxWalkSpeed = bRequested && !bExhausted && Stamina > 0.f ? RunSpeed : WalkSpeed;
    AddMovementInput(Input, Input.IsNearlyZero() ? 0.f : 1.f);
}

void ATownAgePlayer::ServerSetSprintRequested_Implementation(bool bRequested)
{
    bSprintRequested = bRequested;
}

void ATownAgePlayer::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(ATownAgePlayer, Stamina, COND_OwnerOnly);
    DOREPLIFETIME_CONDITION(ATownAgePlayer, bExhausted, COND_OwnerOnly);
    DOREPLIFETIME(ATownAgePlayer, bSprinting);
}

ATownAgeGameMode::ATownAgeGameMode()
{
    DefaultPawnClass = ATownAgePlayer::StaticClass();
    HUDClass = ATownAgeHUD::StaticClass();
}
