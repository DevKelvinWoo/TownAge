#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/Views/SListView.h"
#include "Widgets/Input/SComboBox.h"

class FTownAgeMapEditorModule;

class STownAgeMapLayoutPanel : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(STownAgeMapLayoutPanel) {}
    SLATE_END_ARGS()
    void Construct(const FArguments& Args, FTownAgeMapEditorModule* InOwner);
    virtual ~STownAgeMapLayoutPanel() override;

private:
    struct FElementRow
    {
        FGuid Id;
        FString Summary;
    };
    void Refresh();
    FText TypeText(TSharedPtr<FName> Item) const;
    TSharedRef<ITableRow> MakeElementRow(TSharedPtr<FElementRow> Item, const TSharedRef<STableViewBase>& Table);
    void ElementSelected(TSharedPtr<FElementRow> Item, ESelectInfo::Type SelectInfo);
    bool HasLayout() const;
    bool HasSelection() const;

    FTownAgeMapEditorModule* Owner = nullptr;
    FDelegateHandle ChangedHandle;
    bool bRefreshing = false;
    TArray<TSharedPtr<FName>> TypeItems;
    TArray<TSharedPtr<FElementRow>> ElementItems;
    TSharedPtr<SComboBox<TSharedPtr<FName>>> TypeCombo;
    TSharedPtr<SListView<TSharedPtr<FElementRow>>> ElementList;
    FString SelectedLabel;
    FString SelectedType;
    float SelectedWidth = 400.f;
    float SelectedHeight = 300.f;
};
