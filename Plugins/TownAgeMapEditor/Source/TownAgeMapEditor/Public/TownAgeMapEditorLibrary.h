#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "TownAgeMapEditorLibrary.generated.h"

/** Editor-only batch import/export API. This module is excluded from game builds. */
UCLASS()
class TOWNAGEMAPEDITOR_API UTownAgeMapEditorLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="TownAge|Map Editor")
    static bool ImportJson(class ATownAgeMapLayout* Layout, const FString& Json, FString& Error);
    UFUNCTION(BlueprintPure, Category="TownAge|Map Editor")
    static FString ExportJson(class ATownAgeMapLayout* Layout);
    UFUNCTION(BlueprintPure, Category="TownAge|Map Editor")
    static int32 GetGeneratedInstanceCount(class ATownAgeMapLayout* Layout);
    UFUNCTION(BlueprintCallable, Category="TownAge|Map Editor")
    static void UseLayout(class ATownAgeMapLayout* Layout);
    /** Batch/editor automation entry point through the same transactional handler as the move gizmo. */
    UFUNCTION(BlueprintCallable, Category="TownAge|Map Editor")
    static bool TranslateElement(class ATownAgeMapLayout* Layout, FGuid ElementId, FVector WorldDelta);
};
