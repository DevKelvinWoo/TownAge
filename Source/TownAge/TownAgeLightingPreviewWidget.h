#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "TownAgeLightingPreviewWidget.generated.h"

UCLASS()
class TOWNAGE_API UTownAgeLightingPreviewWidget : public UUserWidget
{
    GENERATED_BODY()

protected:
    void NativeOnInitialized() override;
    FReply NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;

private:
    UFUNCTION() void SelectMorning();
    UFUNCTION() void SelectNoon();
    UFUNCTION() void SelectEvening();
    UFUNCTION() void SelectNight();
    UFUNCTION() void CloseClicked();
};
