#include "TownAgeCosmeticModules.h"

#include "TownAgeAppearance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

namespace
{
bool HasMakeupParameters(UMaterialInterface* Material)
{
    if (!Material) return false;
    float Scalar;
    FLinearColor Color;
    for (const TCHAR* Name : {TEXT("BlushAmount"), TEXT("LinerAmount"), TEXT("IrisAmount"),
        TEXT("AegyoAmount"), TEXT("JawAmount"), TEXT("NoseAmount")})
        if (!Material->GetScalarParameterValue(FMaterialParameterInfo(Name), Scalar)) return false;
    return Material->GetVectorParameterValue(FMaterialParameterInfo(TEXT("BlushTint")), Color)
        && Material->GetVectorParameterValue(FMaterialParameterInfo(TEXT("IrisTint")), Color);
}

bool IsOriginalFaceAtlas(const UMeshComponent* Part, UMaterialInterface* Material, int32 Slot)
{
    const auto* Skeletal = Cast<USkeletalMeshComponent>(Part);
    if (Slot != 0 || !Skeletal || !Skeletal->GetSkeletalMeshAsset() || !Material) return false;
    if (Skeletal->GetSkeletalMeshAsset()->GetPathName()
        != TEXT("/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/SK_TownKeeper_Meshy.SK_TownKeeper_Meshy")) return false;
    const UMaterial* Base = Material->GetMaterial();
    if (!Base) return false;
    const FString Path = Base->GetPathName();
    return Path == TEXT("/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/M_TownKeeper_Meshy.M_TownKeeper_Meshy")
        || Path == TEXT("/Game/Characters/Customization/M_TownKeeper_HairDye.M_TownKeeper_HairDye");
}

UMaterialInterface* PreparedFaceMaterial()
{
    return LoadObject<UMaterialInterface>(nullptr,
        TEXT("/Game/Characters/Customization/M_TownKeeper_Makeup.M_TownKeeper_Makeup"));
}
}

bool UTownAgeDyeModule::Validate(uint8 ColorIndex)
{
    return ColorIndex >= 1 && ColorIndex <= TownAgeAppearance::NumHairColors;
}

bool UTownAgeDyeModule::SupportsMesh(const USkeletalMeshComponent* Mesh)
{
    return TownAgeAppearance::CanDyeHair(Mesh);
}

bool UTownAgeDyeModule::Apply(USkeletalMeshComponent* Mesh, uint8 ColorIndex)
{
    return TownAgeAppearance::ApplyHairColor(Mesh, ColorIndex);
}

bool UTownAgeMakeupModule::Validate(const FTownAgeMakeupState& State)
{
    return State.BlushColor <= 3 && State.IrisColor <= 4 && State.BlushAmount <= 100
        && State.LinerAmount <= 100 && State.IrisAmount <= 100 && State.AegyoAmount <= 100
        && State.JawAmount <= 100 && State.NoseAmount <= 100;
}

bool UTownAgeMakeupModule::SupportsMesh(const USkeletalMeshComponent* Mesh)
{
    for (UMeshComponent* Part : TownAgeAppearance::GetAppearanceMeshes(Mesh))
        for (int32 Slot = 0; Slot < Part->GetNumMaterials(); ++Slot)
        {
            UMaterialInterface* Material = Part->GetMaterial(Slot);
            if (HasMakeupParameters(Material)) return true;
            if (IsOriginalFaceAtlas(Part, Material, Slot) && HasMakeupParameters(PreparedFaceMaterial())) return true;
        }
    return false;
}

FLinearColor UTownAgeMakeupModule::BlushTint(uint8 Index)
{
    switch (Index)
    {
        case 1: return FLinearColor(.80f, .36f, .22f);
        case 2: return FLinearColor(.76f, .23f, .20f);
        case 3: return FLinearColor(.50f, .22f, .34f);
        default: return FLinearColor(.70f, .24f, .31f);
    }
}

FLinearColor UTownAgeMakeupModule::IrisTint(uint8 Index)
{
    switch (Index)
    {
        case 1: return FLinearColor(.30f, .19f, .065f);
        case 2: return FLinearColor(.16f, .23f, .14f);
        case 3: return FLinearColor(.12f, .20f, .29f);
        case 4: return FLinearColor(.23f, .18f, .28f);
        default: return FLinearColor(.18f, .085f, .035f);
    }
}

bool UTownAgeMakeupModule::Apply(USkeletalMeshComponent* Mesh, const FTownAgeMakeupState& State)
{
    if (!Validate(State)) return false;
    bool bApplied = false;
    for (UMeshComponent* Part : TownAgeAppearance::GetAppearanceMeshes(Mesh))
        for (int32 Slot = 0; Slot < Part->GetNumMaterials(); ++Slot)
        {
            UMaterialInterface* Material = Part->GetMaterial(Slot);
            if (IsOriginalFaceAtlas(Part, Material, Slot))
            {
                UMaterialInterface* Parent = PreparedFaceMaterial();
                if (!HasMakeupParameters(Parent)) continue;
                auto* Dynamic = Part->CreateDynamicMaterialInstance(Slot, Parent);
                if (!Dynamic) continue;
                Dynamic->CopyMaterialUniformParameters(Material);
                Material = Dynamic;
            }
            if (!HasMakeupParameters(Material)) continue;
            auto* Dynamic = Cast<UMaterialInstanceDynamic>(Material);
            if (!Dynamic) Dynamic = Part->CreateDynamicMaterialInstance(Slot, Material);
            if (!Dynamic) continue;
            Dynamic->SetVectorParameterValue(TEXT("BlushTint"), BlushTint(State.BlushColor));
            Dynamic->SetVectorParameterValue(TEXT("IrisTint"), IrisTint(State.IrisColor));
            Dynamic->SetScalarParameterValue(TEXT("BlushAmount"), State.BlushAmount / 100.f);
            Dynamic->SetScalarParameterValue(TEXT("LinerAmount"), State.LinerAmount / 100.f);
            Dynamic->SetScalarParameterValue(TEXT("IrisAmount"), State.IrisAmount / 100.f);
            Dynamic->SetScalarParameterValue(TEXT("AegyoAmount"), State.AegyoAmount / 100.f);
            Dynamic->SetScalarParameterValue(TEXT("JawAmount"), State.JawAmount / 100.f);
            Dynamic->SetScalarParameterValue(TEXT("NoseAmount"), State.NoseAmount / 100.f);
            bApplied = true;
        }
    return bApplied;
}
