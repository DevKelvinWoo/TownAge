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
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Animation/BlendSpace1D.h"
#include "Animation/AnimSingleNodeInstance.h"

namespace
{
    // Approved 64cm/cycle gait at 30fps over 28 intervals.
    constexpr float WalkSpeed = 64.f * 30.f / 28.f;
}

ATownAgePlayer::ATownAgePlayer()
{
    PrimaryActorTick.bCanEverTick = true;
    bReplicates = true;
    GetCapsuleComponent()->InitCapsuleSize(38.f, 88.f);
    bUseControllerRotationYaw = false;
    GetCharacterMovement()->bOrientRotationToMovement = true;
    GetCharacterMovement()->RotationRate = FRotator(0.f, 480.f, 0.f);
    GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
    GetCharacterMovement()->MaxAcceleration = 1000.f;
    GetCharacterMovement()->BrakingDecelerationWalking = 1400.f;
    static ConstructorHelpers::FObjectFinder<USkeletalMesh> Model(TEXT("/Game/Characters/Main/TownKeeper/ReferenceRevision04/SK_TownKeeper_Reference.SK_TownKeeper_Reference"));
    if (Model.Succeeded()) GetMesh()->SetSkeletalMesh(Model.Object);
    GetMesh()->SetRelativeLocation(FVector(0.f, 0.f, -88.f));
    GetMesh()->SetRelativeRotation(FRotator(0.f, -90.f, 0.f));
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    static ConstructorHelpers::FObjectFinder<UBlendSpace1D> Locomotion(TEXT("/Game/Characters/Main/TownKeeper/Animations/BS_TownKeeper_Walk.BS_TownKeeper_Walk"));
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
    if (WalkBlendSpace)
    {
        GetMesh()->SetAnimationMode(EAnimationMode::AnimationSingleNode);
        GetMesh()->SetAnimation(WalkBlendSpace);
        if (UAnimSingleNodeInstance* Animation = GetMesh()->GetSingleNodeInstance())
        {
            Animation->SetLooping(true);
            Animation->SetPlaying(true);
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
    FVector2D Weights = FVector2D::ZeroVector;
    if (!BlendSpace) return Weights;
    TArray<FBlendSampleData> Samples;
    int32 CachedIndex = INDEX_NONE;
    BlendSpace->GetSamplesFromBlendInput(FVector(Speed, 0, 0), Samples, CachedIndex, true);
    for (const FBlendSampleData& Sample : Samples)
    {
        if (Sample.SampleDataIndex == 0) Weights.X += Sample.TotalWeight;
        if (Sample.SampleDataIndex == 1) Weights.Y += Sample.TotalWeight;
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
        if (!bDown)
        {
            if (MoveFinger == Finger) MoveFinger = INDEX_NONE;
            if (SprintFinger == Finger) SprintFinger = INDEX_NONE;
            continue;
        }
        const FVector2D Position(X, Y);
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
        bSprinting = bSprintRequested && !StaminaState.bExhausted && StaminaState.Value > 0.f
            && GetVelocity().SizeSquared2D() > 100.f && GetCharacterMovement()->IsMovingOnGround();
        StaminaState.Update(DeltaSeconds, bSprinting);
        Stamina = StaminaState.Value;
        bExhausted = StaminaState.bExhausted;
        bSprinting = bSprinting && !bExhausted;
    }
    GetCharacterMovement()->MaxWalkSpeed = bSprinting ? 440.f : WalkSpeed;
    // All roles animate from actual movement, including replicated simulated proxies.
    const float PlanarSpeed = GetCharacterMovement()->IsMovingOnGround() ? GetVelocity().Size2D() : 0.f;
    AnimationSpeed = FMath::FInterpTo(AnimationSpeed, PlanarSpeed < 3.f ? 0.f : PlanarSpeed, DeltaSeconds, 14.f);
    if (UAnimSingleNodeInstance* Animation = GetMesh()->GetSingleNodeInstance())
    {
        Animation->SetBlendSpacePosition(FVector(FMath::Clamp(AnimationSpeed, 0.f, WalkSpeed), 0, 0));
        // Temporary fast-walk fallback while the separately approved sprint clip is not authored.
        Animation->SetPlayRate(PlanarSpeed > WalkSpeed ? FMath::Clamp(PlanarSpeed / WalkSpeed, 1.f, 2.f) : 1.f);
    }
    APlayerController* PC = Cast<APlayerController>(Controller);
    if (!PC || !IsLocallyControlled()) return;
    UpdateTouchControls(PC);
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
    if (!HasAuthority()) GetCharacterMovement()->MaxWalkSpeed = bRequested && !bExhausted && Stamina > 0.f ? 440.f : WalkSpeed;
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
