#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "TownAgeCustomizationWidget.generated.h"

class UTextureRenderTarget2D;

DECLARE_MULTICAST_DELEGATE_OneParam(FTownAgeColorSelected, uint8);
DECLARE_MULTICAST_DELEGATE_OneParam(FTownAgePreviewViewChanged, bool);
DECLARE_MULTICAST_DELEGATE(FTownAgeCustomizationClosed);

UCLASS()
class TOWNAGE_API UTownAgeCustomizationWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetPreviewTexture(UTextureRenderTarget2D* Texture);
    void SetSelectedColor(uint8 Index);
    void SetReady(bool bInReady);
    void SetFaceView(bool bInFaceView);
    void SetDyeAvailable(bool bInAvailable);
    FTownAgeColorSelected OnColorSelected;
    FTownAgePreviewViewChanged OnViewChanged;
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
    UFUNCTION() void FullBodyClicked();
    UFUNCTION() void FaceClicked();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Customization", meta=(AllowPrivateAccess="true")) TObjectPtr<class UImage> PreviewImage;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Customization", meta=(AllowPrivateAccess="true")) TObjectPtr<class UBorder> LoadingPanel;
    UPROPERTY() TObjectPtr<class UTextBlock> Status;
    UPROPERTY() TObjectPtr<class UBorder> Panel;
    UPROPERTY() TObjectPtr<class USizeBox> CloseSize;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Customization", meta=(AllowPrivateAccess="true")) TArray<TObjectPtr<class UButton>> Chips;
    UPROPERTY() TArray<TObjectPtr<class UTextBlock>> ChipLabels;
    UPROPERTY() TArray<TObjectPtr<class USizeBox>> ChipSizes;
    UPROPERTY() TArray<TObjectPtr<class UButton>> ViewButtons;
    UPROPERTY() TArray<TObjectPtr<class USizeBox>> ViewSizes;
    UPROPERTY() TObjectPtr<UTextureRenderTarget2D> PreviewTexture;
    bool bReady = false;
    bool bFaceView = false;
    bool bDyeAvailable = true;
    uint8 SelectedColor = 0;
};
