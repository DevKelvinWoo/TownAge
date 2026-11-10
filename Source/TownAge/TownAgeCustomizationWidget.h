#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "TownAgeCustomizationWidget.generated.h"

class UTextureRenderTarget2D;

DECLARE_MULTICAST_DELEGATE_OneParam(FTownAgeColorSelected, uint8);
DECLARE_MULTICAST_DELEGATE(FTownAgeCustomizationClosed);

UCLASS()
class TOWNAGE_API UTownAgeCustomizationWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetPreviewTexture(UTextureRenderTarget2D* Texture);
    void SetSelectedColor(uint8 Index);
    void SetReady(bool bInReady);
    FTownAgeColorSelected OnColorSelected;
    FTownAgeCustomizationClosed OnCloseRequested;
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaTime) override;
    virtual FReply NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
private:
    void SelectColor(uint8 Index);
    UFUNCTION() void RedClicked();
    UFUNCTION() void BlueClicked();
    UFUNCTION() void GreenClicked();
    UFUNCTION() void YellowClicked();
    UFUNCTION() void CloseClicked();
    UPROPERTY() TObjectPtr<class UImage> PreviewImage;
    UPROPERTY() TObjectPtr<class UTextBlock> Status;
    UPROPERTY() TObjectPtr<class UBorder> Panel;
    UPROPERTY() TObjectPtr<class USizeBox> CloseSize;
    UPROPERTY() TArray<TObjectPtr<class UButton>> Chips;
    UPROPERTY() TArray<TObjectPtr<class UTextBlock>> ChipLabels;
    UPROPERTY() TArray<TObjectPtr<class USizeBox>> ChipSizes;
    UPROPERTY() TObjectPtr<UTextureRenderTarget2D> PreviewTexture;
    bool bReady = false;
    uint8 SelectedColor = 0;
};
