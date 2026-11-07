#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "TownAgeTerrainLibrary.generated.h"

class ALandscape;
class UMaterialInterface;

UCLASS()
class TOWNAGETERRAINEDITOR_API UTownAgeTerrainLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    // ALandscape::Import is not reflected; keep this bridge out of the runtime game module.
    UFUNCTION(BlueprintCallable, Category="TownAge|Terrain")
    static ALandscape* ImportVillageLandscape(const FString& SourceDirectory, UMaterialInterface* Material);
    UFUNCTION(BlueprintCallable, Category="TownAge|Terrain")
    static int32 FinalizeVillageLandscape(ALandscape* Landscape);
};
