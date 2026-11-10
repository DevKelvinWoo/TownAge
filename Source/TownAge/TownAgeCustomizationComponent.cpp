#include "TownAgeCustomizationComponent.h"

#include "TownAgeAppearance.h"
#include "TownAgeCustomizationPreview.h"
#include "TownAgeCustomizationWidget.h"
#include "TownAgeInteraction.h"
#include "TownAgePlayer.h"
#include "TownAgePlayerController.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Engine/Level.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"

DEFINE_LOG_CATEGORY(LogTownAgeCustomization);

namespace
{
constexpr TCHAR PreviewMap[] = TEXT("/Game/Maps/Customization/L_CharacterCustomizationPreview");
const FVector PreviewOrigin(100000., 0., 0.);
}

UTownAgeCustomizationComponent::UTownAgeCustomizationComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    SetIsReplicatedByDefault(true);
}

void UTownAgeCustomizationComponent::BeginPlay()
{
    Super::BeginPlay();
    OnRep_HairColorIndex();
}

void UTownAgeCustomizationComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    CleanupLocalPreview();
    Super::EndPlay(Reason);
}

bool UTownAgeCustomizationComponent::ServerBegin(UTownAgeInteractionTargetComponent* Target)
{
    auto* Player = Cast<ATownAgePlayer>(GetOwner());
    const auto* Row = IsValid(Target) ? Target->GetDefinition() : nullptr;
    if (!Player || !Player->HasAuthority() || !Player->GetController() || IsCustomizationOpen()
        || Player->IsDoorBusy() || !Row || Row->Action != ETownAgeInteractionAction::OpenCustomization
        || !Target->CanInteract(Player))
        return false;
    SessionTarget = Target;
    SessionController = Player->GetController();
    bServerSessionActive = true;
    ++ServerSessionId;
    auto* Movement = Player->GetCharacterMovement();
    PreviousMovementMode = Movement->MovementMode;
    PreviousCustomMovementMode = Movement->CustomMovementMode;
    Movement->StopMovementImmediately();
    Movement->DisableMovement();
    ClientBeginCustomization(ServerSessionId);
    Player->ForceNetUpdate();
    UE_LOG(LogTownAgeCustomization, Log, TEXT("Customization opened: Player=%s Session=%u Target=%s"),
        *Player->GetName(), ServerSessionId, *Target->GetPathName());
    return true;
}

bool UTownAgeCustomizationComponent::IsSessionTargetValid() const
{
    const auto* Player = Cast<ATownAgePlayer>(GetOwner());
    const auto* Target = SessionTarget.Get();
    if (!Player || !Player->GetController() || Player->GetController() != SessionController.Get()
        || Player->IsDoorBusy() || !IsValid(Target)
        || !IsValid(Target->GetOwner()) || Target->GetOwner()->IsActorBeingDestroyed()
        || !Target->bInteractionEnabled || Target->GetWorld() != GetWorld())
        return false;
    const auto* Row = Target->GetDefinition();
    if (!Row || Row->Action != ETownAgeInteractionAction::OpenCustomization) return false;
    TownAgeInteraction::FCandidateScore Score;
    const FVector Point = Target->GetInteractionPoint();
    const FVector Approach = Target->GetOwner()->GetActorTransform().TransformVectorNoScale(Target->LocalApproachDirection);
    return TownAgeInteraction::IsApproachAllowed(Point, Approach, Player->GetActorLocation())
        && TownAgeInteraction::EvaluateCandidate(Player->GetActorLocation(), Player->GetActorForwardVector(), Point, *Row, Score);
}

void UTownAgeCustomizationComponent::ChooseHairColor(uint8 ColorIndex)
{
    if (!bLocalOpen || !bPreviewPresented || !PreviewActor || ColorIndex < 1 || ColorIndex > TownAgeAppearance::NumHairColors) return;
    // Only an acknowledged server choice updates the displayed selection.
    ServerChooseHairColor(LocalSessionId, ColorIndex);
}

void UTownAgeCustomizationComponent::ServerChooseHairColor_Implementation(uint32 SessionId, uint8 ColorIndex)
{
    if (!bServerSessionActive || SessionId != ServerSessionId) return;
    if (!IsSessionTargetValid())
    {
        EndServerSession();
        return;
    }
    if (ColorIndex < 1 || ColorIndex > TownAgeAppearance::NumHairColors) return;
    HairColorIndex = ColorIndex;
    OnRep_HairColorIndex();
    GetOwner()->ForceNetUpdate();
    ClientConfirmHairColor(SessionId, ColorIndex);
    UE_LOG(LogTownAgeCustomization, Log, TEXT("Hair color applied: Player=%s Color=%u Session=%u"),
        *GetOwner()->GetName(), ColorIndex, SessionId);
}

void UTownAgeCustomizationComponent::OnRep_HairColorIndex()
{
    if (auto* Player = Cast<ATownAgePlayer>(GetOwner()))
        TownAgeAppearance::ApplyHairColor(Player->GetMesh(), HairColorIndex);
    if (PreviewActor) PreviewActor->ApplyHairColor(HairColorIndex);
    if (Widget) Widget->SetSelectedColor(HairColorIndex);
}

void UTownAgeCustomizationComponent::ClientConfirmHairColor_Implementation(uint32 SessionId, uint8 ColorIndex)
{
    if (!bLocalOpen || SessionId != LocalSessionId) return;
    // Property replication may arrive before or after this reliable acknowledgment.
    HairColorIndex = ColorIndex;
    OnRep_HairColorIndex();
}

void UTownAgeCustomizationComponent::ClientBeginCustomization_Implementation(uint32 SessionId)
{
    auto* Player = Cast<ATownAgePlayer>(GetOwner());
    auto* PC = Player ? Cast<ATownAgePlayerController>(Player->GetController()) : nullptr;
    if (!PC || !PC->IsLocalController()) return;
    CleanupLocalPreview();
    PC->CloseChat();
    LocalController = PC;
    LocalSessionId = SessionId;
    bLocalOpen = true;
    bPreviousCursor = PC->bShowMouseCursor;
    PC->bShowMouseCursor = true;
    PC->FlushPressedKeys();
    Player->GetCharacterMovement()->StopMovementImmediately();
    Widget = CreateWidget<UTownAgeCustomizationWidget>(PC);
    if (!Widget)
    {
        CloseCustomization();
        return;
    }
    Widget->OnColorSelected.AddUObject(this, &ThisClass::ChooseHairColor);
    Widget->OnCloseRequested.AddUObject(this, &ThisClass::CloseCustomization);
    Widget->AddToPlayerScreen(100);
    Widget->SetSelectedColor(HairColorIndex);
    Widget->SetReady(false);
    FInputModeGameAndUI Mode;
    Mode.SetWidgetToFocus(Widget->TakeWidget());
    Mode.SetHideCursorDuringCapture(false);
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    PC->SetInputMode(Mode);
    Widget->SetKeyboardFocus();
    bool bSuccess = false;
    PreviewLevel = ULevelStreamingDynamic::LoadLevelInstance(GetWorld(), PreviewMap, PreviewOrigin,
        FRotator::ZeroRotator, bSuccess);
    if (PreviewLevel) PreviewLevel->bClientOnlyVisible = true;
    PreviewLoadStarted = GetWorld()->GetTimeSeconds();
    if (!bSuccess || !PreviewLevel)
    {
        UE_LOG(LogTownAgeCustomization, Warning, TEXT("Customization preview level could not load"));
        CloseCustomization();
    }
}

void UTownAgeCustomizationComponent::UpdateLocalPreview()
{
    if (!bLocalOpen || bPreviewPresented) return;
    if (!PreviewLevel || GetWorld()->GetTimeSeconds() - PreviewLoadStarted > 15.)
    {
        UE_LOG(LogTownAgeCustomization, Warning, TEXT("Customization preview loading timed out"));
        CloseCustomization();
        return;
    }
    if (!PreviewActor)
    {
        if (!PreviewLevel->IsLevelVisible() || !PreviewLevel->GetLoadedLevel()) return;
        FActorSpawnParameters Parameters;
        Parameters.OverrideLevel = PreviewLevel->GetLoadedLevel();
        Parameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        PreviewActor = GetWorld()->SpawnActor<ATownAgeCustomizationPreview>(
            ATownAgeCustomizationPreview::StaticClass(), PreviewOrigin, FRotator::ZeroRotator, Parameters);
        if (PreviewActor) PreviewActor->ApplyHairColor(HairColorIndex);
    }
    if (!PreviewActor)
    {
        UE_LOG(LogTownAgeCustomization, Warning, TEXT("Customization preview actor could not spawn"));
        CloseCustomization();
        return;
    }
    if (!PreviewActor->IsPreviewReady()) return;
    PreviewActor->ApplyHairColor(HairColorIndex);
    Widget->SetPreviewTexture(PreviewActor->GetRenderTarget());
    Widget->SetReady(true);
    bPreviewPresented = true;
    UE_LOG(LogTownAgeCustomization, Log, TEXT("Customization preview ready: Player=%s Level=%s"),
        *GetOwner()->GetName(), *PreviewActor->GetLevel()->GetPathName());
}

void UTownAgeCustomizationComponent::CloseCustomization()
{
    if (!bLocalOpen) return;
    const uint32 ClosingSession = LocalSessionId;
    CleanupLocalPreview();
    ServerCloseCustomization(ClosingSession);
}

void UTownAgeCustomizationComponent::ServerCloseCustomization_Implementation(uint32 SessionId)
{
    if (bServerSessionActive && ServerSessionId == SessionId) EndServerSession();
}

void UTownAgeCustomizationComponent::EndServerSession()
{
    if (!bServerSessionActive) return;
    bServerSessionActive = false;
    SessionTarget.Reset();
    SessionController.Reset();
    if (auto* Player = Cast<ATownAgePlayer>(GetOwner()))
    {
        if (!Player->IsActorBeingDestroyed())
            Player->GetCharacterMovement()->SetMovementMode(PreviousMovementMode, PreviousCustomMovementMode);
        Player->ForceNetUpdate();
    }
    ClientEndCustomization(ServerSessionId);
    UE_LOG(LogTownAgeCustomization, Log, TEXT("Customization closed: Player=%s Session=%u"),
        *GetOwner()->GetName(), ServerSessionId);
}

void UTownAgeCustomizationComponent::ClientEndCustomization_Implementation(uint32 SessionId)
{
    if (bLocalOpen && SessionId == LocalSessionId) CleanupLocalPreview();
}

void UTownAgeCustomizationComponent::CleanupLocalPreview()
{
    const bool bWasOpen = bLocalOpen;
    bLocalOpen = false;
    bPreviewPresented = false;
    if (Widget)
    {
        Widget->OnColorSelected.RemoveAll(this);
        Widget->OnCloseRequested.RemoveAll(this);
        Widget->RemoveFromParent();
        Widget = nullptr;
    }
    if (PreviewActor)
    {
        PreviewActor->Destroy();
        PreviewActor = nullptr;
    }
    if (PreviewLevel)
    {
        PreviewLevel->SetShouldBeVisible(false);
        PreviewLevel->SetShouldBeLoaded(false);
        PreviewLevel->SetIsRequestingUnloadAndRemoval(true);
        PreviewLevel = nullptr;
    }
    auto* PC = LocalController.Get();
    if (bWasOpen && PC && PC->IsLocalController())
    {
        PC->bShowMouseCursor = bPreviousCursor;
        PC->SetInputMode(FInputModeGameOnly());
        PC->FlushPressedKeys();
    }
    LocalController.Reset();
}

void UTownAgeCustomizationComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(DeltaTime, TickType, TickFunction);
    if (GetOwner()->HasAuthority() && bServerSessionActive && !IsSessionTargetValid()) EndServerSession();
    if (bLocalOpen)
    {
        const auto* PC = LocalController.Get();
        if (!PC || !PC->IsLocalController() || PC->GetPawn() != GetOwner())
            CleanupLocalPreview(); // An unowned pawn cannot send its former owner's close RPC.
    }
    UpdateLocalPreview();
}

void UTownAgeCustomizationComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UTownAgeCustomizationComponent, HairColorIndex);
    DOREPLIFETIME_CONDITION(UTownAgeCustomizationComponent, bServerSessionActive, COND_OwnerOnly);
}
