#include "TownAgeCustomizationPreview.h"

#include "TownAgeAppearance.h"
#include "Animation/AnimSequence.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "UObject/ConstructorHelpers.h"

ATownAgeCustomizationPreview::ATownAgeCustomizationPreview()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickInterval = 1.f / 30.f;
    bReplicates = false;
    StageRoot = CreateDefaultSubobject<USceneComponent>(TEXT("StageRoot"));
    SetRootComponent(StageRoot);
    Mesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("PreviewCharacter"));
    Mesh->SetupAttachment(StageRoot);
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->SetLightingChannels(false, false, true);
    Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    static ConstructorHelpers::FObjectFinder<USkeletalMesh> Model(TEXT("/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/SK_TownKeeper_Meshy.SK_TownKeeper_Meshy"));
    if (Model.Succeeded()) Mesh->SetSkeletalMesh(Model.Object);
    Floor = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PreviewFloor"));
    Floor->SetupAttachment(StageRoot);
    Floor->SetRelativeLocation(FVector(0, 0, -3));
    Floor->SetRelativeScale3D(FVector(4, 4, .05f));
    Floor->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Floor->SetLightingChannels(false, false, true);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded()) Floor->SetStaticMesh(Cube.Object);
    KeyLight = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("PreviewKeyLight"));
    KeyLight->SetupAttachment(StageRoot);
    KeyLight->SetRelativeRotation(FRotator(-35, -115, 0));
    KeyLight->SetLightingChannels(false, false, true);
    KeyLight->SetIntensity(3.f);
    KeyLight->SetLightColor(FLinearColor(1.f, .94f, .83f));
    KeyLight->SetCastShadows(false);
    FillLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("PreviewFillLight"));
    FillLight->SetupAttachment(StageRoot);
    FillLight->SetRelativeLocation(FVector(-150, 160, 160));
    FillLight->SetLightingChannels(false, false, true);
    FillLight->SetIntensity(2500.f);
    FillLight->SetAttenuationRadius(600.f);
    FillLight->SetSourceRadius(80.f);
    FillLight->SetLightColor(FLinearColor(.78f, .87f, 1.f));
    FillLight->SetCastShadows(false);
    Capture = CreateDefaultSubobject<USceneCaptureComponent2D>(TEXT("PreviewCapture"));
    Capture->SetupAttachment(StageRoot);
    const FVector CameraLocation(0, 360, 110);
    Capture->SetRelativeLocation(CameraLocation);
    Capture->SetRelativeRotation((FVector(0, 0, 88) - CameraLocation).Rotation());
    Capture->FOVAngle = 34.f;
    Capture->CaptureSource = ESceneCaptureSource::SCS_FinalColorLDR;
    Capture->PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
    Capture->bCaptureEveryFrame = false;
    Capture->bCaptureOnMovement = false;
    // A manually captured Idle portrait must stay sharp even at low frame rates.
    Capture->ShowFlags.SetTemporalAA(false);
    Capture->ShowFlags.SetAntiAliasing(false);
    Capture->ShowFlags.SetAtmosphere(false);
    Capture->ShowFlags.SetFog(false);
    Capture->ShowFlags.SetMotionBlur(false);
    Capture->PostProcessSettings.bOverride_AutoExposureMethod = true;
    Capture->PostProcessSettings.AutoExposureMethod = EAutoExposureMethod::AEM_Manual;
    Capture->PostProcessSettings.bOverride_AutoExposureBias = true;
    Capture->PostProcessSettings.AutoExposureBias = 0.f;
    Capture->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure = true;
    Capture->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure = false;
}

void ATownAgeCustomizationPreview::BeginPlay()
{
    Super::BeginPlay();
    RenderTarget = NewObject<UTextureRenderTarget2D>(this);
    RenderTarget->RenderTargetFormat = RTF_RGBA8;
    RenderTarget->ClearColor = FLinearColor(.055f, .075f, .06f, 1.f);
    RenderTarget->InitAutoFormat(768, 1024);
    RenderTarget->UpdateResourceImmediate(true);
    Capture->TextureTarget = RenderTarget;
    Capture->ShowOnlyComponent(Mesh);
    Capture->ShowOnlyComponent(Floor);
    auto* Idle = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/Animations/Locomotion01/A_TownKeeper_Meshy_Idle.A_TownKeeper_Meshy_Idle"));
    if (Idle) Mesh->PlayAnimation(Idle, true);
    Capture->CaptureScene();
    ++CapturedFrames;
}

void ATownAgeCustomizationPreview::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (Capture && RenderTarget)
    {
        Capture->CaptureScene();
        ++CapturedFrames;
    }
}

void ATownAgeCustomizationPreview::ApplyHairColor(uint8 Index)
{
    if (TownAgeAppearance::ApplyHairColor(Mesh, Index) && !bTexturesPrestreamed)
    {
        // Include the dye mask now that its material has been assigned.
        Mesh->PrestreamTextures(5.f, true);
        bTexturesPrestreamed = true;
    }
}

bool ATownAgeCustomizationPreview::IsPreviewReady() const
{
    return CapturedFrames >= 8 && RenderTarget && Mesh && Mesh->GetSkeletalMeshAsset() && Mesh->GetAnimInstance();
}
