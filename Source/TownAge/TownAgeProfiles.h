#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "TownAgeCosmeticModules.h"
#include "TownAgeWardrobe.h"
#include "TownAgeProfiles.generated.h"

USTRUCT()
struct FTownAgeAppearanceProfile
{
    GENERATED_BODY()
    UPROPERTY() uint8 HairColorIndex = 0;
    UPROPERTY() FTownAgeMakeupState Makeup;

    UPROPERTY() uint8 Outfit = TownAgeWardrobe::Default;
    UPROPERTY() uint8 OwnedOutfits = TownAgeWardrobe::TestOwnership;

    bool IsValid() const;
};

enum class ETownAgeProfileLoad : uint8 { Missing, Loaded, Failed };

// The local provider runs bounded file operations on the game thread. A remote
// provider must preload into a cache and drain its writes outside gameplay.
UCLASS(Abstract)
class TOWNAGE_API UTownAgeProfileStore : public UObject
{
    GENERATED_BODY()
public:
    virtual bool Open(const FString& Directory) { return false; }
    virtual ETownAgeProfileLoad Read(const FString& Account, FTownAgeAppearanceProfile& Out) { return ETownAgeProfileLoad::Failed; }
    virtual bool Write(const FString& Account, const FTownAgeAppearanceProfile& Profile) { return false; }
};

UCLASS()
class TOWNAGE_API UTownAgeLocalProfileStore : public UTownAgeProfileStore
{
    GENERATED_BODY()
public:
    virtual bool Open(const FString& Directory) override;
    virtual ETownAgeProfileLoad Read(const FString& Account, FTownAgeAppearanceProfile& Out) override;
    virtual bool Write(const FString& Account, const FTownAgeAppearanceProfile& Profile) override;
private:
    FString Root;
    FString ProfilePath(const FString& Account) const;
};

UCLASS(Config=Game)
class TOWNAGE_API UTownAgeProfiles : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Deinitialize() override;
    bool LoadAppearance(const FString& Account, FTownAgeAppearanceProfile& Out);
    bool StageAppearance(const FString& Account, const FTownAgeAppearanceProfile& Profile);
    void FlushAppearance();
private:
    UPROPERTY(Config) TSoftClassPtr<UTownAgeProfileStore> StoreClass;
    UPROPERTY(Transient) TObjectPtr<UTownAgeProfileStore> Store;
    TMap<FString, FTownAgeAppearanceProfile> Profiles;
    TSet<FString> DirtyAccounts;
    FTSTicker::FDelegateHandle SaveTicker;
    bool bStoreAttempted = false;
    bool IsAuthorityWorld() const;
    bool EnsureStore();
    bool TickSave(float DeltaTime);
};
