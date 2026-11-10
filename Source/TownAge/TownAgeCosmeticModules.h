#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "TownAgeCosmeticModules.generated.h"

class USkeletalMeshComponent;

UENUM(BlueprintType)
enum class ETownAgeCosmeticCategory : uint8
{
    Dye,
    Surgery,
    Makeup
};

// Discrete, bounded appearance data; clients never submit material names or paths.
USTRUCT(BlueprintType)
struct TOWNAGE_API FTownAgeMakeupState
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) uint8 BlushColor = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) uint8 BlushAmount = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) uint8 LinerAmount = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) uint8 IrisColor = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) uint8 IrisAmount = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) uint8 AegyoAmount = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) uint8 JawAmount = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) uint8 NoseAmount = 0;
};

// These appearance services know nothing about vanity actors, shops or UI.
UCLASS()
class TOWNAGE_API UTownAgeDyeModule : public UObject
{
    GENERATED_BODY()
public:
    static bool Validate(uint8 ColorIndex);
    static bool SupportsMesh(const USkeletalMeshComponent* Mesh);
    static bool Apply(USkeletalMeshComponent* Mesh, uint8 ColorIndex);
};

UCLASS()
class TOWNAGE_API UTownAgeMakeupModule : public UObject
{
    GENERATED_BODY()
public:
    static bool Validate(const FTownAgeMakeupState& State);
    static bool SupportsMesh(const USkeletalMeshComponent* Mesh);
    static bool Apply(USkeletalMeshComponent* Mesh, const FTownAgeMakeupState& State);
    static FLinearColor BlushTint(uint8 Index);
    static FLinearColor IrisTint(uint8 Index);
};

UCLASS()
class TOWNAGE_API UTownAgeSurgeryModule : public UObject
{
    GENERATED_BODY()
public:
    static bool IsAvailable() { return false; }
};
