#pragma once

#include "CoreMinimal.h"

class USkeletalMesh;
class USkeletalMeshComponent;

namespace TownAgeWardrobe
{
    // Persistent catalog IDs. Keep existing values when adding garments.
    enum : uint8 { Default = 0, PinkDress = 1, YellowOveralls = 2 };
    constexpr uint8 TestOwnership = (1 << PinkDress) | (1 << YellowOveralls);

    inline bool Owns(uint8 Owned, uint8 Outfit)
    {
        return Outfit == Default || (Outfit <= YellowOveralls && (Owned & (1 << Outfit)) != 0);
    }

    void ApplyMesh(USkeletalMeshComponent& Component, USkeletalMesh& Asset);
}
