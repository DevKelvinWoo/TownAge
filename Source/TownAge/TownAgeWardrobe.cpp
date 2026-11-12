#include "TownAgeWardrobe.h"

#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

void TownAgeWardrobe::ApplyMesh(USkeletalMeshComponent& Component, USkeletalMesh& Asset)
{
    if (Component.GetSkeletalMeshAsset() == &Asset) return;
    Component.SetSkeletalMesh(&Asset, false);

    // Keep the face atlas override in slot zero. Assign the new fabric
    // explicitly so the render proxy updates the added or replaced slot.
    constexpr int32 FabricSlot = 1;
    const auto& Materials = Asset.GetMaterials();
    Component.SetMaterial(FabricSlot, Materials.IsValidIndex(FabricSlot)
        ? Materials[FabricSlot].MaterialInterface.Get() : nullptr);
}
