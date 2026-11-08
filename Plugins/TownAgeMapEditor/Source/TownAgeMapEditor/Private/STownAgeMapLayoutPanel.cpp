#include "STownAgeMapLayoutPanel.h"
#include "TownAgeMapEditorModule.h"
#include "TownAgeMapLayout.h"
#include "Styling/AppStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SSpinBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/Layout/SUniformGridPanel.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
    const TCHAR* KindName(ETownAgeMapElementKind Kind)
    {
        switch (Kind)
        {
        case ETownAgeMapElementKind::Road: return TEXT("Road");
        case ETownAgeMapElementKind::Field: return TEXT("Field");
        case ETownAgeMapElementKind::Building: return TEXT("Building");
        default: return TEXT("Unknown");
        }
    }
}

void STownAgeMapLayoutPanel::Construct(const FArguments& Args, FTownAgeMapEditorModule* InOwner)
{
    Owner = InOwner;
    auto Button = [](const TCHAR* Label, const TCHAR* Hint, TFunction<FReply()> Action)
    {
        return SNew(SButton)
            .Text(FText::FromString(Label))
            .ToolTipText(FText::FromString(Hint))
            .OnClicked_Lambda([Action = MoveTemp(Action)]() { return Action(); });
    };
    auto ToolButton = [this](ETownAgeMapElementKind Kind)
    {
        return SNew(SCheckBox)
            .Style(FAppStyle::Get(), "ToggleButtonCheckbox")
            .Padding(FMargin(12, 6))
            .IsChecked_Lambda([this, Kind]() { return Owner->GetToolKind() == Kind ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
            .OnCheckStateChanged_Lambda([this, Kind](ECheckBoxState State)
            {
                if (State == ECheckBoxState::Checked) Owner->SetToolKind(Kind);
            })
            [ SNew(STextBlock).Text(FText::FromString(KindName(Kind))) ];
    };

    ChildSlot
    [
        SNew(SBox).MinDesiredWidth(350.f)
        [
            SNew(SScrollBox)
            + SScrollBox::Slot().Padding(12)
            [
                SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [ SNew(STextBlock).Text(FText::FromString(TEXT("Map Layout"))).Font(FAppStyle::GetFontStyle("DetailsView.CategoryFontStyle")) ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [
                    SNew(STextBlock).AutoWrapText(true)
                    .Text(FText::FromString(TEXT("Road: click route points, then Enter to finish.\nField / Building: click two opposite corners.\nEscape cancels the draft. Select / Move enables picking and the move gizmo.")))
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [
                    SNew(STextBlock).AutoWrapText(true).Text_Lambda([this]()
                    {
                        const ATownAgeMapLayout* Layout = Owner->GetLayout();
                        return FText::FromString(Layout ? TEXT("Layout: ") + Layout->GetActorLabel() : TEXT("No active layout"));
                    })
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [
                    SNew(SUniformGridPanel).SlotPadding(FMargin(2))
                    + SUniformGridPanel::Slot(0, 0)
                    [ Button(TEXT("New Layout"), TEXT("Add one layout actor to the current map. Existing map objects are kept."), [this]() { Owner->CreateLayout(); return FReply::Handled(); }) ]
                    + SUniformGridPanel::Slot(1, 0)
                    [ Button(TEXT("Use Selected"), TEXT("Use the selected TownAgeMapLayout actor."), [this]() { Owner->UseSelectedLayout(); return FReply::Handled(); }) ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 2, 0, 8) [ SNew(SSeparator) ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [
                    SNew(SHorizontalBox)
                    + SHorizontalBox::Slot().FillWidth(1).Padding(2) [ ToolButton(ETownAgeMapElementKind::Road) ]
                    + SHorizontalBox::Slot().FillWidth(1).Padding(2) [ ToolButton(ETownAgeMapElementKind::Field) ]
                    + SHorizontalBox::Slot().FillWidth(1).Padding(2) [ ToolButton(ETownAgeMapElementKind::Building) ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4) [ SNew(STextBlock).Text(FText::FromString(TEXT("Type"))) ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [
                    SAssignNew(TypeCombo, SComboBox<TSharedPtr<FName>>)
                    .OptionsSource(&TypeItems)
                    .IsEnabled_Lambda([this]() { return HasLayout(); })
                    .OnGenerateWidget_Lambda([this](TSharedPtr<FName> Item) { return SNew(STextBlock).Text(TypeText(Item)); })
                    .OnSelectionChanged_Lambda([this](TSharedPtr<FName> Item, ESelectInfo::Type)
                    {
                        if (!bRefreshing && Item.IsValid()) Owner->SetTypeId(*Item);
                    })
                    [ SNew(STextBlock).Text_Lambda([this]() { return TypeText(TypeCombo.IsValid() ? TypeCombo->GetSelectedItem() : TSharedPtr<FName>()); }) ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [
                    SNew(SHorizontalBox)
                    + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center) [ SNew(STextBlock).Text(FText::FromString(TEXT("Road width (cm)"))) ]
                    + SHorizontalBox::Slot().AutoWidth()
                    [
                        SNew(SBox).WidthOverride(120)
                        [
                            SNew(SSpinBox<float>).MinValue(50).MaxValue(3000).Delta(50)
                            .Value_Lambda([this]() { return Owner->GetRoadWidth(); })
                            .OnValueChanged_Lambda([this](float Value) { Owner->SetRoadWidth(Value); })
                        ]
                    ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [
                    SNew(SHorizontalBox)
                    + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center) [ SNew(STextBlock).Text(FText::FromString(TEXT("Building height (cm)"))) ]
                    + SHorizontalBox::Slot().AutoWidth()
                    [
                        SNew(SBox).WidthOverride(120)
                        [
                            SNew(SSpinBox<float>).MinValue(50).MaxValue(10000).Delta(50)
                            .Value_Lambda([this]() { return Owner->GetBuildingHeight(); })
                            .OnValueChanged_Lambda([this](float Value) { Owner->SetBuildingHeight(Value); })
                        ]
                    ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [
                    SNew(SUniformGridPanel).SlotPadding(FMargin(2)).IsEnabled_Lambda([this]() { return HasLayout(); })
                    + SUniformGridPanel::Slot(0, 0)
                    [ Button(TEXT("Start Drawing"), TEXT("Use left clicks in the level viewport to draw the chosen kind and type."), [this]() { Owner->ActivateTool(); return FReply::Handled(); }) ]
                    + SUniformGridPanel::Slot(1, 0)
                    [ Button(TEXT("Select / Move"), TEXT("Pick existing generated geometry and move the selected element with the gizmo."), [this]() { Owner->SelectMode(); return FReply::Handled(); }) ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [
                    SNew(SBorder).BorderImage(FAppStyle::GetBrush("ToolPanel.GroupBorder")).Padding(8)
                    [ SNew(STextBlock).AutoWrapText(true).Text_Lambda([this]() { return FText::FromString(Owner->GetStatus()); }) ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 2, 0, 8) [ SNew(SSeparator) ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 6)
                [ SNew(STextBlock).Text_Lambda([this]() { return FText::FromString(FString::Printf(TEXT("Elements (%d)"), ElementItems.Num())); }) ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 6)
                [
                    SNew(SBox).HeightOverride(210)
                    [
                        SAssignNew(ElementList, SListView<TSharedPtr<FElementRow>>)
                        .ListItemsSource(&ElementItems).SelectionMode(ESelectionMode::Single)
                        .OnGenerateRow(this, &STownAgeMapLayoutPanel::MakeElementRow)
                        .OnSelectionChanged(this, &STownAgeMapLayoutPanel::ElementSelected)
                    ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [
                    SNew(SUniformGridPanel).SlotPadding(FMargin(2)).IsEnabled_Lambda([this]() { return HasSelection(); })
                    + SUniformGridPanel::Slot(0, 0)
                    [ Button(TEXT("Focus"), TEXT("Frame the selected element in the level viewport."), [this]() { Owner->FocusSelectedElement(); return FReply::Handled(); }) ]
                    + SUniformGridPanel::Slot(1, 0)
                    [ Button(TEXT("Delete Element"), TEXT("Remove only the selected layout record. Ctrl+Z restores it."), [this]() { Owner->DeleteSelectedElement(); return FReply::Handled(); }) ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [
                    SNew(SVerticalBox).IsEnabled_Lambda([this]() { return HasSelection(); })
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4) [ SNew(STextBlock).Text(FText::FromString(TEXT("Selected element label"))) ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 6)
                    [ SNew(SEditableTextBox).Text_Lambda([this]() { return FText::FromString(SelectedLabel); }).OnTextChanged_Lambda([this](const FText& Value) { SelectedLabel = Value.ToString(); }) ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4) [ SNew(STextBlock).Text(FText::FromString(TEXT("Selected type ID (same kind)"))) ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 6)
                    [ SNew(SEditableTextBox).Text_Lambda([this]() { return FText::FromString(SelectedType); }).OnTextChanged_Lambda([this](const FText& Value) { SelectedType = Value.ToString(); }) ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 6)
                    [
                        SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center) [ SNew(STextBlock).Text(FText::FromString(TEXT("Width / Height (cm)"))) ]
                        + SHorizontalBox::Slot().FillWidth(1).Padding(2)
                        [ SNew(SSpinBox<float>).MinValue(50).MaxValue(3000).Value_Lambda([this]() { return SelectedWidth; }).OnValueChanged_Lambda([this](float V) { SelectedWidth = V; }) ]
                        + SHorizontalBox::Slot().FillWidth(1).Padding(2)
                        [ SNew(SSpinBox<float>).MinValue(50).MaxValue(10000).Value_Lambda([this]() { return SelectedHeight; }).OnValueChanged_Lambda([this](float V) { SelectedHeight = V; }) ]
                    ]
                    + SVerticalBox::Slot().AutoHeight()
                    [ Button(TEXT("Apply Selected Changes"), TEXT("Apply label, compatible type, road width and building height to the selected record."), [this]() { Owner->UpdateSelectedElement(SelectedLabel, FName(*SelectedType), SelectedWidth, SelectedHeight); return FReply::Handled(); }) ]
                ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 2, 0, 8) [ SNew(SSeparator) ]
                + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                [
                    SNew(SUniformGridPanel).SlotPadding(FMargin(2)).IsEnabled_Lambda([this]() { return HasLayout(); })
                    + SUniformGridPanel::Slot(0, 0)
                    [ Button(TEXT("Rebuild Preview"), TEXT("Validate the layout and rebuild its owned placeholder components."), [this]() { Owner->Rebuild(); return FReply::Handled(); }) ]
                    + SUniformGridPanel::Slot(1, 0)
                    [ Button(TEXT("Layout Details"), TEXT("Edit type catalog, replacement meshes/materials and precise region points in Details."), [this]() { Owner->ShowLayoutDetails(); return FReply::Handled(); }) ]
                    + SUniformGridPanel::Slot(0, 1)
                    [ Button(TEXT("Export JSON"), TEXT("Export versioned layout data for reuse."), [this]() { Owner->ExportJson(); return FReply::Handled(); }) ]
                    + SUniformGridPanel::Slot(1, 1)
                    [ Button(TEXT("Import JSON"), TEXT("Validate a versioned layout file before replacing this layout's data."), [this]() { Owner->ImportJson(); return FReply::Handled(); }) ]
                ]
                + SVerticalBox::Slot().AutoHeight()
                [ SNew(STextBlock).AutoWrapText(true).Text(FText::FromString(TEXT("Save the map to keep the layout. Type IDs remain stable when you later assign different meshes or materials in Layout Details. Ctrl+Z / Ctrl+Y use editor undo / redo."))) ]
            ]
        ]
    ];
    ChangedHandle = Owner->OnChanged.AddSP(this, &STownAgeMapLayoutPanel::Refresh);
    Refresh();
}

STownAgeMapLayoutPanel::~STownAgeMapLayoutPanel()
{
    if (Owner && FModuleManager::Get().IsModuleLoaded(TEXT("TownAgeMapEditor"))) Owner->OnChanged.Remove(ChangedHandle);
}

bool STownAgeMapLayoutPanel::HasLayout() const { return Owner && Owner->GetLayout(); }
bool STownAgeMapLayoutPanel::HasSelection() const { return Owner && Owner->GetSelectedElement(); }

FText STownAgeMapLayoutPanel::TypeText(TSharedPtr<FName> Item) const
{
    if (!Item.IsValid() || !HasLayout()) return FText::FromString(TEXT("Choose a layout type"));
    if (const FTownAgeMapType* Type = Owner->GetLayout()->FindType(*Item))
        return FText::FromString(Type->DisplayName.ToString() + TEXT("  [") + Item->ToString() + TEXT("]"));
    return FText::FromName(*Item);
}

void STownAgeMapLayoutPanel::Refresh()
{
    if (bRefreshing) return;
    TGuardValue<bool> Guard(bRefreshing, true);
    TypeItems.Reset();
    ElementItems.Reset();
    if (const ATownAgeMapLayout* Layout = Owner->GetLayout())
    {
        for (const FTownAgeMapType& Type : Layout->Types)
            if (Type.Kind == Owner->GetToolKind()) TypeItems.Add(MakeShared<FName>(Type.TypeId));
        for (const FTownAgeMapElement& Element : Layout->Elements)
        {
            auto Row = MakeShared<FElementRow>();
            Row->Id = Element.Id;
            Row->Summary = (Element.Label.IsEmpty() ? TEXT("Unnamed") : Element.Label)
                + FString::Printf(TEXT("\n%s  |  %s"), KindName(Element.Kind), *Element.TypeId.ToString());
            ElementItems.Add(Row);
        }
    }
    TypeCombo->RefreshOptions();
    TypeCombo->ClearSelection();
    for (const auto& Type : TypeItems)
        if (*Type == Owner->GetTypeId()) { TypeCombo->SetSelectedItem(Type); break; }
    ElementList->RequestListRefresh();
    ElementList->ClearSelection();
    for (const auto& Element : ElementItems)
        if (Element->Id == Owner->GetSelectedElementId()) { ElementList->SetSelection(Element, ESelectInfo::Direct); break; }
    if (const FTownAgeMapElement* Element = Owner->GetSelectedElement())
    {
        SelectedLabel = Element->Label;
        SelectedType = Element->TypeId.ToString();
        SelectedWidth = Element->WidthCm;
        SelectedHeight = Element->HeightCm;
    }
    else
    {
        SelectedLabel.Reset();
        SelectedType.Reset();
    }
}

TSharedRef<ITableRow> STownAgeMapLayoutPanel::MakeElementRow(TSharedPtr<FElementRow> Item, const TSharedRef<STableViewBase>& Table)
{
    return SNew(STableRow<TSharedPtr<FElementRow>>, Table).Padding(FMargin(6))
        [ SNew(STextBlock).Text(FText::FromString(Item->Summary)).AutoWrapText(true) ];
}

void STownAgeMapLayoutPanel::ElementSelected(TSharedPtr<FElementRow> Item, ESelectInfo::Type SelectInfo)
{
    if (!bRefreshing && Item.IsValid()) Owner->SelectElement(Item->Id);
}
