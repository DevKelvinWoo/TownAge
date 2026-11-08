#include "TownAgeMapEditorLibrary.h"
#include "TownAgeMapLayout.h"
#include "TownAgeMapEditorModule.h"
#include "Editor.h"
#include "Engine/World.h"
#include "ScopedTransaction.h"
#include "TownAgeMapEdMode.h"
#include "EditorModeManager.h"
#include "LevelEditorViewport.h"

namespace
{
    bool IsEditable(ATownAgeMapLayout* Layout)
    { return IsValid(Layout) && GEditor && !GEditor->PlayWorld && Layout->GetWorld() == GEditor->GetEditorWorldContext().World(); }
}

bool UTownAgeMapEditorLibrary::ImportJson(ATownAgeMapLayout* Layout, const FString& Json, FString& Error)
{
    if (!IsEditable(Layout)) { Error = TEXT("Import requires an editor-world layout with Play stopped."); return false; }
    FScopedTransaction Transaction(NSLOCTEXT("TownAgeMap", "ScriptImport", "Import map layout data"));
    Layout->Modify();
    if (!Layout->ImportLayoutJson(Json, Error)) { Transaction.Cancel(); return false; }
    Layout->MarkPackageDirty();
    FTownAgeMapEditorModule::Get().NotifyChanged();
    return true;
}

FString UTownAgeMapEditorLibrary::ExportJson(ATownAgeMapLayout* Layout)
{ return IsEditable(Layout) ? Layout->ExportLayoutJson() : FString(); }
int32 UTownAgeMapEditorLibrary::GetGeneratedInstanceCount(ATownAgeMapLayout* Layout)
{ return IsValid(Layout) ? Layout->GetGeneratedInstanceCount() : 0; }
void UTownAgeMapEditorLibrary::UseLayout(ATownAgeMapLayout* Layout)
{
    if (!IsEditable(Layout) || IsRunningCommandlet()) return;
    GEditor->SelectNone(false, true); GEditor->SelectActor(Layout, true, true);
    FTownAgeMapEditorModule::Get().UseSelectedLayout();
}

bool UTownAgeMapEditorLibrary::TranslateElement(ATownAgeMapLayout* Layout, FGuid ElementId, FVector WorldDelta)
{
    if (!IsEditable(Layout) || IsRunningCommandlet() || WorldDelta.ContainsNaN() || WorldDelta.IsNearlyZero()) return false;
    if (!Layout->Elements.ContainsByPredicate([&](const auto& Element) { return Element.Id == ElementId; })) return false;
    TArray<FTownAgeMapElement> Proposed = Layout->Elements;
    for (auto& Element : Proposed)
        if (Element.Id == ElementId)
            for (FVector& Point : Element.Points) Point += Layout->GetActorTransform().InverseTransformVector(WorldDelta);
    FString Error;
    if (!ATownAgeMapLayout::ValidateData(Layout->Types, Proposed, Error)) return false;
    UseLayout(Layout);
    FTownAgeMapEditorModule::Get().SelectElement(ElementId);
    auto* Mode = static_cast<FTownAgeMapEdMode*>(GLevelEditorModeTools().GetActiveMode(FTownAgeMapEditorModule::ModeId));
    FLevelEditorViewportClient* Client = nullptr;
    for (auto* Candidate : GEditor->GetLevelViewportClients())
        if (Candidate && Candidate->GetWorld() == Layout->GetWorld()) { Client = Candidate; break; }
    if (!Mode || !Client || !Client->Viewport) return false;
    const EAxisList::Type PreviousAxis = Client->GetCurrentWidgetAxis();
    Client->SetCurrentWidgetAxis(EAxisList::X);
    FRotator Rotation = FRotator::ZeroRotator;
    FVector Scale = FVector::ZeroVector;
    const bool bTracking = Mode->StartTracking(Client, Client->Viewport);
    const bool bMoved = bTracking && Mode->InputDelta(Client, Client->Viewport, WorldDelta, Rotation, Scale);
    if (bTracking) Mode->EndTracking(Client, Client->Viewport);
    Client->SetCurrentWidgetAxis(PreviousAxis);
    return bMoved;
}
