#pragma once
#include "CoreMinimal.h"
#include "EdMode.h"

class FTownAgeMapEdMode : public FEdMode
{
public:
    virtual void Exit() override;
    virtual bool HandleClick(FEditorViewportClient* Client, HHitProxy* Hit, const FViewportClick& Click) override;
    virtual bool MouseMove(FEditorViewportClient* Client, FViewport* Viewport, int32 X, int32 Y) override;
    virtual bool InputKey(FEditorViewportClient* Client, FViewport* Viewport, FKey Key, EInputEvent Event) override;
    virtual void Render(const FSceneView* View, FViewport* Viewport, FPrimitiveDrawInterface* PDI) override;
    virtual bool UsesToolkits() const override { return false; }
    virtual bool UsesTransformWidget() const override;
    virtual bool UsesTransformWidget(UE::Widget::EWidgetMode CheckMode) const override;
    virtual bool ShouldDrawWidget() const override;
    virtual FVector GetWidgetLocation() const override;
    virtual EAxisList::Type GetWidgetAxisToDraw(UE::Widget::EWidgetMode Mode) const override;
    virtual bool StartTracking(FEditorViewportClient* Client, FViewport* Viewport) override;
    virtual bool EndTracking(FEditorViewportClient* Client, FViewport* Viewport) override;
    virtual bool InputDelta(FEditorViewportClient* Client, FViewport* Viewport, FVector& Drag, FRotator& Rot, FVector& Scale) override;
    void CancelDraft();
private:
    bool GroundPoint(const FVector& Origin, const FVector& Direction, FVector& LocalPoint) const;
    bool CommitDraft();
    TArray<FVector> Draft;
    FVector Hover = FVector::ZeroVector;
    bool bHasHover = false;
    bool bTrackingElement = false;
    TUniquePtr<class FScopedTransaction> MoveTransaction;
};
