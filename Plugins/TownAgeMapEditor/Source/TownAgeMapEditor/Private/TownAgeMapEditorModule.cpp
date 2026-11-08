#include "TownAgeMapEditorModule.h"
#include "TownAgeMapEdMode.h"
#include "STownAgeMapLayoutPanel.h"
#include "Editor.h"
#include "EditorModeManager.h"
#include "EditorModeRegistry.h"
#include "EditorViewportClient.h"
#include "LevelEditorViewport.h"
#include "Engine/Selection.h"
#include "Engine/World.h"
#include "ScopedTransaction.h"
#include "ToolMenus.h"
#include "DesktopPlatformModule.h"
#include "IDesktopPlatform.h"
#include "Framework/Application/SlateApplication.h"
#include "Framework/Docking/TabManager.h"
#include "Widgets/Docking/SDockTab.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "UnrealWidget.h"

IMPLEMENT_MODULE(FTownAgeMapEditorModule, TownAgeMapEditor)
const FName FTownAgeMapEditorModule::ModeId(TEXT("EM_TownAgeMapLayout"));
static const FName LayoutTabId(TEXT("TownAge.MapLayout"));

FTownAgeMapEditorModule& FTownAgeMapEditorModule::Get()
{ return FModuleManager::LoadModuleChecked<FTownAgeMapEditorModule>(TEXT("TownAgeMapEditor")); }

void FTownAgeMapEditorModule::StartupModule()
{
    // Batch imports/tests may load this editor module without a global mode manager.
    if (IsRunningCommandlet()) return;
    bUIRegistered = true;
    FEditorModeRegistry::Get().RegisterMode<FTownAgeMapEdMode>(ModeId, NSLOCTEXT("TownAgeMap", "Mode", "TownAge Map Layout"));
    FGlobalTabmanager::Get()->RegisterNomadTabSpawner(LayoutTabId, FOnSpawnTab::CreateRaw(this, &FTownAgeMapEditorModule::SpawnTab))
        .SetDisplayName(NSLOCTEXT("TownAgeMap", "Tab", "TownAge Map Layout"))
        .SetMenuType(ETabSpawnerMenuType::Hidden);
    FTabManager::RegisterDefaultTabWindowSize(LayoutTabId, FVector2D(420, 740));
    UToolMenus::RegisterStartupCallback(FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FTownAgeMapEditorModule::RegisterMenus));
    if (GEditor) GEditor->RegisterForUndo(this);
    MapOpenedHandle = FEditorDelegates::OnMapOpened.AddLambda([this](const FString&, bool)
    {
        DeactivateTool(); Layout.Reset(); SelectedId.Invalidate();
        SetStatus(TEXT("Map changed. Create a layout or use a selected layout actor."));
    });
    BeginPieHandle = FEditorDelegates::BeginPIE.AddLambda([this](bool)
    { DeactivateTool(); SetStatus(TEXT("Layout authoring is disabled during Play. Stop Play to edit.")); });
}

void FTownAgeMapEditorModule::ShutdownModule()
{
    if (!bUIRegistered) { OnChanged.Clear(); return; }
    FEditorDelegates::OnMapOpened.Remove(MapOpenedHandle);
    FEditorDelegates::BeginPIE.Remove(BeginPieHandle);
    if (TSharedPtr<SDockTab> Tab = FGlobalTabmanager::Get()->FindExistingLiveTab(LayoutTabId)) Tab->RequestCloseTab();
    if (GEditor) { DeactivateTool(); GEditor->UnregisterForUndo(this); }
    OnChanged.Clear();
    UToolMenus::UnRegisterStartupCallback(this);
    UToolMenus::UnregisterOwner(this);
    FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(LayoutTabId);
    FTabManager::UnregisterDefaultTabWindowSize(LayoutTabId);
    FEditorModeRegistry::Get().UnregisterMode(ModeId);
}

void FTownAgeMapEditorModule::RegisterMenus()
{
    FToolMenuOwnerScoped Owner(this);
    UToolMenu* Menu = UToolMenus::Get()->ExtendMenu(TEXT("LevelEditor.MainMenu.Tools"));
    Menu->FindOrAddSection(TEXT("TownAge"), NSLOCTEXT("TownAgeMap", "Section", "TownAge"))
        .AddMenuEntry(TEXT("OpenTownAgeMapLayout"), NSLOCTEXT("TownAgeMap", "Open", "TownAge Map Layout"),
            NSLOCTEXT("TownAgeMap", "Tooltip", "Draw data-driven roads, fields and building footprints."), FSlateIcon(),
            FUIAction(FExecuteAction::CreateLambda([]() { FGlobalTabmanager::Get()->TryInvokeTab(LayoutTabId); })));
}

TSharedRef<SDockTab> FTownAgeMapEditorModule::SpawnTab(const FSpawnTabArgs& Args)
{
    TSharedRef<SDockTab> Tab = SNew(SDockTab).TabRole(ETabRole::NomadTab)[ SNew(STownAgeMapLayoutPanel, this) ];
    Tab->SetOnTabClosed(SDockTab::FOnTabClosedCallback::CreateLambda([this](TSharedRef<SDockTab>) { DeactivateTool(); }));
    return Tab;
}

ATownAgeMapLayout* FTownAgeMapEditorModule::GetLayout() const
{
    ATownAgeMapLayout* Plan = Layout.Get();
    return Plan && GEditor && !GEditor->PlayWorld && Plan->GetWorld() == GEditor->GetEditorWorldContext().World() ? Plan : nullptr;
}

void FTownAgeMapEditorModule::UseSelectedLayout()
{
    if (!GEditor || GEditor->PlayWorld) { SetStatus(TEXT("Stop Play before editing a layout.")); return; }
    for (FSelectionIterator It(*GEditor->GetSelectedActors()); It; ++It)
    {
        if (auto* Plan = Cast<ATownAgeMapLayout>(*It))
        {
            DeactivateTool(); Layout = Plan; SelectedId.Invalidate(); SetToolKind(ToolKind);
            SetStatus(TEXT("Layout selected. Choose a kind/type, then Start Drawing.")); return;
        }
    }
    SetStatus(TEXT("Select a TownAgeMapLayout actor in the Outliner first."));
}

void FTownAgeMapEditorModule::CreateLayout()
{
    if (!GEditor || GEditor->PlayWorld) { SetStatus(TEXT("Stop Play before creating a layout.")); return; }
    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World || !World->GetCurrentLevel()) return;
    const FScopedTransaction Transaction(NSLOCTEXT("TownAgeMap", "Create", "Create map layout"));
    auto* Plan = Cast<ATownAgeMapLayout>(GEditor->AddActor(World->GetCurrentLevel(), ATownAgeMapLayout::StaticClass(), FTransform::Identity));
    if (!Plan) { SetStatus(TEXT("Could not create a layout in the current level.")); return; }
    DeactivateTool();
    Plan->SetActorLabel(TEXT("TownAge Layout"));
    Layout = Plan; SelectedId.Invalidate(); SetToolKind(ToolKind);
    ShowLayoutDetails();
    SetStatus(TEXT("Layout created. Existing map actors are unchanged. Choose a type and Start Drawing."));
}

void FTownAgeMapEditorModule::SetToolKind(ETownAgeMapElementKind Kind)
{
    if (bUIRegistered)
        if (auto* Mode = static_cast<FTownAgeMapEdMode*>(GLevelEditorModeTools().GetActiveMode(ModeId))) Mode->CancelDraft();
    ToolKind = Kind;
    if (const auto* Plan = GetLayout())
    {
        const auto* Type = Plan->FindType(ActiveTypeId);
        if (!Type || Type->Kind != Kind)
        {
            ActiveTypeId = NAME_None;
            for (const auto& Candidate : Plan->Types)
                if (Candidate.Kind == Kind) { ActiveTypeId = Candidate.TypeId; BuildingHeight = Candidate.DefaultHeightCm; break; }
        }
    }
    NotifyChanged();
}

void FTownAgeMapEditorModule::SetTypeId(FName TypeId)
{
    if (const auto* Plan = GetLayout())
        if (const auto* Type = Plan->FindType(TypeId); Type && Type->Kind == ToolKind)
        { ActiveTypeId = TypeId; BuildingHeight = Type->DefaultHeightCm; NotifyChanged(); }
}

void FTownAgeMapEditorModule::ActivateTool()
{
    if (!bUIRegistered) return;
    const auto* Plan = GetLayout();
    if (!Plan || !Plan->FindType(ActiveTypeId)) { SetStatus(TEXT("Select a layout and a valid catalog type first.")); return; }
    GLevelEditorModeTools().ActivateMode(ModeId);
    if (auto* Mode = static_cast<FTownAgeMapEdMode*>(GLevelEditorModeTools().GetActiveMode(ModeId))) Mode->CancelDraft();
    bDrawing = true;
    SetStatus(ToolKind == ETownAgeMapElementKind::Road ? TEXT("Click road points on the ground. Enter finishes; Esc cancels.") : TEXT("Click two opposite rectangle corners on the ground. Esc cancels."));
}

void FTownAgeMapEditorModule::SelectMode()
{
    if (!bUIRegistered) return;
    if (!GetLayout()) return;
    bDrawing = false;
    GLevelEditorModeTools().ActivateMode(ModeId);
    GLevelEditorModeTools().SetWidgetMode(UE::Widget::WM_Translate);
    if (auto* Mode = static_cast<FTownAgeMapEdMode*>(GLevelEditorModeTools().GetActiveMode(ModeId))) Mode->CancelDraft();
    SetStatus(TEXT("Click a generated piece or select a list row. Drag the move gizmo; Ctrl+Z undoes."));
}

void FTownAgeMapEditorModule::DeactivateTool()
{
    bDrawing = false;
    if (bUIRegistered) GLevelEditorModeTools().DeactivateMode(ModeId);
}

const FTownAgeMapElement* FTownAgeMapEditorModule::GetSelectedElement() const
{
    if (const auto* Plan = GetLayout()) return Plan->Elements.FindByPredicate([this](const auto& E) { return E.Id == SelectedId; });
    return nullptr;
}

void FTownAgeMapEditorModule::SelectElement(FGuid Id)
{
    SelectedId = Id;
    if (!GetSelectedElement()) SelectedId.Invalidate();
    ShowLayoutDetails();
    SelectMode();
    NotifyChanged();
}

void FTownAgeMapEditorModule::DeleteSelectedElement()
{
    auto* Plan = GetLayout();
    if (!Plan || !GetSelectedElement()) return;
    const FScopedTransaction Transaction(NSLOCTEXT("TownAgeMap", "Delete", "Delete map layout element"));
    Plan->Modify();
    Plan->Elements.RemoveAll([this](const auto& E) { return E.Id == SelectedId; });
    SelectedId.Invalidate(); Plan->RebuildLayout(); Plan->MarkPackageDirty();
    SetStatus(TEXT("Placement deleted. Ctrl+Z restores it; unrelated map actors are untouched."));
}

void FTownAgeMapEditorModule::FocusSelectedElement()
{
    const auto* Plan = GetLayout();
    const auto* Element = GetSelectedElement();
    if (!Plan || !Element) return;
    FBox Bounds(ForceInit);
    for (const FVector& P : Element->Points) Bounds += Plan->GetActorTransform().TransformPosition(P);
    Bounds = Bounds.ExpandBy(FMath::Max(200.f, Element->WidthCm * .5f));
    for (FEditorViewportClient* Client : GEditor->GetLevelViewportClients()) if (Client) Client->FocusViewportOnBox(Bounds, true);
}

void FTownAgeMapEditorModule::UpdateSelectedElement(const FString& Label, FName TypeId, float Width, float Height)
{
    auto* Plan = GetLayout();
    if (!Plan || !GetSelectedElement()) return;
    TArray<FTownAgeMapElement> Proposed = Plan->Elements;
    for (auto& Element : Proposed)
        if (Element.Id == SelectedId) { Element.Label = Label; Element.TypeId = TypeId; Element.WidthCm = Width; Element.HeightCm = Height; break; }
    FString Error;
    if (!ATownAgeMapLayout::ValidateData(Plan->Types, Proposed, Error)) { SetStatus(Error); return; }
    const FScopedTransaction Transaction(NSLOCTEXT("TownAgeMap", "Edit", "Edit map layout element"));
    Plan->Modify(); Plan->Elements = MoveTemp(Proposed); Plan->RebuildLayout(); Plan->MarkPackageDirty();
    SetStatus(TEXT("Placement updated. Catalog mesh/material changes apply to every placement of that type."));
}

void FTownAgeMapEditorModule::Rebuild()
{
    auto* Plan = GetLayout();
    if (!Plan) return;
    FString Error;
    if (!Plan->ValidateLayout(Error)) { SetStatus(Error); return; }
    Plan->RebuildLayout();
    SetStatus(FString::Printf(TEXT("Built %d placements into %d mesh instances."), Plan->Elements.Num(), Plan->GetGeneratedInstanceCount()));
}

void FTownAgeMapEditorModule::ShowLayoutDetails()
{
    if (auto* Plan = GetLayout())
    { GEditor->SelectNone(false, true); GEditor->SelectActor(Plan, true, true); GEditor->NoteSelectionChange(); }
}

void FTownAgeMapEditorModule::ExportJson()
{
    const auto* Plan = GetLayout();
    if (!Plan) return;
    FString Error;
    if (!Plan->ValidateLayout(Error)) { SetStatus(Error); return; }
    IDesktopPlatform* Desktop = FDesktopPlatformModule::Get();
    if (!Desktop) { SetStatus(TEXT("Native file dialogs are unavailable.")); return; }
    TArray<FString> Files;
    const FString Directory = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("Tools/MapLayout/Layouts"));
    IFileManager::Get().MakeDirectory(*Directory, true);
    if (!Desktop->SaveFileDialog(FSlateApplication::Get().FindBestParentWindowHandleForDialogs(nullptr), TEXT("Export TownAge Layout"), Directory,
        TEXT("VillageLayout.json"), TEXT("Layout JSON (*.json)|*.json"), EFileDialogFlags::None, Files) || Files.IsEmpty()) return;
    const FString Json = Plan->ExportLayoutJson();
    SetStatus(!Json.IsEmpty() && FFileHelper::SaveStringToFile(Json, *Files[0], FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)
        ? TEXT("Layout exported. JSON contains data and asset paths, not model files.") : TEXT("Could not write the layout JSON."));
}

void FTownAgeMapEditorModule::ImportJson()
{
    auto* Plan = GetLayout();
    if (!Plan) return;
    IDesktopPlatform* Desktop = FDesktopPlatformModule::Get();
    if (!Desktop) { SetStatus(TEXT("Native file dialogs are unavailable.")); return; }
    TArray<FString> Files;
    if (!Desktop->OpenFileDialog(FSlateApplication::Get().FindBestParentWindowHandleForDialogs(nullptr), TEXT("Import TownAge Layout"),
        FPaths::ProjectDir(), TEXT(""), TEXT("Layout JSON (*.json)|*.json"), EFileDialogFlags::None, Files) || Files.IsEmpty()) return;
    if (IFileManager::Get().FileSize(*Files[0]) > 8 * 1024 * 1024) { SetStatus(TEXT("Layout files must be at most 8 MiB.")); return; }
    FString Json, Error;
    if (!FFileHelper::LoadFileToString(Json, *Files[0])) { SetStatus(TEXT("Could not read the layout JSON.")); return; }
    FScopedTransaction Transaction(NSLOCTEXT("TownAgeMap", "Import", "Import map layout data"));
    Plan->Modify();
    if (!Plan->ImportLayoutJson(Json, Error)) { Transaction.Cancel(); SetStatus(Error); return; }
    Plan->MarkPackageDirty(); SelectedId.Invalidate(); SetToolKind(ToolKind);
    SetStatus(TEXT("Layout imported and rebuilt. Ctrl+Z restores the previous layout."));
}

void FTownAgeMapEditorModule::SetStatus(const FString& Value) { Status = Value; NotifyChanged(); }
void FTownAgeMapEditorModule::NotifyChanged() { OnChanged.Broadcast(); if (GEditor && !IsRunningCommandlet()) GEditor->RedrawAllViewports(); }
void FTownAgeMapEditorModule::PostUndo(bool bSuccess) { if (!GetSelectedElement()) SelectedId.Invalidate(); NotifyChanged(); }
void FTownAgeMapEditorModule::PostRedo(bool bSuccess) { PostUndo(bSuccess); }
