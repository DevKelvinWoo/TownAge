#include "TownAgeCustomizationPreview.h"

#include "TownAgeAppearance.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/BlendSpace.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
void CopyMaterials(UMeshComponent* Source, UMeshComponent* Destination)
{
    for (int32 Slot = 0; Slot < Source->GetNumMaterials(); ++Slot)
    {
        UMaterialInterface* Material = Source->GetMaterial(Slot);
        if (!Material) continue;
        auto* ExistingDynamic = Cast<UMaterialInstanceDynamic>(Material);
        auto* Copy = UMaterialInstanceDynamic::Create(ExistingDynamic && ExistingDynamic->Parent ? ExistingDynamic->Parent.Get() : Material, Destination);
        if (!Copy) continue;
        Copy->CopyMaterialUniformParameters(Material);
        Destination->SetMaterial(Slot, Copy);
    }
}

UAnimationAsset* FindIdle(USkeletalMeshComponent* Source, UAnimationAsset* Override)
{
    UAnimationAsset* Asset = Override;
    if (!Asset)
        if (auto* Single = Cast<UAnimSingleNodeInstance>(Source->GetAnimInstance())) Asset = Single->GetCurrentAsset();
    if (const auto* Blend = Cast<UBlendSpace>(Asset))
    {
        const FBlendSample* Closest = nullptr;
        for (const FBlendSample& Sample : Blend->GetBlendSamples())
            if (Sample.Animation && (!Closest || Sample.SampleValue.SizeSquared() < Closest->SampleValue.SizeSquared())) Closest = &Sample;
        Asset = Closest ? Closest->Animation.Get() : nullptr;
    }
    return Asset && Source->GetSkeletalMeshAsset()
        && Asset->GetSkeleton() == Source->GetSkeletalMeshAsset()->GetSkeleton() ? Asset : nullptr;
}

void CopyMorphs(USkeletalMeshComponent* Source, USkeletalMeshComponent* Destination)
{
    for (const auto& Morph : Source->GetMorphTargetCurves()) Destination->SetMorphTarget(Morph.Key, Morph.Value);
}
}

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
    KeyLight->SetRelativeRotation(FRotator(-35, 155, 0));
    KeyLight->SetLightingChannels(false, false, true);
    KeyLight->SetIntensity(3.f);
    KeyLight->SetLightColor(FLinearColor(1.f, .94f, .83f));
    KeyLight->SetCastShadows(false);
    FillLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("PreviewFillLight"));
    FillLight->SetupAttachment(StageRoot);
    FillLight->SetRelativeLocation(FVector(160, 150, 160));
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
    // Keep these in the serialized settings: component registration rebuilds
    // ShowFlags from its archetype and would discard direct flag assignments.
    TArray<FEngineShowFlagsSetting> CaptureFlags;
    for (const TCHAR* Name : {TEXT("TemporalAA"), TEXT("AntiAliasing"), TEXT("Atmosphere"), TEXT("Fog"), TEXT("MotionBlur")})
    {
        FEngineShowFlagsSetting Flag;
        Flag.ShowFlagName = Name;
        Flag.Enabled = false;
        CaptureFlags.Add(Flag);
    }
    Capture->SetShowFlagSettings(CaptureFlags);
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
}

bool ATownAgeCustomizationPreview::InitializeFromCharacter(USkeletalMeshComponent* Source, UAnimationAsset* IdleOverride)
{
    if (!IsValid(Source) || !Source->GetSkeletalMeshAsset()) return false;
    Mesh->SetSkeletalMesh(Source->GetSkeletalMeshAsset());
    Mesh->SetRelativeRotation(Source->GetRelativeRotation());
    Mesh->SetRelativeScale3D(Source->GetComponentScale());
    Mesh->SetRelativeLocation(FVector::ZeroVector);
    CopyMaterials(Source, Mesh);
    if (auto* Idle = FindIdle(Source, IdleOverride)) Mesh->PlayAnimation(Idle, true);
    else if (Source->GetAnimClass()) Mesh->SetAnimInstanceClass(Source->GetAnimClass());
    else Mesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);
    CopyMorphs(Source, Mesh);
    const FBox LocalBounds = Mesh->GetSkeletalMeshAsset()->GetBounds().GetBox().TransformBy(Mesh->GetRelativeTransform());
    Mesh->SetRelativeLocation(FVector(0, 0, -LocalBounds.Min.Z));
    const FBox Bounds = Mesh->GetSkeletalMeshAsset()->GetBounds().GetBox().TransformBy(Mesh->GetComponentTransform());
    CharacterHeight = FMath::Max(30.f, float(Bounds.GetSize().Z));
    FullBodyTarget = Bounds.GetCenter();
    const float HalfFOV = FMath::DegreesToRadians(Capture->FOVAngle * .5f);
    FullBodyDistance = FMath::Max(CharacterHeight * .65f, float(Bounds.GetSize().Y) * .8f) / FMath::Tan(HalfFOV);
    for (FName Name : {FName(TEXT("Head")), FName(TEXT("head")), FName(TEXT("mixamorig:Head"))})
        if (Mesh->DoesSocketExist(Name)) { HeadSocket = Name; break; }
    const FVector HeadLocation = HeadSocket.IsNone() ? Bounds.GetCenter() : Mesh->GetSocketLocation(HeadSocket);
    const FVector Forward = GetActorForwardVector();
    FaceSurfaceOffset = FMath::Max(0.f, float(FVector::DotProduct(Bounds.GetCenter() - HeadLocation, Forward)
        + FVector::DotProduct(Bounds.GetExtent(), Forward.GetAbs())));
    TMap<USceneComponent*, USceneComponent*> Copies;
    Copies.Add(Source, Mesh);
    TArray<USceneComponent*> AttachedComponents;
    Source->GetChildrenComponents(true, AttachedComponents);
    for (USceneComponent* Child : AttachedComponents)
    {
        auto* SourcePart = Cast<UMeshComponent>(Child);
        USceneComponent* ParentCopy = Copies.FindRef(Child->GetAttachParent());
        if (!ParentCopy) ParentCopy = Mesh;
        if (!SourcePart)
        {
            // Retain transform-only attachment anchors, without copying their
            // gameplay/FX behavior into the portrait scene.
            auto* Anchor = NewObject<USceneComponent>(this);
            AddInstanceComponent(Anchor);
            Anchor->SetupAttachment(ParentCopy, Child->GetAttachSocketName());
            Anchor->SetRelativeTransform(Child->GetRelativeTransform());
            Anchor->RegisterComponent();
            Copies.Add(Child, Anchor);
            continue;
        }
        if (!Child->IsVisible()) continue;
        UMeshComponent* Part = nullptr;
        if (auto* Skeletal = Cast<USkeletalMeshComponent>(SourcePart))
        {
            auto* Copy = NewObject<USkeletalMeshComponent>(this);
            Copy->SetSkeletalMesh(Skeletal->GetSkeletalMeshAsset());
            Copy->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
            if (Skeletal->GetSkeletalMeshAsset() && Skeletal->GetSkeletalMeshAsset()->GetSkeleton() == Source->GetSkeletalMeshAsset()->GetSkeleton()) Copy->SetLeaderPoseComponent(Mesh);
            else if (auto* Idle = FindIdle(Skeletal, nullptr)) Copy->PlayAnimation(Idle, true);
            else Copy->SetAnimInstanceClass(Skeletal->GetAnimClass());
            CopyMorphs(Skeletal, Copy);
            Part = Copy;
        }
        else if (auto* Static = Cast<UStaticMeshComponent>(SourcePart))
        {
            auto* Copy = NewObject<UStaticMeshComponent>(this);
            Copy->SetStaticMesh(Static->GetStaticMesh());
            Part = Copy;
        }
        if (!Part) continue;
        AddInstanceComponent(Part);
        Part->SetupAttachment(ParentCopy, Child->GetAttachSocketName());
        Part->SetRelativeTransform(Child->GetRelativeTransform());
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetLightingChannels(false, false, true);
        CopyMaterials(SourcePart, Part);
        Part->RegisterComponent();
        Capture->ShowOnlyComponent(Part);
        Copies.Add(Child, Part);
    }
    Floor->SetRelativeScale3D(FVector(CharacterHeight / 42.f, CharacterHeight / 42.f, .05f));
    bInitialized = true;
    SetFaceView(false);
    Capture->SetWorldLocation(DesiredCameraLocation);
    Capture->SetWorldRotation((ViewTarget - DesiredCameraLocation).Rotation());
    return true;
}

void ATownAgeCustomizationPreview::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (bInitialized && Capture && RenderTarget)
    {
        UpdateCameraTarget();
        const FVector Location = FMath::VInterpTo(Capture->GetComponentLocation(), DesiredCameraLocation, DeltaSeconds, 12.f);
        Capture->SetWorldLocation(Location);
        Capture->SetWorldRotation((ViewTarget - Location).Rotation());
        Capture->CaptureScene();
        ++CapturedFrames;
    }
}

void ATownAgeCustomizationPreview::ApplyHairColor(uint8 Index)
{
    const bool bApplied = TownAgeAppearance::ApplyHairColor(Mesh, Index);
    if (bApplied && !bTexturesPrestreamed)
    {
        // Include the dye mask now that its material has been assigned.
        Mesh->PrestreamTextures(5.f, true);
        bTexturesPrestreamed = true;
    }
}

bool ATownAgeCustomizationPreview::IsPreviewReady() const
{
    return bInitialized && CapturedFrames >= 8 && RenderTarget && Mesh && Mesh->GetSkeletalMeshAsset() && Mesh->GetAnimInstance();
}

void ATownAgeCustomizationPreview::SetFaceView(bool bInFaceView)
{
    bFaceView = bInFaceView;
    UpdateCameraTarget();
}

void ATownAgeCustomizationPreview::UpdateCameraTarget()
{
    ViewTarget = FullBodyTarget;
    float Distance = FullBodyDistance;
    if (bFaceView)
    {
        ViewTarget = HeadSocket.IsNone() ? FullBodyTarget + FVector(0, 0, CharacterHeight * .2f)
            : Mesh->GetSocketLocation(HeadSocket);
        // Head bones often sit at the neck, especially on stylized avatars.
        // Frame the head region and account for its surface in front of the bone.
        const float HeadHeight = FMath::Clamp(float(FullBodyTarget.Z + CharacterHeight * .5f - ViewTarget.Z),
            CharacterHeight * .12f, CharacterHeight * .5f);
        ViewTarget.Z += HeadHeight * .52f;
        Distance = FMath::Max(10.f, HeadHeight * .55f)
            / FMath::Tan(FMath::DegreesToRadians(Capture->FOVAngle * .5f)) + FaceSurfaceOffset;
    }
    DesiredCameraLocation = ViewTarget + GetActorForwardVector() * Distance
        + FVector(0, 0, CharacterHeight * (bFaceView ? .015f : .13f));
}

FVector ATownAgeCustomizationPreview::GetPreviewCameraLocation() const
{
    return Capture ? Capture->GetComponentLocation() : FVector::ZeroVector;
}

bool ATownAgeCustomizationPreview::CanDyeHair() const
{
    return TownAgeAppearance::CanDyeHair(Mesh);
}
