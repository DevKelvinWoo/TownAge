#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TownAgeTimeSky.generated.h"

/** Local presentation of the authoritative GameState clock; never owns time. */
UCLASS(Config=Game, NotBlueprintable)
class TOWNAGE_API ATownAgeTimeSky : public AActor
{
    GENERATED_BODY()
public:
    ATownAgeTimeSky();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;

private:
    void UpdateSky();

    UPROPERTY(Config) TArray<FName> CozyVillageLightingMaps;
    UPROPERTY(Config) TArray<FName> WarmIllustratedLightingMaps;
    UPROPERTY() TObjectPtr<class UStaticMeshComponent> SkyDome;
    UPROPERTY() TObjectPtr<class UPostProcessComponent> Exposure;
    UPROPERTY() TObjectPtr<class UMaterialInterface> SkyMaterial;
    UPROPERTY() TObjectPtr<class UMaterialInstanceDynamic> SkyInstance;
    UPROPERTY() TObjectPtr<class UTextureCube> AmbientCubemap;
    UPROPERTY() TObjectPtr<class UDirectionalLightComponent> Sun;
    UPROPERTY() TObjectPtr<class USkyLightComponent> SkyFill;
    float PeakSunIntensity = 10.f;
    float PeakSkyIntensity = 1.f;
    bool bCozyVillageLighting = false;
    bool bWarmIllustratedLighting = false;
};
