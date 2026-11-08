#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TownAgeMapLayout.generated.h"

UENUM(BlueprintType)
enum class ETownAgeMapElementKind : uint8
{
    Road,
    Field,
    Building
};

/** Stable type keys keep authored geometry independent from its eventual art. */
USTRUCT(BlueprintType)
struct TOWNAGE_API FTownAgeMapType
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName TypeId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) ETownAgeMapElementKind Kind = ETownAgeMapElementKind::Road;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FText DisplayName;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TSoftObjectPtr<class UStaticMesh> Mesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TSoftObjectPtr<class UMaterialInterface> Material;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FLinearColor PreviewColor = FLinearColor::White;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="50", ClampMax="10000")) float DefaultHeightCm = 300.f;
};

USTRUCT(BlueprintType)
struct TOWNAGE_API FTownAgeMapElement
{
    GENERATED_BODY()
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) FGuid Id;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Label;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) ETownAgeMapElementKind Kind = ETownAgeMapElementKind::Road;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName TypeId;
    /** Roads: polyline; fields/buildings: two opposite rectangle corners, in plan-local centimeters. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<FVector> Points;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="50", ClampMax="3000")) float WidthCm = 400.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="50", ClampMax="10000")) float HeightCm = 300.f;
};

USTRUCT()
struct TOWNAGE_API FTownAgeMapLayoutSnapshot
{
    GENERATED_BODY()
    UPROPERTY() int32 SchemaVersion = 1;
    UPROPERTY() FTransform LayoutTransform = FTransform::Identity;
    UPROPERTY() TArray<FTownAgeMapType> Types;
    UPROPERTY() TArray<FTownAgeMapElement> Elements;
};

/** Authored, level-owned layout data. Generated components are disposable derived geometry. */
UCLASS(BlueprintType)
class TOWNAGE_API ATownAgeMapLayout : public AActor
{
    GENERATED_BODY()
public:
    ATownAgeMapLayout();
    virtual void PostRegisterAllComponents() override;
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void PostInitializeComponents() override;
#if WITH_EDITOR
    virtual void PostEditChangeProperty(FPropertyChangedEvent& Event) override;
    virtual void PostEditUndo() override;
#endif
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Map Layout") TArray<FTownAgeMapType> Types;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Map Layout") TArray<FTownAgeMapElement> Elements;
    UFUNCTION(CallInEditor, BlueprintCallable, Category="Map Layout") void RebuildLayout();
    bool ValidateLayout(FString& Error) const;
    static bool ValidateData(const TArray<FTownAgeMapType>& InTypes, const TArray<FTownAgeMapElement>& InElements, FString& Error);
    FString ExportLayoutJson() const;
    /** Atomic validation: bad imports leave transform, types, elements and generated geometry untouched. */
    bool ImportLayoutJson(const FString& Json, FString& Error);
    const FTownAgeMapType* FindType(FName TypeId) const;
    FGuid GetElementIdForInstance(const class UInstancedStaticMeshComponent* Component, int32 InstanceIndex) const;
    int32 GetGeneratedInstanceCount() const;
private:
    UPROPERTY() TObjectPtr<class USceneComponent> LayoutRoot;
    UPROPERTY() TObjectPtr<class UStaticMesh> PlaceholderMesh;
    UPROPERTY() TObjectPtr<class UMaterialInterface> PlaceholderMaterial;
    UPROPERTY(Transient, NonTransactional) TArray<TObjectPtr<class UInstancedStaticMeshComponent>> GeneratedComponents;
    TMap<const UInstancedStaticMeshComponent*, TArray<FGuid>> InstanceElements;
    bool bRebuilding = false;
};
