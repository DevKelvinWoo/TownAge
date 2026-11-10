#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TownAgeCustomizationPreview.generated.h"

UCLASS()
class TOWNAGE_API ATownAgeCustomizationPreview : public AActor
{
    GENERATED_BODY()
public:
    ATownAgeCustomizationPreview();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    UFUNCTION(BlueprintPure, Category="TownAge|Customization")
    class UTextureRenderTarget2D* GetRenderTarget() const { return RenderTarget; }
    void ApplyHairColor(uint8 Index);
    bool IsPreviewReady() const;
    UFUNCTION(BlueprintPure, Category="TownAge|Customization")
    class USkeletalMeshComponent* GetPreviewMesh() const { return Mesh; }
protected:
    UPROPERTY(VisibleAnywhere) TObjectPtr<class USceneComponent> StageRoot;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class USkeletalMeshComponent> Mesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UStaticMeshComponent> Floor;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class USceneCaptureComponent2D> Capture;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UDirectionalLightComponent> KeyLight;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UPointLightComponent> FillLight;
    UPROPERTY(Transient) TObjectPtr<class UTextureRenderTarget2D> RenderTarget;
    int32 CapturedFrames = 0;
    bool bTexturesPrestreamed = false;
};
