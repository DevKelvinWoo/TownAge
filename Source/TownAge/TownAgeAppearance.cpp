#include "TownAgeAppearance.h"

#include "Components/SkeletalMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

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
    if (!IsValid(Mesh) || !IsValidHairColor(Index) || Mesh->GetNumMaterials() == 0) return false;
    UMaterialInterface* Parent = LoadObject<UMaterialInterface>(nullptr,
        TEXT("/Game/Characters/Customization/M_TownKeeper_HairDye.M_TownKeeper_HairDye"));
    if (!Parent) return false;
    UMaterialInstanceDynamic* Dynamic = Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(0));
    if (!Dynamic || Dynamic->Parent != Parent)
        Dynamic = Mesh->CreateDynamicMaterialInstance(0, Parent);
    if (!Dynamic) return false;
    Dynamic->SetVectorParameterValue(TEXT("HairTint"), HairColor(Index));
    Dynamic->SetScalarParameterValue(TEXT("DyeStrength"), Index == 0 ? 0.f : 1.f);
    return true;
}
