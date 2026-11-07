#pragma once
#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "TownAgeHUD.generated.h"

UCLASS()
class TOWNAGE_API ATownAgeHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
};
