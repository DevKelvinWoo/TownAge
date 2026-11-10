#include "TownAgeAppearance.h"

#include "Components/SkeletalMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Engine/SkeletalMesh.h"

namespace
{
FName HairParameter(UMaterialInterface* Material, FName SlotName)
{
    if (!Material) return NAME_None;
    FLinearColor Color;
    float Strength;
    if (Material->GetVectorParameterValue(FMaterialParameterInfo(TEXT("HairTint")), Color)
        && Material->GetScalarParameterValue(FMaterialParameterInfo(TEXT("DyeStrength")), Strength))
        return TEXT("HairTint");
    // A dedicated authored hair slot may expose a direct color parameter.
    if (SlotName.ToString().Contains(TEXT("Hair"), ESearchCase::IgnoreCase))
        for (FName Name : {FName(TEXT("HairTint")), FName(TEXT("HairColor"))})
            if (Material->GetVectorParameterValue(FMaterialParameterInfo(Name), Color)) return Name;
    return NAME_None;
}

bool UsesOriginalTownKeeperAtlas(const UMeshComponent* Mesh, UMaterialInterface* Material, int32 Slot)
{
    const auto* Skeletal = Cast<USkeletalMeshComponent>(Mesh);
    return Slot == 0 && Skeletal && Skeletal->GetSkeletalMeshAsset()
        && Skeletal->GetSkeletalMeshAsset()->GetPathName() == TEXT("/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/SK_TownKeeper_Meshy.SK_TownKeeper_Meshy")
        && Material && Material->GetPathName() == TEXT("/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/M_TownKeeper_Meshy.M_TownKeeper_Meshy");
}

TArray<UMeshComponent*> AppearanceMeshes(const USkeletalMeshComponent* Root)
{
    TArray<UMeshComponent*> Result;
    if (!IsValid(Root)) return Result;
    Result.Add(const_cast<USkeletalMeshComponent*>(Root));
    TArray<USceneComponent*> Children;
    Root->GetChildrenComponents(true, Children);
    for (USceneComponent* Child : Children)
        if (auto* Part = Cast<UMeshComponent>(Child); Part && Part->IsVisible()) Result.Add(Part);
    return Result;
}
}

bool TownAgeAppearance::IsValidHairColor(uint8 Index)
{
    return Index <= NumHairColors;
}

FLinearColor TownAgeAppearance::HairColor(uint8 Index)
{
    switch (Index)
    {
        case 1: return FLinearColor(.80f, .035f, .025f);
        case 2: return FLinearColor(.025f, .16f, .85f);
        case 3: return FLinearColor(.035f, .55f, .09f);
        case 4: return FLinearColor(.95f, .65f, .025f);
        default: return FLinearColor::White;
    }
}

bool TownAgeAppearance::ApplyHairColor(USkeletalMeshComponent* Mesh, uint8 Index)
{
    if (!IsValid(Mesh) || !IsValidHairColor(Index)) return false;
    bool bApplied = false;
    for (UMeshComponent* Part : AppearanceMeshes(Mesh))
    {
        const TArray<FName> Slots = Part->GetMaterialSlotNames();
        for (int32 Slot = 0; Slot < Part->GetNumMaterials(); ++Slot)
        {
        UMaterialInterface* Material = Part->GetMaterial(Slot);
        if (UsesOriginalTownKeeperAtlas(Part, Material, Slot))
        {
            Material = LoadObject<UMaterialInterface>(nullptr,
                TEXT("/Game/Characters/Customization/M_TownKeeper_HairDye.M_TownKeeper_HairDye"));
            if (!Material) continue;
            Part->SetMaterial(Slot, Material);
        }
        const FName Parameter = HairParameter(Material, Slots.IsValidIndex(Slot) ? Slots[Slot] : NAME_None);
        if (Parameter.IsNone()) continue;
        auto* Dynamic = Cast<UMaterialInstanceDynamic>(Material);
        if (!Dynamic) Dynamic = Part->CreateDynamicMaterialInstance(Slot, Material);
        if (!Dynamic) continue;
        float Strength;
        const bool bMasked = Material->GetScalarParameterValue(FMaterialParameterInfo(TEXT("DyeStrength")), Strength);
        if (Index != 0 || bMasked) Dynamic->SetVectorParameterValue(Parameter, HairColor(Index));
        if (bMasked) Dynamic->SetScalarParameterValue(TEXT("DyeStrength"), Index == 0 ? 0.f : 1.f);
        bApplied = true;
        }
    }
    return bApplied;
}

bool TownAgeAppearance::IsMaskedHairMaterial(UMaterialInterface* Material)
{
    return !HairParameter(Material, NAME_None).IsNone();
}

bool TownAgeAppearance::CanDyeHair(const USkeletalMeshComponent* Mesh)
{
    if (!IsValid(Mesh)) return false;
    for (UMeshComponent* Part : AppearanceMeshes(Mesh))
    {
        const TArray<FName> Slots = Part->GetMaterialSlotNames();
        for (int32 Slot = 0; Slot < Part->GetNumMaterials(); ++Slot)
            if (UsesOriginalTownKeeperAtlas(Part, Part->GetMaterial(Slot), Slot)
                || !HairParameter(Part->GetMaterial(Slot), Slots.IsValidIndex(Slot) ? Slots[Slot] : NAME_None).IsNone()) return true;
    }
    return false;
}
