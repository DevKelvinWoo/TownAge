#pragma once
#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"
#include "EditorUndoClient.h"
#include "TownAgeMapLayout.h"

class FTownAgeMapEditorModule : public IModuleInterface, public FEditorUndoClient
{
public:
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;
    virtual void PostUndo(bool bSuccess) override;
    virtual void PostRedo(bool bSuccess) override;
    static FTownAgeMapEditorModule& Get();
    ATownAgeMapLayout* GetLayout() const;
    void UseSelectedLayout();
    void CreateLayout();
    void SetToolKind(ETownAgeMapElementKind Kind);
    ETownAgeMapElementKind GetToolKind() const { return ToolKind; }
    FName GetTypeId() const { return ActiveTypeId; }
    void SetTypeId(FName TypeId);
    float GetRoadWidth() const { return RoadWidth; }
    void SetRoadWidth(float Value) { RoadWidth = FMath::Clamp(Value, 50.f, 3000.f); }
    float GetBuildingHeight() const { return BuildingHeight; }
    void SetBuildingHeight(float Value) { BuildingHeight = FMath::Clamp(Value, 50.f, 10000.f); }
    void ActivateTool();
    void SelectMode();
    void DeactivateTool();
    bool IsDrawing() const { return bDrawing; }
    FGuid GetSelectedElementId() const { return SelectedId; }
    const FTownAgeMapElement* GetSelectedElement() const;
    void SelectElement(FGuid Id);
    void DeleteSelectedElement();
    void FocusSelectedElement();
    void UpdateSelectedElement(const FString& Label, FName TypeId, float Width, float Height);
    void Rebuild();
    void ExportJson();
    void ImportJson();
    void ShowLayoutDetails();
    FString GetStatus() const { return Status; }
    void SetStatus(const FString& Value);
    void NotifyChanged();
    FSimpleMulticastDelegate OnChanged;
    static const FName ModeId;
private:
    void RegisterMenus();
    TSharedRef<class SDockTab> SpawnTab(const class FSpawnTabArgs& Args);
    TWeakObjectPtr<ATownAgeMapLayout> Layout;
    ETownAgeMapElementKind ToolKind = ETownAgeMapElementKind::Road;
    FName ActiveTypeId = TEXT("road.path");
    float RoadWidth = 400.f;
    float BuildingHeight = 300.f;
    FGuid SelectedId;
    bool bDrawing = false;
    bool bUIRegistered = false;
    FString Status = TEXT("Create a layout or use a selected TownAgeMapLayout actor.");
    FDelegateHandle MapOpenedHandle;
    FDelegateHandle BeginPieHandle;
};
