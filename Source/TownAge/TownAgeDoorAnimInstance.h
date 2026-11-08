#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "TownAgeDoorAnimInstance.generated.h"

/**
 * Native single-asset playback with a short pose transition when assets change.
 * The existing Blend Space still owns locomotion sample smoothing.
 */
UCLASS(Transient, NotBlueprintable)
class TOWNAGE_API UTownAgeDoorAnimInstance : public UAnimSingleNodeInstance
{
    GENERATED_BODY()
public:
    UTownAgeDoorAnimInstance(const FObjectInitializer& ObjectInitializer);

    /** Time to blend from the last displayed pose into a different animation. */
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="TownAge|Animation", meta=(ClampMin="0.0", ClampMax="1.0", Units="s"))
    float AssetBlendDuration = .22f;

protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
};
