#include "TownAgePlayerController.h"
#include "TownAgeChatWidget.h"
#include "TownAgeChat.h"
#include "TownAgeGameState.h"
#include "TownAgeLightingPreviewWidget.h"
#include "TownAgePlayer.h"
#include "GameFramework/PlayerState.h"
#include "Engine/World.h"
#include "Components/InputComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Engine/Engine.h"
#include "CoreGlobals.h"
#include "InputCoreTypes.h"

namespace
{
#if !UE_BUILD_SHIPPING
    // PIE and standalone are local development environments. Other network
    // servers must deliberately opt in; clients cannot grant this permission.
    TAutoConsoleVariable<int32> CVarAllowDebugTeleport(
        TEXT("TownAge.Debug.AllowTeleport"), 0,
        TEXT("Allow Ctrl+Alt+click debug teleport on a non-shipping network server. PIE/standalone allow it automatically."),
        ECVF_Default);
    bool IsDebugPointInBounds(const FVector& Point)
    {
        return !Point.ContainsNaN() && Point.GetAbsMax() <= 10000000.;
    }
#endif
}

void ATownAgePlayerController::BeginPlay()
{
    Super::BeginPlay();
    if (IsLocalController() && GetNetMode() != NM_DedicatedServer)
    {
        ChatWidget = CreateWidget<UTownAgeChatWidget>(this);
        if (ChatWidget) ChatWidget->AddToPlayerScreen(20);
    }
}

void ATownAgePlayerController::EndPlay(const EEndPlayReason::Type Reason)
{
    if (ChatWidget) ChatWidget->RemoveFromParent();
    if (LightingPreviewWidget) LightingPreviewWidget->RemoveFromParent();
    Super::EndPlay(Reason);
}

void ATownAgePlayerController::SetupInputComponent()
{
    Super::SetupInputComponent();
    InputComponent->BindKey(EKeys::Enter, IE_Pressed, this, &ATownAgePlayerController::OpenChat);
    InputComponent->BindAxisKey(EKeys::MouseWheelAxis, this, &ATownAgePlayerController::HandleCameraWheel);
#if !UE_BUILD_SHIPPING
    InputComponent->BindKey(EKeys::F7, IE_Pressed, this, &ATownAgePlayerController::ToggleLightingPreview);
    InputComponent->BindKey(FInputChord(EKeys::LeftMouseButton, false, true, true, false),
        IE_Pressed, this, &ATownAgePlayerController::HandleDebugTeleportClick);
#endif
}

void ATownAgePlayerController::PlayerTick(float DeltaTime)
{
    Super::PlayerTick(DeltaTime);
#if !UE_BUILD_SHIPPING
    if (!IsLocalController()) return;
    const auto* TownPlayer = Cast<ATownAgePlayer>(GetPawn());
    const bool bUIOwnsInput = bChatOpen || LightingPreviewWidget || (TownPlayer && TownPlayer->IsCustomizing());
    const bool bModifiers = (IsInputKeyDown(EKeys::LeftControl) || IsInputKeyDown(EKeys::RightControl))
        && (IsInputKeyDown(EKeys::LeftAlt) || IsInputKeyDown(EKeys::RightAlt));
    if (bModifiers && TownPlayer && !TownPlayer->IsDoorBusy() && !bUIOwnsInput)
    {
        if (!bDebugTeleportCursor)
        {
            bDebugPreviousCursor = bShowMouseCursor;
            bDebugTeleportCursor = true;
            bShowMouseCursor = true;
            FInputModeGameAndUI Mode;
            Mode.SetHideCursorDuringCapture(false);
            Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
            SetInputMode(Mode);
        }
    }
    else ReleaseDebugTeleportCursor(!bUIOwnsInput);
#endif
}

void ATownAgePlayerController::ReleaseDebugTeleportCursor(bool bRestoreInput)
{
    // Replicated customization state can precede its client UI-open RPC. Keep
    // the saved cursor state until the UI explicitly takes ownership below.
    if (!bDebugTeleportCursor || !bRestoreInput) return;
    bDebugTeleportCursor = false;
    bShowMouseCursor = bDebugPreviousCursor;
    SetInputMode(FInputModeGameOnly());
}

void ATownAgePlayerController::HandleDebugTeleportClick()
{
#if !UE_BUILD_SHIPPING
    if (!IsLocalController() || bChatOpen || LightingPreviewWidget) return;
    const auto* TownPlayer = Cast<ATownAgePlayer>(GetPawn());
    if (!TownPlayer || TownPlayer->IsCustomizing() || TownPlayer->IsDoorBusy()) return;
    FHitResult Hit;
    if (GetHitResultUnderCursorByChannel(UEngineTypes::ConvertToTraceType(ECC_Visibility), false, Hit) && Hit.bBlockingHit)
        RequestDebugTeleportAt(Hit.ImpactPoint);
#endif
}

bool ATownAgePlayerController::RequestDebugTeleportAt(const FVector& SurfacePoint)
{
#if !UE_BUILD_SHIPPING
    if (!IsLocalController() || bChatOpen || LightingPreviewWidget || !IsDebugPointInBounds(SurfacePoint)) return false;
    const auto* TownPlayer = Cast<ATownAgePlayer>(GetPawn());
    if (!TownPlayer || TownPlayer->IsCustomizing() || TownPlayer->IsDoorBusy()) return false;
    if (HasAuthority())
    {
        FString Notice;
        const bool bAccepted = TryDebugTeleport(SurfacePoint, Notice);
        ClientDebugTeleportResult(bAccepted, Notice);
        return bAccepted;
    }
    bLastDebugTeleportSucceeded = false;
    LastDebugTeleportNotice = TEXT("Waiting for server.");
#if WITH_EDITOR
    if (GetWorld() && GetWorld()->WorldType == EWorldType::PIE)
    {
        // Python's FEditorScriptExecutionGuard forces actor RPCs to execute
        // locally, even when the object belongs to a PIE client. Restore real
        // callspace only around this owned RPC; server permission checks stay
        // unchanged. Physical input already has this flag false.
        TGuardValue<bool> ScriptCallspaceGuard(GAllowActorScriptExecutionInEditor, false);
        ServerDebugTeleport(SurfacePoint);
        return true;
    }
#endif
    ServerDebugTeleport(SurfacePoint);
    return true;
#else
    return false;
#endif
}

void ATownAgePlayerController::ServerDebugTeleport_Implementation(const FVector& SurfacePoint)
{
    FString Notice;
    const bool bAccepted = TryDebugTeleport(SurfacePoint, Notice);
    ClientDebugTeleportResult(bAccepted, Notice);
}

bool ATownAgePlayerController::TryDebugTeleport(const FVector& SurfacePoint, FString& Notice)
{
    Notice = TEXT("Debug teleport is disabled.");
#if !UE_BUILD_SHIPPING
    UWorld* World = GetWorld();
    if (!World)
    { Notice = TEXT("Debug teleport unavailable: no world."); return false; }
    if (!HasAuthority())
    {
        Notice = FString::Printf(TEXT("Debug teleport requires authority (role=%d, net=%d, world=%d)."),
            int32(GetLocalRole()), int32(GetNetMode()), int32(World->WorldType));
        UE_LOG(LogTemp, Warning, TEXT("TownAge debug teleport: %s: %s"), *GetPathName(), *Notice);
        return false;
    }
    if (World->WorldType != EWorldType::PIE && GetNetMode() != NM_Standalone
        && CVarAllowDebugTeleport.GetValueOnGameThread() == 0)
    {
        Notice = FString::Printf(TEXT("Debug teleport disabled by server policy (net=%d, world=%d). Enable TownAge.Debug.AllowTeleport on the development server."),
            int32(GetNetMode()), int32(World->WorldType));
        UE_LOG(LogTemp, Warning, TEXT("TownAge debug teleport: %s: %s"), *GetPathName(), *Notice);
        return false;
    }
    auto* TownPlayer = Cast<ATownAgePlayer>(GetPawn());
    if (!TownPlayer || TownPlayer->GetController() != this || TownPlayer->IsCustomizing() || TownPlayer->IsDoorBusy())
    { Notice = TEXT("Player is busy or unavailable."); return false; }
    if (!IsDebugPointInBounds(SurfacePoint)
        || FVector::DistSquared(TownPlayer->GetActorLocation(), SurfacePoint) > FMath::Square(200000.))
    { Notice = TEXT("Target is outside the debug teleport bounds."); return false; }
    const double Now = World->GetTimeSeconds();
    if (Now - LastDebugTeleportTime < .15)
    { Notice = TEXT("Wait briefly before another teleport."); return false; }
    LastDebugTeleportTime = Now;
    auto* Movement = TownPlayer->GetCharacterMovement();
    auto* Capsule = TownPlayer->GetCapsuleComponent();
    if (!Movement || !Capsule || Movement->MovementMode == MOVE_None)
    { Notice = TEXT("Player movement is unavailable."); return false; }
    FCollisionQueryParams Params(SCENE_QUERY_STAT(TownAgeDebugTeleport), false, TownPlayer);
    FHitResult Ground;
    // The client selects a visible surface; authority independently resolves the
    // nearby walkable floor rather than trusting a client-supplied capsule origin.
    if (!World->LineTraceSingleByChannel(Ground, SurfacePoint + FVector(0, 0, 125),
        SurfacePoint - FVector(0, 0, 250), ECC_Visibility, Params)
        || !Movement->IsWalkable(Ground) || FMath::Abs(Ground.ImpactPoint.Z - SurfacePoint.Z) > 100.)
    { Notice = TEXT("Choose a walkable ground surface."); return false; }
    const FVector Destination = Ground.ImpactPoint + FVector(0, 0, Capsule->GetScaledCapsuleHalfHeight() + 3.);
    const FCollisionShape Shape = FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight());
    if (World->OverlapBlockingTestByProfile(Destination, FQuat::Identity,
        Capsule->GetCollisionProfileName(), Shape, Params))
    { Notice = TEXT("Not enough space for the player at that point."); return false; }
    if (!TownPlayer->TeleportTo(Destination, TownPlayer->GetActorRotation(), false, false))
    { Notice = TEXT("Teleport could not find a safe destination."); return false; }
    Movement->StopMovementImmediately();
    Movement->ClearAccumulatedForces();
    Movement->SetMovementMode(MOVE_Walking);
    Movement->ForceClientAdjustment();
    Movement->ForceReplicationUpdate();
    TownPlayer->ForceNetUpdate();
    // Character RepMovement does not drive its autonomous owning client, and
    // an idle owner may have no movement packet awaiting correction. Use the
    // engine's reliable server-to-owner teleport with the committed location.
    if (!IsLocalController()) ClientSetLocation(TownPlayer->GetActorLocation(), GetControlRotation());
    Notice = TEXT("Debug teleport complete.");
    return true;
#else
    return false;
#endif
}

void ATownAgePlayerController::ClientDebugTeleportResult_Implementation(bool bAccepted, const FString& Notice)
{
#if !UE_BUILD_SHIPPING
    bLastDebugTeleportSucceeded = bAccepted;
    LastDebugTeleportNotice = Notice;
    if (bAccepted && IsLocalController())
        if (auto* TownPlayer = Cast<ATownAgePlayer>(GetPawn()))
        {
            // Ordered after ClientSetLocation on the same controller channel.
            auto* Movement = TownPlayer->GetCharacterMovement();
            Movement->StopMovementImmediately();
            Movement->ClearAccumulatedForces();
        }
    if (GEngine && IsLocalController()) GEngine->AddOnScreenDebugMessage(-1, 2.f,
        bAccepted ? FColor::Green : FColor::Yellow, Notice);
#endif
}

void ATownAgePlayerController::HandleCameraWheel(float Delta)
{
    if (!FMath::IsNearlyZero(Delta))
        if (auto* TownPlayer = Cast<ATownAgePlayer>(GetPawn())) TownPlayer->ZoomCameraByWheel(Delta);
}

void ATownAgePlayerController::ToggleLightingPreview()
{
#if !UE_BUILD_SHIPPING
    if (LightingPreviewWidget)
    {
        CloseLightingPreview();
        return;
    }
    if (!HasAuthority() || !IsLocalController() || GetNetMode() == NM_DedicatedServer || bChatOpen) return;
    const auto* TownPlayer = Cast<ATownAgePlayer>(GetPawn());
    if (!TownPlayer || TownPlayer->IsCustomizing() || TownPlayer->IsDoorBusy()) return;
    ReleaseDebugTeleportCursor();
    LightingPreviewWidget = CreateWidget<UTownAgeLightingPreviewWidget>(this);
    if (!LightingPreviewWidget) return;
    bLightingPreviousCursor = bShowMouseCursor;
    bShowMouseCursor = true;
    LightingPreviewWidget->AddToPlayerScreen(60);
    FInputModeGameAndUI Mode;
    Mode.SetWidgetToFocus(LightingPreviewWidget->TakeWidget());
    Mode.SetHideCursorDuringCapture(false);
    SetInputMode(Mode);
#endif
}

void ATownAgePlayerController::CloseLightingPreview()
{
    if (!LightingPreviewWidget) return;
    LightingPreviewWidget->RemoveFromParent();
    LightingPreviewWidget = nullptr;
    bShowMouseCursor = bLightingPreviousCursor;
    SetInputMode(FInputModeGameOnly());
    FlushPressedKeys();
}

bool ATownAgePlayerController::SetLightingPreviewTime(ETownAgeLightingPreview Period)
{
#if !UE_BUILD_SHIPPING
    if (!LightingPreviewWidget || !HasAuthority() || !IsLocalController()) return false;
    auto* Clock = GetWorld()->GetGameState<ATownAgeGameState>();
    constexpr double Hours[] = {8.0, 12.0, 17.5, 22.0};
    const uint8 Index = static_cast<uint8>(Period);
    return Clock && Index < UE_ARRAY_COUNT(Hours) && Clock->SetTimeOfDay(Hours[Index]);
#else
    return false;
#endif
}

void ATownAgePlayerController::OpenChat()
{
    if (const auto* TownPlayer = Cast<ATownAgePlayer>(GetPawn()); TownPlayer && TownPlayer->IsCustomizing()) return;
    if (!ChatWidget || bChatOpen) return;
    ReleaseDebugTeleportCursor();
    CloseLightingPreview();
    bChatOpen = true;
    bPreviousCursor = bShowMouseCursor;
    bShowMouseCursor = true;
    SetIgnoreMoveInput(true);
    SetIgnoreLookInput(true);
    ChatWidget->SetChatOpen(true);
    FInputModeUIOnly Mode;
    Mode.SetWidgetToFocus(ChatWidget->TakeWidget());
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    SetInputMode(Mode);
    ChatWidget->FocusEntry();
}

void ATownAgePlayerController::CloseChat()
{
    if (!bChatOpen) return;
    bChatOpen = false;
    SetIgnoreMoveInput(false);
    SetIgnoreLookInput(false);
    bShowMouseCursor = bPreviousCursor;
    SetInputMode(FInputModeGameOnly());
    FlushPressedKeys();
    if (ChatWidget) ChatWidget->SetChatOpen(false);
}

bool ATownAgePlayerController::SubmitChat(const FString& Message)
{
    const FString Clean = TownAgeChat::Sanitize(Message);
    if (Clean.IsEmpty() || bChatPending) return false;
    PendingDraft = Message;
    bChatPending = true;
    ServerSendChat(Clean);
    return true;
}

void ATownAgePlayerController::ServerSendChat_Implementation(const FString& Message)
{
    if (!PlayerState || !GetWorld())
    { ClientChatResult(false, TEXT("Chat is not ready yet.")); return; }
    // Oversized requests are rejected rather than allocating unbounded display history.
    if (Message.Len() > TownAgeChat::MaxLength)
    { ClientChatResult(false, TEXT("Message too long (200 characters maximum).")); return; }
    const FString Clean = TownAgeChat::Sanitize(Message);
    if (Clean.IsEmpty()) { ClientChatResult(false, TEXT("Message is empty.")); return; }
    const double Now = GetWorld()->GetTimeSeconds();
    if (!TownAgeChat::CanSend(Now, LastChatTime))
    { ClientChatResult(false, TEXT("Please wait a moment before sending again. Your draft was kept.")); return; }
    LastChatTime = Now;
    ClientChatResult(true, FString());
    FString Sender = TownAgeChat::Sanitize(PlayerState->GetPlayerName(), 32);
    if (Sender.IsEmpty()) Sender = FString::Printf(TEXT("Player %d"), PlayerState->GetPlayerId());
    for (FConstPlayerControllerIterator It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (ATownAgePlayerController* Recipient = Cast<ATownAgePlayerController>(It->Get()))
            Recipient->ClientReceiveChat(Sender, Clean, Recipient == this);
}

void ATownAgePlayerController::ClientReceiveChat_Implementation(const FString& Sender, const FString& Message, bool bOwnMessage)
{
    if (ChatWidget) ChatWidget->AppendMessage(Sender, Message, !bOwnMessage);
}

void ATownAgePlayerController::ClientChatResult_Implementation(bool bAccepted, const FString& Notice)
{
    if (ChatWidget)
    {
        if (bAccepted) ChatWidget->ClearAcceptedDraft(PendingDraft);
        else if (!Notice.IsEmpty()) ChatWidget->AppendMessage(TEXT("TownAge"), Notice);
    }
    PendingDraft.Reset();
    bChatPending = false;
}
