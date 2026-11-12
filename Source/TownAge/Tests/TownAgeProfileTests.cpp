#include "../TownAgeProfiles.h"
#include "HAL/FileManager.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTownAgeProfileRoundTripTest, "TownAge.Profiles.DurableAppearance",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FTownAgeProfileRoundTripTest::RunTest(const FString& Parameters)
{
    const FString Directory = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() /
        TEXT("Automation/ProfileTests") / FGuid::NewGuid().ToString());
    const FString Account = TEXT("test:../first");
    auto* Store = NewObject<UTownAgeLocalProfileStore>();
    if (!TestTrue(TEXT("Open isolated storage"), Store->Open(Directory))) return false;
    FTownAgeAppearanceProfile Profile;
    TestTrue(TEXT("Unseen account has no profile"), Store->Read(Account, Profile) == ETownAgeProfileLoad::Missing);
    Profile.HairColorIndex = 2;
    Profile.Makeup.BlushAmount = 33;
    Profile.Makeup.IrisColor = 3;
    Profile.Makeup.NoseAmount = 81;
    TestTrue(TEXT("Write first snapshot"), Store->Write(Account, Profile));
    Profile.HairColorIndex = 4;
    Profile.OwnedOutfits = 1 << TownAgeWardrobe::PinkDress;
    Profile.Outfit = TownAgeWardrobe::PinkDress;
    TestTrue(TEXT("Replace snapshot"), Store->Write(Account, Profile));

    auto* Reopened = NewObject<UTownAgeLocalProfileStore>();
    TestTrue(TEXT("Fresh provider opens the same storage"), Reopened->Open(Directory));
    FTownAgeAppearanceProfile Loaded;
    TestTrue(TEXT("Read from disk through a fresh provider"), Reopened->Read(Account, Loaded) == ETownAgeProfileLoad::Loaded);
    TestEqual(TEXT("Latest hair"), Loaded.HairColorIndex, uint8(4));
    TestEqual(TEXT("Makeup amount"), Loaded.Makeup.BlushAmount, uint8(33));
    TestEqual(TEXT("Iris palette"), Loaded.Makeup.IrisColor, uint8(3));
    TestEqual(TEXT("Nose amount"), Loaded.Makeup.NoseAmount, uint8(81));
    TestEqual(TEXT("Equipped garment"), Loaded.Outfit, uint8(TownAgeWardrobe::PinkDress));
    TestEqual(TEXT("Owned garments"), Loaded.OwnedOutfits, Profile.OwnedOutfits);
    TestTrue(TEXT("Another account stays isolated"), Reopened->Read(TEXT("test:second"), Loaded) == ETownAgeProfileLoad::Missing);
    Profile.Outfit = TownAgeWardrobe::YellowOveralls;
    TestFalse(TEXT("Cannot equip a garment outside the owned set"), Store->Write(Account, Profile));
    Profile.Outfit = TownAgeWardrobe::PinkDress;
    Profile.Makeup.NoseAmount = 101;
    TestFalse(TEXT("Invalid profile cannot replace saved state"), Store->Write(Account, Profile));

    IFileManager& Files = IFileManager::Get();
    TArray<FString> Records;
    Files.FindFiles(Records, *(Directory / TEXT("*.json")), true, false);
    if (TestEqual(TEXT("Identifier mapped to one file inside the root"), Records.Num(), 1))
    {
        const FString Path = Directory / Records[0];
        TestTrue(TEXT("Simulate an interrupted replace"), Files.Delete(*Path));
        TestTrue(TEXT("Previous snapshot survives the gap"), Reopened->Read(Account, Loaded) == ETownAgeProfileLoad::Loaded);
        TestEqual(TEXT("Backup hair"), Loaded.HairColorIndex, uint8(2));
        const FString LegacyRecord = FString::Printf(TEXT(
            "{\"version\":1,\"account\":\"%s\",\"appearance\":{\"hairColor\":2,\"blushColor\":0,"
            "\"blushAmount\":33,\"linerAmount\":0,\"irisColor\":3,\"irisAmount\":0,"
            "\"aegyoAmount\":0,\"jawAmount\":0,\"noseAmount\":81}}"), *Account);
        TestTrue(TEXT("Write a version 1 profile"), FFileHelper::SaveStringToFile(LegacyRecord, *Path));
        TestTrue(TEXT("Read a version 1 profile"), Reopened->Read(Account, Loaded) == ETownAgeProfileLoad::Loaded);
        TestEqual(TEXT("Version 1 defaults to the starter appearance"), Loaded.Outfit, uint8(TownAgeWardrobe::Default));
        TestEqual(TEXT("Version 1 receives test ownership"), Loaded.OwnedOutfits, TownAgeWardrobe::TestOwnership);
        TestTrue(TEXT("Write a malformed test record"), FFileHelper::SaveStringToFile(TEXT("{}"), *Path));
        TestTrue(TEXT("Malformed primary fails without silently defaulting"), Reopened->Read(Account, Loaded) == ETownAgeProfileLoad::Failed);
    }
    TArray<FString> Entries;
    Files.FindFiles(Entries, *(Directory / TEXT("*")), true, false);
    for (const FString& Entry : Entries) Files.Delete(*(Directory / Entry));
    Files.DeleteDirectory(*Directory);
    return true;
}
#endif
