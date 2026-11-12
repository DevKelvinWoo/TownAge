#include "TownAgeProfiles.h"

#include "Containers/Ticker.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"
#include "TownAgeAppearance.h"

DEFINE_LOG_CATEGORY_STATIC(LogTownAgeProfiles, Log, All);

namespace
{
struct FMakeupField
{
    const TCHAR* Key;
    uint8 FTownAgeMakeupState::* Member;
};

constexpr FMakeupField MakeupFields[] = {
    {TEXT("blushColor"), &FTownAgeMakeupState::BlushColor},
    {TEXT("blushAmount"), &FTownAgeMakeupState::BlushAmount},
    {TEXT("linerAmount"), &FTownAgeMakeupState::LinerAmount},
    {TEXT("irisColor"), &FTownAgeMakeupState::IrisColor},
    {TEXT("irisAmount"), &FTownAgeMakeupState::IrisAmount},
    {TEXT("aegyoAmount"), &FTownAgeMakeupState::AegyoAmount},
    {TEXT("jawAmount"), &FTownAgeMakeupState::JawAmount},
    {TEXT("noseAmount"), &FTownAgeMakeupState::NoseAmount}
};

bool ReadByte(const FJsonObject& Object, const TCHAR* Key, uint8& Out)
{
    double Value = 0;
    if (!Object.TryGetNumberField(Key, Value) || !FMath::IsFinite(Value) ||
        Value < 0 || Value > 255 || FMath::FloorToDouble(Value) != Value) return false;
    Out = static_cast<uint8>(Value);
    return true;
}
}

bool FTownAgeAppearanceProfile::IsValid() const
{
    return TownAgeAppearance::IsValidHairColor(HairColorIndex) && UTownAgeMakeupModule::Validate(Makeup)
        && (OwnedOutfits & ~TownAgeWardrobe::TestOwnership) == 0 && TownAgeWardrobe::Owns(OwnedOutfits, Outfit);
}

bool UTownAgeLocalProfileStore::Open(const FString& Directory)
{
    if (Directory.IsEmpty() || FPaths::IsRelative(Directory)) return false;
    if (!IFileManager::Get().DirectoryExists(*Directory) && !IFileManager::Get().MakeDirectory(*Directory, true))
        return false;
    Root = Directory;
    return true;
}

FString UTownAgeLocalProfileStore::ProfilePath(const FString& Account) const
{
    // Account identifiers are data, never path components.
    const FTCHARToUTF8 Utf8(*Account);
    return FPaths::Combine(Root, FMD5::HashBytes(reinterpret_cast<const uint8*>(Utf8.Get()), Utf8.Length()) + TEXT(".json"));
}

ETownAgeProfileLoad UTownAgeLocalProfileStore::Read(const FString& Account, FTownAgeAppearanceProfile& Out)
{
    if (Root.IsEmpty() || Account.IsEmpty()) return ETownAgeProfileLoad::Failed;
    FString Path = ProfilePath(Account);
    if (!IFileManager::Get().FileExists(*Path))
    {
        Path += TEXT(".bak");
        if (!IFileManager::Get().FileExists(*Path)) return ETownAgeProfileLoad::Missing;
    }
    if (IFileManager::Get().FileSize(*Path) > 16 * 1024) return ETownAgeProfileLoad::Failed;
    FString Contents;
    if (!FFileHelper::LoadFileToString(Contents, *Path)) return ETownAgeProfileLoad::Failed;
    TSharedPtr<FJsonObject> Record;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Contents), Record) || !Record.IsValid())
        return ETownAgeProfileLoad::Failed;
    FString StoredAccount;
    double Version = 0;
    const TSharedPtr<FJsonObject>* Appearance = nullptr;
    FTownAgeAppearanceProfile Loaded;
    if (!Record->TryGetNumberField(TEXT("version"), Version) || (Version != 1 && Version != 2)
        || !Record->TryGetStringField(TEXT("account"), StoredAccount) || StoredAccount != Account
        || !Record->TryGetObjectField(TEXT("appearance"), Appearance) || !Appearance->IsValid()
        || !ReadByte(*Appearance->Get(), TEXT("hairColor"), Loaded.HairColorIndex))
        return ETownAgeProfileLoad::Failed;
    for (const FMakeupField& Field : MakeupFields)
        if (!ReadByte(*Appearance->Get(), Field.Key, Loaded.Makeup.*Field.Member)) return ETownAgeProfileLoad::Failed;
    if (Version == 2 && (!ReadByte(*Appearance->Get(), TEXT("outfit"), Loaded.Outfit)
        || !ReadByte(*Appearance->Get(), TEXT("ownedOutfits"), Loaded.OwnedOutfits)))
        return ETownAgeProfileLoad::Failed;
    if (!Loaded.IsValid()) return ETownAgeProfileLoad::Failed;
    Out = Loaded;
    return ETownAgeProfileLoad::Loaded;
}

bool UTownAgeLocalProfileStore::Write(const FString& Account, const FTownAgeAppearanceProfile& Profile)
{
    if (Root.IsEmpty() || Account.IsEmpty() || !Profile.IsValid()) return false;
    const TSharedRef<FJsonObject> Appearance = MakeShared<FJsonObject>();
    Appearance->SetNumberField(TEXT("hairColor"), Profile.HairColorIndex);
    for (const FMakeupField& Field : MakeupFields)
        Appearance->SetNumberField(Field.Key, Profile.Makeup.*Field.Member);
    const TSharedRef<FJsonObject> Record = MakeShared<FJsonObject>();
    Appearance->SetNumberField(TEXT("outfit"), Profile.Outfit);
    Appearance->SetNumberField(TEXT("ownedOutfits"), Profile.OwnedOutfits);
    Record->SetNumberField(TEXT("version"), 2);
    Record->SetStringField(TEXT("account"), Account);
    Record->SetObjectField(TEXT("appearance"), Appearance);
    FString Contents;
    if (!FJsonSerializer::Serialize(Record, TJsonWriterFactory<>::Create(&Contents))) return false;
    const FString Path = ProfilePath(Account);
    const FString Temporary = Path + TEXT(".tmp");
    if (!FFileHelper::SaveStringToFile(Contents, *Temporary, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
        return false;
    // UE's replace move deletes the destination first. Keep a previous
    // snapshot available if the process stops between the two moves.
    IFileManager& Files = IFileManager::Get();
    const FString Backup = Path + TEXT(".bak");
    if (Files.FileExists(*Path) && !Files.Move(*Backup, *Path, true, false, false, true)) return false;
    return Files.Move(*Path, *Temporary, false, false, false, true);
}

bool UTownAgeProfiles::IsAuthorityWorld() const
{
    const UWorld* World = GetWorld();
    return World && World->IsGameWorld() && World->GetNetMode() != NM_Client;
}

bool UTownAgeProfiles::EnsureStore()
{
    if (bStoreAttempted) return Store != nullptr;
    bStoreAttempted = true;
    UClass* Provider = StoreClass.IsNull() ? UTownAgeLocalProfileStore::StaticClass() : StoreClass.LoadSynchronous();
    if (!Provider || Provider->HasAnyClassFlags(CLASS_Abstract)) return false;
    FString Directory = FPlatformMisc::GetEnvironmentVariable(TEXT("TOWNAGE_PROFILE_DIRECTORY"));
    FParse::Value(FCommandLine::Get(), TEXT("TownAgeProfileDirectory="), Directory);
    if (Directory.IsEmpty()) Directory = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("Profiles"));
    Store = NewObject<UTownAgeProfileStore>(this, Provider);
    if (!Store->Open(Directory))
    {
        UE_LOG(LogTownAgeProfiles, Error, TEXT("Profile store could not be opened."));
        Store = nullptr;
    }
    return Store != nullptr;
}

bool UTownAgeProfiles::LoadAppearance(const FString& Account, FTownAgeAppearanceProfile& Out)
{
    if (!IsAuthorityWorld() || Account.IsEmpty() || Account.Len() > 256 || !EnsureStore()) return false;
    if (const auto* Existing = Profiles.Find(Account))
    {
        Out = *Existing;
        return true;
    }
    FTownAgeAppearanceProfile Profile;
    if (Store->Read(Account, Profile) == ETownAgeProfileLoad::Failed || !Profile.IsValid())
    {
        UE_LOG(LogTownAgeProfiles, Error, TEXT("Profile load failed. The stored record will not be overwritten."));
        return false;
    }
    Out = Profiles.Add(Account, Profile);
    return true;
}

bool UTownAgeProfiles::StageAppearance(const FString& Account, const FTownAgeAppearanceProfile& Profile)
{
    if (!IsAuthorityWorld() || !Profiles.Contains(Account) || !Profile.IsValid()) return false;
    Profiles[Account] = Profile;
    DirtyAccounts.Add(Account);
    if (!SaveTicker.IsValid())
        SaveTicker = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &ThisClass::TickSave), 1.f);
    return true;
}

void UTownAgeProfiles::FlushAppearance()
{
    if (!Store) return;
    for (auto It = DirtyAccounts.CreateIterator(); It; ++It)
        if (Store->Write(*It, Profiles.FindChecked(*It))) It.RemoveCurrent();
    if (!DirtyAccounts.IsEmpty()) UE_LOG(LogTownAgeProfiles, Warning, TEXT("Profile writes pending: %d"), DirtyAccounts.Num());
}

bool UTownAgeProfiles::TickSave(float DeltaTime)
{
    FlushAppearance();
    if (!DirtyAccounts.IsEmpty()) return true;
    SaveTicker.Reset();
    return false;
}

void UTownAgeProfiles::Deinitialize()
{
    if (SaveTicker.IsValid()) FTSTicker::GetCoreTicker().RemoveTicker(SaveTicker);
    FlushAppearance();
    Super::Deinitialize();
}
