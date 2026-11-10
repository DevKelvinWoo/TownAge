#pragma once

#include "CoreMinimal.h"

class USkeletalMeshComponent;
class UMaterialInterface;
class UMeshComponent;

namespace TownAgeAppearance
{
    // Zero retains the original atlas; player-selectable dye chips are 1..4.
    constexpr uint8 NumHairColors = 4;
    TOWNAGE_API bool IsValidHairColor(uint8 Index);
    TOWNAGE_API FLinearColor HairColor(uint8 Index);
    TOWNAGE_API bool CanDyeHair(const USkeletalMeshComponent* Mesh);
    TOWNAGE_API bool IsMaskedHairMaterial(UMaterialInterface* Material);
    TOWNAGE_API bool ApplyHairColor(USkeletalMeshComponent* Mesh, uint8 Index);
    TOWNAGE_API TArray<UMeshComponent*> GetAppearanceMeshes(const USkeletalMeshComponent* Mesh);
}
