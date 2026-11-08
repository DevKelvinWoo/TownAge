#include "TownAgeTimeSky.h"
#include "TownAgeGameState.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureCube.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    struct FSkyPalette
    {
        double Hour;
        FLinearColor Zenith, Horizon, Cloud, SunTint;
    };

    FSkyPalette SamplePalette(double Hour)
    {
        // Linear colors; duplicate midnight makes the 24 -> 0 seam continuous.
        static const FSkyPalette Keys[] = {
            {0, {.008f,.012f,.035f}, {.025f,.035f,.07f}, {.025f,.03f,.055f}, {.55f,.65f,1.f}},
            {4.5, {.012f,.025f,.07f}, {.09f,.065f,.11f}, {.08f,.065f,.10f}, {.78f,.65f,.55f}},
            {6.5, {.12f,.22f,.40f}, {.78f,.40f,.22f}, {.72f,.46f,.32f}, {1.f,.64f,.38f}},
            {10, {.035f,.22f,.55f}, {.45f,.68f,.85f}, {.85f,.90f,.96f}, {1.f,.96f,.86f}},
            {14, {.035f,.22f,.55f}, {.45f,.68f,.85f}, {.85f,.90f,.96f}, {1.f,.96f,.86f}},
            {17, {.12f,.20f,.38f}, {.78f,.43f,.24f}, {.76f,.50f,.35f}, {1.f,.66f,.40f}},
            {18.5, {.065f,.055f,.17f}, {.38f,.12f,.13f}, {.25f,.12f,.18f}, {1.f,.38f,.22f}},
            {20.5, {.008f,.012f,.035f}, {.025f,.035f,.07f}, {.025f,.03f,.055f}, {.55f,.65f,1.f}},
            {24, {.008f,.012f,.035f}, {.025f,.035f,.07f}, {.025f,.03f,.055f}, {.55f,.65f,1.f}}
        };
        for (int32 I = 1; I < UE_ARRAY_COUNT(Keys); ++I)
        {
            if (Hour > Keys[I].Hour) continue;
            const FSkyPalette& A = Keys[I - 1];
            const FSkyPalette& B = Keys[I];
            const float T = FMath::Clamp(float((Hour - A.Hour) / (B.Hour - A.Hour)), 0.f, 1.f);
            const float Blend = T * T * (3.f - 2.f * T);
            return {Hour, FMath::Lerp(A.Zenith, B.Zenith, Blend), FMath::Lerp(A.Horizon, B.Horizon, Blend),
                FMath::Lerp(A.Cloud, B.Cloud, Blend), FMath::Lerp(A.SunTint, B.SunTint, Blend)};
        }
        return Keys[0];
    }
}

ATownAgeTimeSky::ATownAgeTimeSky()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickInterval = .1f;
    bReplicates = false;
    SkyDome = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("TimeSkyDome"));
    SetRootComponent(SkyDome);
    SkyDome->SetMobility(EComponentMobility::Movable);
    SkyDome->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    SkyDome->SetGenerateOverlapEvents(false);
    SkyDome->SetCanEverAffectNavigation(false);
    SkyDome->SetCastShadow(false);
    SkyDome->SetReceivesDecals(false);
    SkyDome->bAffectDistanceFieldLighting = false;
    SkyDome->SetRelativeScale3D(FVector(10000.f));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Mesh(TEXT("/Engine/EngineSky/SM_SkySphere.SM_SkySphere"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Engine/EngineSky/M_Sky_Panning_Clouds2.M_Sky_Panning_Clouds2"));
    static ConstructorHelpers::FObjectFinder<UTextureCube> Cubemap(TEXT("/Engine/MapTemplates/Sky/DaylightAmbientCubemap.DaylightAmbientCubemap"));
    if (Mesh.Succeeded()) SkyDome->SetStaticMesh(Mesh.Object);
    SkyMaterial = Material.Object;
    AmbientCubemap = Cubemap.Object;
    Exposure = CreateDefaultSubobject<UPostProcessComponent>(TEXT("TimeExposure"));
    Exposure->SetupAttachment(SkyDome);
    Exposure->bUnbound = true;
    Exposure->Priority = 1.f;
    Exposure->Settings.bOverride_AutoExposureBias = true;
    Exposure->Settings.bOverride_AutoExposureSpeedUp = true;
    Exposure->Settings.bOverride_AutoExposureSpeedDown = true;
    Exposure->Settings.AutoExposureSpeedUp = 4.f;
    Exposure->Settings.AutoExposureSpeedDown = 4.f;
}

void ATownAgeTimeSky::BeginPlay()
{
    Super::BeginPlay();
    if (GetNetMode() == NM_DedicatedServer) { SetActorTickEnabled(false); return; }
    if (SkyMaterial)
    {
        SkyInstance = UMaterialInstanceDynamic::Create(SkyMaterial, this);
        SkyDome->SetMaterial(0, SkyInstance);
    }
    UWorld* World = GetWorld();
    // Touch only persistent outdoor lighting, never streamed house lighting.
    for (TActorIterator<ADirectionalLight> It(World); It; ++It)
    {
        if (It->GetLevel() != World->PersistentLevel) continue;
        Sun = Cast<UDirectionalLightComponent>(It->GetLightComponent());
        if (Sun) break;
    }
    if (!Sun)
    {
        ADirectionalLight* Created = World->SpawnActor<ADirectionalLight>();
        if (Created) Sun = Cast<UDirectionalLightComponent>(Created->GetLightComponent());
    }
    if (Sun)
    {
        PeakSunIntensity = FMath::Max(.01f, Sun->Intensity);
        Sun->SetMobility(EComponentMobility::Movable);
        Sun->SetAtmosphereSunLight(true);
    }
    for (TActorIterator<ASkyLight> It(World); It; ++It)
    {
        if (It->GetLevel() != World->PersistentLevel) continue;
        SkyFill = It->GetLightComponent();
        if (SkyFill) break;
    }
    if (!SkyFill)
    {
        ASkyLight* Created = World->SpawnActor<ASkyLight>();
        if (Created) SkyFill = Created->GetLightComponent();
    }
    if (SkyFill)
    {
        PeakSkyIntensity = FMath::Max(.1f, SkyFill->Intensity);
        SkyFill->SetMobility(EComponentMobility::Movable);
        SkyFill->SetRealTimeCaptureEnabled(false);
        if (AmbientCubemap)
        {
            // A fixed environment gives late joiners the same ambient baseline,
            // regardless of whether their first frame occurs at noon or night.
            SkyFill->SourceType = SLS_SpecifiedCubemap;
            SkyFill->SetCubemap(AmbientCubemap);
        }
    }
    // Legacy sky BPs can paint a second, unchanging sky over the new backdrop.
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (*It == this || It->GetLevel() != World->PersistentLevel) continue;
        const FString ClassName = It->GetClass()->GetName();
        if (ClassName.StartsWith(TEXT("BP_Sky_Sphere")) || ClassName.StartsWith(TEXT("BP_Sky_Shere")))
            It->SetActorHiddenInGame(true);
    }
    // This material is the complete stylized sky. The physical atmosphere would
    // otherwise apply aerial extinction over the distant emissive dome and
    // collapse its night palette to black when the physical sun disappears.
    for (TActorIterator<ASkyAtmosphere> It(World); It; ++It)
        if (It->GetLevel() == World->PersistentLevel)
            It->GetComponent()->SetVisibility(false);
    UpdateSky();
    // Intensity/tint changes reuse one convolution. No scene recapture or
    // real-time cloud capture is requested on mobile each frame.
}

void ATownAgeTimeSky::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    UpdateSky();
}

void ATownAgeTimeSky::UpdateSky()
{
    const ATownAgeGameState* Clock = GetWorld()->GetGameState<ATownAgeGameState>();
    if (!Clock) return;
    const double Hour = Clock->GetTimeOfDayHours();
    const FSkyPalette Palette = SamplePalette(Hour);
    const double Orbit = (Hour - 6.0) / 24.0 * UE_DOUBLE_TWO_PI;
    const float Elevation = FMath::Sin(Orbit);
    const float Daylight = FMath::SmoothStep(-.08f, .18f, Elevation);
    const FVector SunDirection(FMath::Cos(Orbit) * .70710678, FMath::Cos(Orbit) * .70710678, Elevation);
    const FVector MoonDirection = FVector(-.35, .45, .82).GetSafeNormal();
    const FVector KeyDirection = (SunDirection * Daylight + MoonDirection * (1.f - Daylight)).GetSafeNormal();
    const float MoonTintBlend = FMath::SmoothStep(.7f, 1.f, 1.f - Daylight);
    if (Sun)
    {
        // Reuse one mobile directional light as a soft moon key after sunset.
        // Absolute real-world moon lux would make a cozy playable village black
        // at the authored 50,000-lux daytime exposure, so retain a 3% key floor.
        Sun->SetWorldRotation((-KeyDirection).Rotation());
        Sun->SetIntensity(PeakSunIntensity * FMath::Lerp(.03f, 1.f, Daylight));
        Sun->SetLightColor(FMath::Lerp(Palette.SunTint, FLinearColor(.65f,.73f,.90f), MoonTintBlend));
    }
    if (SkyFill)
    {
        SkyFill->SetIntensity(PeakSkyIntensity * FMath::Lerp(.20f, 1.f, Daylight));
        SkyFill->SetLightColor(FMath::Lerp(FLinearColor(.44f,.55f,.82f), FLinearColor::White, Daylight));
    }
    Exposure->Settings.AutoExposureBias = FMath::Lerp(-1.25f, 0.f, Daylight);
    if (SkyInstance)
    {
        SkyInstance->SetVectorParameterValue(TEXT("Zenith Color"), Palette.Zenith);
        SkyInstance->SetVectorParameterValue(TEXT("Horizon color"), Palette.Horizon);
        SkyInstance->SetVectorParameterValue(TEXT("Cloud color"), Palette.Cloud);
        SkyInstance->SetVectorParameterValue(TEXT("Sun color"), Palette.SunTint);
        // Legacy engine sky colors use the 10-lux template lighting range.
        // Match emissive radiance to this map so 50k-lux village exposure does
        // not erase the authored gradient/stars, while the test map stays mild.
        const float RadianceScale = FMath::Max(1.f, PeakSunIntensity / 10.f);
        SkyInstance->SetVectorParameterValue(TEXT("Overall Color"), FLinearColor(RadianceScale, RadianceScale, RadianceScale));
        SkyInstance->SetVectorParameterValue(TEXT("SunVector"), FLinearColor(SunDirection.X, SunDirection.Y, SunDirection.Z));
        SkyInstance->SetScalarParameterValue(TEXT("Sun height"), Elevation);
        SkyInstance->SetScalarParameterValue(TEXT("Sun brightness"), Daylight * 35.f);
        // The legacy stars texture produces dark speckles at this HDR scale.
        // Keep the calm night gradient without that optional texture layer.
        SkyInstance->SetScalarParameterValue(TEXT("Stars brightness"), 0.f);
        SkyInstance->SetScalarParameterValue(TEXT("Cloud opacity"), .45f);
        SkyInstance->SetScalarParameterValue(TEXT("Cloud speed"), .15f);
        SkyInstance->SetScalarParameterValue(TEXT("Horizon Falloff"), 3.f);
    }
    if (const APlayerController* PC = GetWorld()->GetFirstPlayerController())
        if (PC->PlayerCameraManager) SetActorLocation(PC->PlayerCameraManager->GetCameraLocation());
}
