#include "TownAgeMapEdMode.h"
#include "TownAgeMapEditorModule.h"
#include "Editor.h"
#include "EditorViewportClient.h"
#include "Engine/World.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "ScopedTransaction.h"
#include "SceneManagement.h"
#include "UnrealWidget.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

DEFINE_LOG_CATEGORY_STATIC(LogTownAgeMapInput, Log, All);

namespace
{
    FVector ElementCenter(const FTownAgeMapElement& Element)
    {
        FVector Sum = FVector::ZeroVector;
        for (const FVector& P : Element.Points) Sum += P;
        return Element.Points.IsEmpty() ? Sum : Sum / Element.Points.Num();
    }
}

void FTownAgeMapEdMode::Exit()
{
    bTrackingElement = false;
    MoveTransaction.Reset();
    CancelDraft();
    FEdMode::Exit();
}

void FTownAgeMapEdMode::CancelDraft() { Draft.Reset(); bHasHover = false; }

bool FTownAgeMapEdMode::GroundPoint(const FVector& Origin, const FVector& Direction, FVector& LocalPoint) const
{
    const auto* Layout = FTownAgeMapEditorModule::Get().GetLayout();
    if (!Layout || !Layout->GetWorld() || Layout->GetWorld()->WorldType != EWorldType::Editor) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(TownAgeMapPaint), true);
    Query.AddIgnoredActor(Layout);
    FHitResult Hit;
    FVector Point;
    if (Layout->GetWorld()->LineTraceSingleByChannel(Hit, Origin, Origin + Direction * 10000000.0, ECC_Visibility, Query))
        Point = Hit.ImpactPoint;
    else
    {
        if (FMath::Abs(Direction.Z) < UE_DOUBLE_SMALL_NUMBER) return false;
        const double Distance = (Layout->GetActorLocation().Z - Origin.Z) / Direction.Z;
        if (Distance < 0 || Distance > 10000000.0) return false;
        Point = Origin + Direction * Distance;
    }
    LocalPoint = Layout->GetActorTransform().InverseTransformPosition(Point);
    LocalPoint.X = FMath::GridSnap(LocalPoint.X, 100.0);
    LocalPoint.Y = FMath::GridSnap(LocalPoint.Y, 100.0);
    return !LocalPoint.ContainsNaN();
}

bool FTownAgeMapEdMode::MouseMove(FEditorViewportClient* Client, FViewport* Viewport, int32 X, int32 Y)
{
    if (!FTownAgeMapEditorModule::Get().IsDrawing()) return false;
    const FViewportCursorLocation Cursor = Client->GetCursorWorldLocationFromMousePos();
    bHasHover = GroundPoint(Cursor.GetOrigin(), Cursor.GetDirection(), Hover);
    Client->Invalidate(false, false);
    return false;
}

bool FTownAgeMapEdMode::HandleClick(FEditorViewportClient* Client, HHitProxy* Hit, const FViewportClick& Click)
{
    auto& Tool = FTownAgeMapEditorModule::Get();
    ATownAgeMapLayout* Layout = Tool.GetLayout();
    if (!Layout || Click.GetKey() != EKeys::LeftMouseButton || Click.IsAltDown() || Click.IsControlDown()) return false;
    if (!Tool.IsDrawing())
    {
        if (Hit && Hit->IsA(HInstancedStaticMeshInstance::StaticGetType()))
        {
            const auto* Instance = static_cast<HInstancedStaticMeshInstance*>(Hit);
            const FGuid Id = Layout->GetElementIdForInstance(Instance->Component.Get(), Instance->InstanceIndex);
            if (Id.IsValid()) { Tool.SelectElement(Id); return true; }
        }
        return false;
    }
    FVector Point;
    if (!GroundPoint(Click.GetOrigin(), Click.GetDirection(), Point)) return true;
    if (!Draft.IsEmpty() && FVector::DistSquared2D(Point, Draft.Last()) < 2500.f)
    { Tool.SetStatus(TEXT("Choose a different point (minimum 50 cm).")); return true; }
    if (Draft.Num() >= 512) { Tool.SetStatus(TEXT("A road can contain at most 512 points. Press Enter to finish.")); return true; }
    Draft.Add(Point);
    if (Tool.GetToolKind() != ETownAgeMapElementKind::Road && Draft.Num() == 2) CommitDraft();
    else Tool.SetStatus(FString::Printf(TEXT("%d point(s). Road: Enter finishes; Backspace removes a point; Esc cancels."), Draft.Num()));
    Client->Invalidate();
    return true;
}

bool FTownAgeMapEdMode::CommitDraft()
{
    auto& Tool = FTownAgeMapEditorModule::Get();
    ATownAgeMapLayout* Layout = Tool.GetLayout();
    if (!Layout || Draft.Num() < 2) { Tool.SetStatus(TEXT("Choose at least two points first.")); return false; }
    FTownAgeMapElement Element;
    Element.Id = FGuid::NewGuid();
    Element.Kind = Tool.GetToolKind();
    Element.TypeId = Tool.GetTypeId();
    Element.Points = Draft;
    Element.WidthCm = Tool.GetRoadWidth();
    Element.HeightCm = Tool.GetBuildingHeight();
    Element.Label = FString::Printf(TEXT("%s %d"), *Element.TypeId.ToString(), Layout->Elements.Num() + 1);
    TArray<FTownAgeMapElement> Proposed = Layout->Elements;
    Proposed.Add(Element);
    FString Error;
    if (!ATownAgeMapLayout::ValidateData(Layout->Types, Proposed, Error))
    {
        Tool.SetStatus(Error);
        if (Element.Kind != ETownAgeMapElementKind::Road) Draft.SetNum(1);
        return false;
    }
    const FScopedTransaction Transaction(NSLOCTEXT("TownAgeMap", "AddElement", "Add map layout element"));
    Layout->Modify();
    Layout->Elements = MoveTemp(Proposed);
    Layout->RebuildLayout();
    Layout->MarkPackageDirty();
    CancelDraft();
    Tool.SelectElement(Element.Id);
    Tool.ActivateTool();
    Tool.SetStatus(TEXT("Placement added. Continue drawing, or choose Select / Move."));
    return true;
}

bool FTownAgeMapEdMode::InputKey(FEditorViewportClient* Client, FViewport* Viewport, FKey Key, EInputEvent Event)
{
    if (Event != IE_Pressed) return false;
    auto& Tool = FTownAgeMapEditorModule::Get();
    if (!Tool.IsDrawing() && Tool.GetSelectedElement() && Key == EKeys::LeftMouseButton &&
        !Viewport->KeyState(EKeys::LeftAlt) && !Viewport->KeyState(EKeys::RightAlt))
    {
        HHitProxy* PressHit = Viewport->GetHitProxy(Viewport->GetMouseX(), Viewport->GetMouseY());
        if (FParse::Param(FCommandLine::Get(), TEXT("MapLayoutDebugInput")))
            UE_LOG(LogTownAgeMapInput, Display, TEXT("Press mouse=%d,%d proxy=%s axis=%d"), Viewport->GetMouseX(), Viewport->GetMouseY(), PressHit ? PressHit->GetType()->GetName() : TEXT("none"), int32(Client->GetCurrentWidgetAxis()));
        // Seed the legacy axis on press too, so a quick drag need not wait for an idle hover tick.
        if (PressHit && PressHit->IsA(HWidgetAxis::StaticGetType()))
            Client->SetCurrentWidgetAxis(static_cast<HWidgetAxis*>(PressHit)->Axis);
    }
    if (Key == EKeys::Escape) { CancelDraft(); Tool.SetStatus(TEXT("Draft cancelled; existing placements are unchanged.")); Client->Invalidate(); return true; }
    if (Tool.IsDrawing() && Key == EKeys::BackSpace && !Draft.IsEmpty()) { Draft.Pop(); Client->Invalidate(); return true; }
    if (Tool.IsDrawing() && Key == EKeys::Enter) return CommitDraft();
    if (!Tool.IsDrawing() && Key == EKeys::Delete && Tool.GetSelectedElement()) { Tool.DeleteSelectedElement(); return true; }
    return false;
}

void FTownAgeMapEdMode::Render(const FSceneView* View, FViewport* Viewport, FPrimitiveDrawInterface* PDI)
{
    FEdMode::Render(View, Viewport, PDI);
    const auto& Tool = FTownAgeMapEditorModule::Get();
    const ATownAgeMapLayout* Layout = Tool.GetLayout();
    if (!Layout) return;
    const FTransform Transform = Layout->GetActorTransform();
    auto Line = [&](FVector A, FVector B, FLinearColor Color, float Thickness)
    { PDI->DrawLine(Transform.TransformPosition(A) + FVector(0,0,12), Transform.TransformPosition(B) + FVector(0,0,12), Color, SDPG_Foreground, Thickness, 0.f, true); };
    auto Shape = [&](const TArray<FVector>& Points, ETownAgeMapElementKind Kind, FLinearColor Color, float Thickness)
    {
        if (Points.Num() < 2) return;
        if (Kind == ETownAgeMapElementKind::Road)
            for (int32 I = 1; I < Points.Num(); ++I) Line(Points[I-1], Points[I], Color, Thickness);
        else
        {
            const FVector A = Points[0], C = Points[1];
            const FVector B(C.X, A.Y, A.Z), D(A.X, C.Y, C.Z);
            Line(A,B,Color,Thickness); Line(B,C,Color,Thickness); Line(C,D,Color,Thickness); Line(D,A,Color,Thickness);
        }
    };
    int32 Segments = 0;
    for (const auto& Element : Layout->Elements)
    {
        if ((Segments += Element.Points.Num()) > 10000) break;
        const bool bSelected = Element.Id == Tool.GetSelectedElementId();
        const auto* Type = Layout->FindType(Element.TypeId);
        Shape(Element.Points, Element.Kind, bSelected ? FLinearColor::White : (Type ? Type->PreviewColor : FLinearColor::Red), bSelected ? 3.f : 1.f);
    }
    if (Tool.IsDrawing() && !Draft.IsEmpty())
    {
        TArray<FVector> Preview = Draft;
        if (bHasHover) Preview.Add(Hover);
        Shape(Preview, Tool.GetToolKind(), FLinearColor(1,.8f,.15f), 3.f);
        for (const FVector& P : Draft) PDI->DrawPoint(Transform.TransformPosition(P) + FVector(0,0,14), FLinearColor::Yellow, 10.f, SDPG_Foreground);
    }
}

bool FTownAgeMapEdMode::UsesTransformWidget() const { return ShouldDrawWidget(); }
bool FTownAgeMapEdMode::UsesTransformWidget(UE::Widget::EWidgetMode Mode) const { return Mode == UE::Widget::WM_Translate && ShouldDrawWidget(); }
bool FTownAgeMapEdMode::ShouldDrawWidget() const
{ const auto& Tool = FTownAgeMapEditorModule::Get(); return !Tool.IsDrawing() && Tool.GetSelectedElement(); }
FVector FTownAgeMapEdMode::GetWidgetLocation() const
{
    const auto& Tool = FTownAgeMapEditorModule::Get();
    const auto* Element = Tool.GetSelectedElement();
    return Element && Tool.GetLayout() ? Tool.GetLayout()->GetActorTransform().TransformPosition(ElementCenter(*Element)) : FVector::ZeroVector;
}
EAxisList::Type FTownAgeMapEdMode::GetWidgetAxisToDraw(UE::Widget::EWidgetMode Mode) const
{ return Mode == UE::Widget::WM_Translate ? EAxisList::XYZ : EAxisList::None; }

bool FTownAgeMapEdMode::StartTracking(FEditorViewportClient* Client, FViewport* Viewport)
{
    if (FParse::Param(FCommandLine::Get(), TEXT("MapLayoutDebugInput")))
        UE_LOG(LogTownAgeMapInput, Display, TEXT("Track axis=%d widget=%d"), int32(Client->GetCurrentWidgetAxis()), int32(ShouldDrawWidget()));
    if (!ShouldDrawWidget() || Client->GetCurrentWidgetAxis() == EAxisList::None ||
        Viewport->KeyState(EKeys::LeftAlt) || Viewport->KeyState(EKeys::RightAlt)) return false;
    bTrackingElement = true;
    return true;
}
bool FTownAgeMapEdMode::EndTracking(FEditorViewportClient* Client, FViewport* Viewport)
{
    const bool bHandled = bTrackingElement;
    const bool bMoved = MoveTransaction.IsValid();
    bTrackingElement = false;
    MoveTransaction.Reset();
    if (bMoved) FTownAgeMapEditorModule::Get().NotifyChanged();
    return bHandled;
}
bool FTownAgeMapEdMode::InputDelta(FEditorViewportClient* Client, FViewport* Viewport, FVector& Drag, FRotator& Rot, FVector& Scale)
{
    if (FParse::Param(FCommandLine::Get(), TEXT("MapLayoutDebugInput")))
        UE_LOG(LogTownAgeMapInput, Display, TEXT("Delta axis=%d tracking=%d drag=%s"), int32(Client->GetCurrentWidgetAxis()), int32(bTrackingElement), *Drag.ToString());
    if (!bTrackingElement || !ShouldDrawWidget() || Client->GetCurrentWidgetAxis() == EAxisList::None || Drag.IsNearlyZero()) return false;
    auto& Tool = FTownAgeMapEditorModule::Get();
    ATownAgeMapLayout* Layout = Tool.GetLayout();
    if (!Layout) return false;
    TArray<FTownAgeMapElement> Proposed = Layout->Elements;
    for (auto& Element : Proposed)
    {
        if (Element.Id != Tool.GetSelectedElementId()) continue;
        const FVector Delta = Layout->GetActorTransform().InverseTransformVector(Drag);
        for (FVector& P : Element.Points) P += Delta;
        FString Error;
        if (!ATownAgeMapLayout::ValidateData(Layout->Types, Proposed, Error))
        { Tool.SetStatus(Error); return true; } // Consume the drag without moving unrelated actors.
        if (!MoveTransaction)
        {
            MoveTransaction = MakeUnique<FScopedTransaction>(NSLOCTEXT("TownAgeMap", "MoveElement", "Move map layout element"));
            Layout->Modify();
        }
        Layout->Elements = MoveTemp(Proposed);
        Layout->RebuildLayout();
        Layout->MarkPackageDirty();
        return true;
    }
    return false;
}
