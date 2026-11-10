#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "TownAgeCosmeticModules.h"
#include "TownAgeCustomizationWidget.generated.h"

class UTextureRenderTarget2D;

DECLARE_MULTICAST_DELEGATE_OneParam(FTownAgeColorSelected, uint8);
DECLARE_MULTICAST_DELEGATE_OneParam(FTownAgeCategorySelected, ETownAgeCosmeticCategory);
DECLARE_MULTICAST_DELEGATE_OneParam(FTownAgeMakeupChanged, const FTownAgeMakeupState&);
DECLARE_MULTICAST_DELEGATE_OneParam(FTownAgeOriginalPreviewChanged, bool);
DECLARE_MULTICAST_DELEGATE(FTownAgeCustomizationClosed);

UCLASS()
class TOWNAGE_API UTownAgeCustomizationWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetPreviewTexture(UTextureRenderTarget2D* Texture);
    void SetSelectedColor(uint8 Index);
    void SetReady(bool bInReady);
    void SetCategory(ETownAgeCosmeticCategory InCategory);
    void SetMakeupState(const FTownAgeMakeupState& InState);
    void SetDyeAvailable(bool bInAvailable);
    void SetMakeupAvailable(bool bInAvailable);
    void SetAllowedCategories(uint8 Mask);
    FTownAgeColorSelected OnColorSelected;
    FTownAgeCategorySelected OnCategorySelected;
    FTownAgeMakeupChanged OnMakeupChanged;
    FTownAgeOriginalPreviewChanged OnOriginalPreview;
    FTownAgeCustomizationClosed OnCloseRequested;
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaTime) override;
    virtual FReply NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
private:
    void SelectColor(uint8 Index);
    void SelectCategory(ETownAgeCosmeticCategory InCategory);
    void SelectBlush(uint8 Index);
    void SelectIris(uint8 Index);
    void QueueMakeupChange();
    void FlushMakeupChange();
    void SetAmount(int32 Index, float Value);
    UFUNCTION() void RedClicked();
    UFUNCTION() void BlueClicked();
    UFUNCTION() void GreenClicked();
    UFUNCTION() void YellowClicked();
    UFUNCTION() void CloseClicked();
    UFUNCTION() void DyeClicked();
    UFUNCTION() void SurgeryClicked();
    UFUNCTION() void MakeupClicked();
    UFUNCTION() void RoseClicked();
    UFUNCTION() void PeachClicked();
    UFUNCTION() void CoralClicked();
    UFUNCTION() void MauveClicked();
    UFUNCTION() void BrownClicked();
    UFUNCTION() void HazelClicked();
    UFUNCTION() void SageClicked();
    UFUNCTION() void BlueGrayClicked();
    UFUNCTION() void LavenderClicked();
    UFUNCTION() void ResetMakeupClicked();
    UFUNCTION() void NaturalMakeupClicked();
    UFUNCTION() void StrongMakeupClicked();
    UFUNCTION() void OriginalPreviewPressed();
    UFUNCTION() void OriginalPreviewReleased();
    UFUNCTION() void BlushChanged(float Value);
    UFUNCTION() void LinerChanged(float Value);
    UFUNCTION() void IrisChanged(float Value);
    UFUNCTION() void AegyoChanged(float Value);
    UFUNCTION() void JawChanged(float Value);
    UFUNCTION() void NoseChanged(float Value);
    UFUNCTION() void SliderCaptureBegin();
    UFUNCTION() void SliderCaptureEnd();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Customization", meta=(AllowPrivateAccess="true")) TObjectPtr<class UImage> PreviewImage;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Customization", meta=(AllowPrivateAccess="true")) TObjectPtr<class UBorder> LoadingPanel;
    UPROPERTY() TObjectPtr<class UTextBlock> Status;
    UPROPERTY() TObjectPtr<class UBorder> Panel;
    UPROPERTY() TObjectPtr<class UWidgetSwitcher> CategoryPanels;
    UPROPERTY() TArray<TObjectPtr<class UButton>> CategoryButtons;
    UPROPERTY() TArray<TObjectPtr<class USizeBox>> TouchSizes;
    UPROPERTY() TArray<TObjectPtr<class UWidget>> MakeupControls;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Customization", meta=(AllowPrivateAccess="true")) TArray<TObjectPtr<class UButton>> Chips;
    UPROPERTY() TArray<TObjectPtr<class UTextBlock>> ChipLabels;
    UPROPERTY() TArray<TObjectPtr<class USizeBox>> ChipSizes;
    UPROPERTY() TArray<TObjectPtr<class UButton>> BlushButtons;
    UPROPERTY() TArray<TObjectPtr<class UButton>> IrisButtons;
    UPROPERTY() TArray<TObjectPtr<class USlider>> AmountSliders;
    UPROPERTY() TArray<TObjectPtr<class UTextBlock>> AmountLabels;
    UPROPERTY() TObjectPtr<UTextureRenderTarget2D> PreviewTexture;
    FTownAgeMakeupState MakeupState;
    ETownAgeCosmeticCategory Category = ETownAgeCosmeticCategory::Dye;
    bool bReady = false;
    bool bDyeAvailable = true;
    bool bMakeupAvailable = true;
    bool bSyncingMakeup = false;
    bool bSliderCaptured = false;
    bool bMakeupPending = false;
    float MakeupPendingAge = 0.f;
    uint8 SelectedColor = 0;
    uint8 AllowedCategories = 7;
};
