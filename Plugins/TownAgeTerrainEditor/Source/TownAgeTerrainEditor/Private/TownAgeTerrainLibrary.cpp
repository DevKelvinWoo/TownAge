#include "TownAgeTerrainLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Editor.h"
#include "Engine/World.h"
#include "Landscape.h"
#include "LandscapeComponent.h"
#include "LandscapeInfo.h"
#include "LandscapeLayerInfoObject.h"
#include "Misc/FileHelper.h"
#include "Misc/App.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "Materials/MaterialInstanceConstant.h"
#include "ShaderCompiler.h"
#include "UObject/Package.h"

IMPLEMENT_MODULE(FDefaultModuleImpl, TownAgeTerrainEditor)

int32 UTownAgeTerrainLibrary::FinalizeVillageLandscape(ALandscape* Landscape)
{
    if (!Landscape || !GEditor || Landscape->GetWorld() != GEditor->GetEditorWorldContext().World() ||
        Landscape->GetOutermost()->GetName() != TEXT("/Game/Maps/L_VillageTerrain_01") || !FApp::CanEverRender())
    {
        UE_LOG(LogTemp, Error, TEXT("Village finalization requires the generated map in a rendering editor"));
        return INDEX_NONE;
    }
    auto Describe = [&](const TCHAR* Stage)
    {
        int32 Allocations = 0;
        for (ULandscapeComponent* Component : Landscape->LandscapeComponents)
        {
            Allocations += Component->GetWeightmapLayerAllocations().Num();
            UE_LOG(LogTemp, Display, TEXT("Village %s %s: MIs=%d weightTextures=%d allocations=%d"), Stage,
                *Component->GetName(), Component->MaterialInstances.Num(), Component->GetWeightmapTextures().Num(),
                Component->GetWeightmapLayerAllocations().Num());
            for (UMaterialInstanceConstant* Instance : Component->MaterialInstances)
            {
                UE_LOG(LogTemp, Display, TEXT("  MI=%s class=%s parent=%s parentClass=%s"),
                    *GetPathNameSafe(Instance), *GetNameSafe(Instance ? Instance->GetClass() : nullptr),
                    *GetPathNameSafe(Instance ? Instance->Parent.Get() : nullptr),
                    *GetNameSafe(Instance && Instance->Parent ? Instance->Parent->GetClass() : nullptr));
            }
        }
        return Allocations;
    };
    Describe(TEXT("before"));
    if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
    Landscape->ForceLayersFullUpdate();
    Landscape->UpdateAllComponentMaterialInstances(true);
    if (GShaderCompilingManager) GShaderCompilingManager->FinishAllCompilation();
    Landscape->ForceUpdateLayersContent();
    Landscape->MarkPackageDirty();
    return Describe(TEXT("after"));
}

ALandscape* UTownAgeTerrainLibrary::ImportVillageLandscape(const FString& SourceDirectory, UMaterialInterface* Material)
{
    constexpr int32 Size = 253;
    constexpr int32 Samples = Size * Size;
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World || World->WorldType != EWorldType::Editor || !Material)
    {
        UE_LOG(LogTemp, Error, TEXT("Village import requires an editor world and landscape material"));
        return nullptr;
    }
    TArray<uint8> HeightBytes;
    const FString HeightPath = FPaths::Combine(SourceDirectory, TEXT("Height.r16"));
    if (!FFileHelper::LoadFileToArray(HeightBytes, *HeightPath) || HeightBytes.Num() != Samples * sizeof(uint16))
    {
        UE_LOG(LogTemp, Error, TEXT("Village heightmap must contain 253x253 little-endian uint16 samples"));
        return nullptr;
    }
    TArray<uint16> Heights;
    Heights.SetNumUninitialized(Samples);
    for (int32 Index = 0; Index < Samples; ++Index)
    {
        Heights[Index] = uint16(HeightBytes[Index * 2]) | (uint16(HeightBytes[Index * 2 + 1]) << 8);
    }
    const TArray<FName> Names = { TEXT("Grass"), TEXT("Paving"), TEXT("Earth") };
    TArray<FLandscapeImportLayerInfo> Layers;
    for (const FName Name : Names)
    {
        FLandscapeImportLayerInfo Layer(Name);
        Layer.SourceFilePath = FPaths::Combine(SourceDirectory, Name.ToString() + TEXT(".r8"));
        if (!FFileHelper::LoadFileToArray(Layer.LayerData, *Layer.SourceFilePath) || Layer.LayerData.Num() != Samples)
        {
            UE_LOG(LogTemp, Error, TEXT("Invalid village paint mask: %s"), *Layer.SourceFilePath);
            return nullptr;
        }
        Layers.Add(MoveTemp(Layer));
    }
    for (int32 Index = 0; Index < Samples; ++Index)
    {
        if (int32(Layers[0].LayerData[Index]) + Layers[1].LayerData[Index] + Layers[2].LayerData[Index] != 255)
        {
            UE_LOG(LogTemp, Error, TEXT("Village paint masks must sum to 255 at every vertex"));
            return nullptr;
        }
    }
    for (FLandscapeImportLayerInfo& Layer : Layers)
    {
        const FString AssetName = TEXT("LI_") + Layer.LayerName.ToString();
        const FString PackageName = TEXT("/Game/Terrain/Village01/") + AssetName;
        const FString ObjectPath = PackageName + TEXT(".") + AssetName;
        const bool bPackageExists = FPackageName::DoesPackageExist(PackageName);
        ULandscapeLayerInfoObject* Info = bPackageExists
            ? LoadObject<ULandscapeLayerInfoObject>(nullptr, *ObjectPath) : nullptr;
        if (bPackageExists && (!Info || Info->GetLayerName() != Layer.LayerName ||
            Info->GetBlendMethod() != ELandscapeTargetLayerBlendMethod::FinalWeightBlending))
        {
            UE_LOG(LogTemp, Error, TEXT("Existing layer-info package is incompatible: %s"), *PackageName);
            return nullptr;
        }
        if (!Info)
        {
            Info = NewObject<ULandscapeLayerInfoObject>(CreatePackage(*PackageName), *AssetName,
                RF_Public | RF_Standalone | RF_Transactional);
            Info->SetLayerName(Layer.LayerName, false);
            Info->SetBlendMethod(ELandscapeTargetLayerBlendMethod::FinalWeightBlending, false);
            FAssetRegistryModule::AssetCreated(Info);
            Info->MarkPackageDirty();
        }
        Layer.LayerInfo = Info;
    }
    ALandscape* Landscape = World->SpawnActor<ALandscape>(FVector(-12600, -12600, 0), FRotator::ZeroRotator);
    if (!Landscape)
    {
        UE_LOG(LogTemp, Error, TEXT("Could not spawn village Landscape actor"));
        return nullptr;
    }
    Landscape->SetActorLabel(TEXT("Village01_Landscape"));
    Landscape->SetActorScale3D(FVector(100, 100, 100));
    Landscape->LandscapeMaterial = Material;
    Landscape->StaticLightingLOD = 0;
    TMap<FGuid, TArray<uint16>> HeightLayers;
    HeightLayers.Add(FGuid(), MoveTemp(Heights));
    TMap<FGuid, TArray<FLandscapeImportLayerInfo>> PaintLayers;
    PaintLayers.Add(FGuid(), Layers);
    Landscape->Import(FGuid::NewGuid(), 0, 0, Size - 1, Size - 1, 1, 63, HeightLayers,
        *HeightPath, PaintLayers, ELandscapeImportAlphamapType::Additive, TArrayView<const FLandscapeLayer>());
    ULandscapeInfo* Info = Landscape->GetLandscapeInfo();
    if (!Info)
    {
        UE_LOG(LogTemp, Error, TEXT("Village Landscape import did not produce LandscapeInfo"));
        return nullptr;
    }
    Info->UpdateLayerInfoMap(Landscape);
    for (const FLandscapeImportLayerInfo& Layer : Layers)
    {
        Landscape->AddTargetLayer(Layer.LayerName, FLandscapeTargetLayerSettings(Layer.LayerInfo, Layer.SourceFilePath));
    }
    Landscape->UpdateAllComponentMaterialInstances();
    Landscape->MarkPackageDirty();
    UE_LOG(LogTemp, Display, TEXT("Village Landscape imported: %d render components, %d collision components"),
        Landscape->LandscapeComponents.Num(), Landscape->CollisionComponents.Num());
    return Landscape;
}
