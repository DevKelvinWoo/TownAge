#include "TownAgeMapLayout.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "JsonObjectConverter.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/ConstructorHelpers.h"

DEFINE_LOG_CATEGORY_STATIC(LogTownAgeMapLayout, Log, All);

namespace
{
    constexpr int32 MaxElements = 5000;
    constexpr int32 MaxInstances = 50000;
    constexpr int32 MaxJsonCharacters = 8 * 1024 * 1024;

    bool ValidKind(ETownAgeMapElementKind Kind)
    {
        return uint8(Kind) <= uint8(ETownAgeMapElementKind::Building);
    }

    bool ValidTransform(const FTransform& Transform)
    {
        const FVector Scale = Transform.GetScale3D();
        return Transform.IsValid() && Scale.GetMin() >= .001 && Scale.GetMax() <= 100.0;
    }

    FTransform FitMesh(const UStaticMesh* Mesh, const FVector& Center, const FVector& Size, const FQuat& Rotation)
    {
        const FBoxSphereBounds Bounds = Mesh->GetBounds();
        const FVector BoundsSize = Bounds.BoxExtent * 2.0;
        const FVector Scale(Size.X / FMath::Max(1.0, BoundsSize.X), Size.Y / FMath::Max(1.0, BoundsSize.Y),
                            Size.Z / FMath::Max(1.0, BoundsSize.Z));
        return FTransform(Rotation, Center - Rotation.RotateVector(Bounds.Origin * Scale), Scale);
    }
}

ATownAgeMapLayout::ATownAgeMapLayout()
{
    bReplicates = false;
    PrimaryActorTick.bCanEverTick = false;
    LayoutRoot = CreateDefaultSubobject<USceneComponent>(TEXT("LayoutRoot"));
    SetRootComponent(LayoutRoot);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
    PlaceholderMesh = Cube.Object;
    PlaceholderMaterial = Material.Object;
    auto AddType = [&](const TCHAR* Id, ETownAgeMapElementKind Kind, const TCHAR* Name, FLinearColor Color, float Height)
    {
        FTownAgeMapType Type;
        Type.TypeId = FName(Id); Type.Kind = Kind; Type.DisplayName = FText::FromString(Name);
        Type.PreviewColor = Color; Type.DefaultHeightCm = Height;
        Types.Add(Type);
    };
    AddType(TEXT("road.path"), ETownAgeMapElementKind::Road, TEXT("Path"), FLinearColor(.32f, .40f, .43f), 300);
    AddType(TEXT("road.stone"), ETownAgeMapElementKind::Road, TEXT("Stone road"), FLinearColor(.65f, .66f, .62f), 300);
    AddType(TEXT("field.soil"), ETownAgeMapElementKind::Field, TEXT("Soil field"), FLinearColor(.36f, .19f, .075f), 300);
    AddType(TEXT("field.orchard"), ETownAgeMapElementKind::Field, TEXT("Orchard field"), FLinearColor(.28f, .50f, .14f), 300);
    AddType(TEXT("building.house"), ETownAgeMapElementKind::Building, TEXT("House"), FLinearColor(.26f, .50f, .72f), 300);
    AddType(TEXT("building.shop"), ETownAgeMapElementKind::Building, TEXT("Shop"), FLinearColor(.78f, .48f, .16f), 450);
}

void ATownAgeMapLayout::PostRegisterAllComponents()
{
    Super::PostRegisterAllComponents();
    // Native actors loaded from a saved editor map need not rerun construction.
    // Their transient previews are rebuilt once component registration is ready.
    // Rebuild's guard also covers registration of the generated components here.
    if (GetWorld() && !GetWorld()->IsGameWorld()) RebuildLayout();
}

void ATownAgeMapLayout::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    // Runtime collision is established once in PostInitializeComponents, before
    // gameplay spawn collision checks. Editor construction still previews edits.
    if (GetWorld() && !GetWorld()->IsGameWorld()) RebuildLayout();
}

void ATownAgeMapLayout::PostInitializeComponents()
{
    Super::PostInitializeComponents();
    // The authored level data is shared by all peers; transient geometry is
    // rebuilt on rendering clients AND dedicated authority for equal collision.
    // Cooked loads do not serialize it, and waiting for BeginPlay is too late
    // for GameMode's initial player-spawn encroachment checks.
    if (GetWorld() && GetWorld()->IsGameWorld()) RebuildLayout();
}

#if WITH_EDITOR
void ATownAgeMapLayout::PostEditChangeProperty(FPropertyChangedEvent& Event)
{
    Super::PostEditChangeProperty(Event);
    RebuildLayout();
}

void ATownAgeMapLayout::PostEditUndo()
{
    Super::PostEditUndo();
    RebuildLayout();
}
#endif

const FTownAgeMapType* ATownAgeMapLayout::FindType(FName TypeId) const
{
    return Types.FindByPredicate([TypeId](const FTownAgeMapType& Type) { return Type.TypeId == TypeId; });
}

bool ATownAgeMapLayout::ValidateData(const TArray<FTownAgeMapType>& InTypes,
    const TArray<FTownAgeMapElement>& InElements, FString& Error)
{
    Error.Reset();
    auto Fail = [&](const FString& Message) { Error = Message; return false; };
    if (InTypes.Num() > 256) return Fail(TEXT("The catalog cannot exceed 256 types."));
    if (InElements.Num() > MaxElements) return Fail(TEXT("The layout cannot exceed 5000 elements."));
    TMap<FName, ETownAgeMapElementKind> Kinds;
    for (int32 Index = 0; Index < InTypes.Num(); ++Index)
    {
        const FTownAgeMapType& Type = InTypes[Index];
        if (Type.TypeId.IsNone() || Type.TypeId.ToString().Len() > 128 || Kinds.Contains(Type.TypeId))
            return Fail(FString::Printf(TEXT("Catalog type %d needs a unique, nonempty TypeId of at most 128 characters."), Index));
        if (!ValidKind(Type.Kind)) return Fail(FString::Printf(TEXT("Catalog type %s has an invalid kind."), *Type.TypeId.ToString()));
        if (!FMath::IsFinite(Type.DefaultHeightCm) || Type.DefaultHeightCm < 50 || Type.DefaultHeightCm > 10000 ||
            !FMath::IsFinite(Type.PreviewColor.R) || !FMath::IsFinite(Type.PreviewColor.G) ||
            !FMath::IsFinite(Type.PreviewColor.B) || !FMath::IsFinite(Type.PreviewColor.A))
            return Fail(FString::Printf(TEXT("Catalog type %s has an invalid height or preview color."), *Type.TypeId.ToString()));
        Kinds.Add(Type.TypeId, Type.Kind);
    }
    TSet<FGuid> Ids;
    int32 InstanceCount = 0;
    for (int32 Index = 0; Index < InElements.Num(); ++Index)
    {
        const FTownAgeMapElement& Element = InElements[Index];
        const FString Context = FString::Printf(TEXT("Element %d (%s)"), Index, *Element.Label);
        const ETownAgeMapElementKind* Kind = Kinds.Find(Element.TypeId);
        if (!Element.Id.IsValid() || Ids.Contains(Element.Id)) return Fail(Context + TEXT(" needs a unique valid ID."));
        Ids.Add(Element.Id);
        if (Element.Label.Len() > 128) return Fail(Context + TEXT(" has a label longer than 128 characters."));
        if (!ValidKind(Element.Kind) || !Kind || *Kind != Element.Kind)
            return Fail(Context + TEXT(" references a missing type or a type of a different kind."));
        if (!FMath::IsFinite(Element.WidthCm) || Element.WidthCm < 50 || Element.WidthCm > 3000 ||
            !FMath::IsFinite(Element.HeightCm) || Element.HeightCm < 50 || Element.HeightCm > 10000)
            return Fail(Context + TEXT(" needs width 50..3000 cm and height 50..10000 cm."));
        const bool bRoad = Element.Kind == ETownAgeMapElementKind::Road;
        if ((bRoad && (Element.Points.Num() < 2 || Element.Points.Num() > 512)) || (!bRoad && Element.Points.Num() != 2))
            return Fail(Context + TEXT(" needs 2..512 road points or exactly two rectangle corners."));
        for (const FVector& Point : Element.Points)
            if (Point.ContainsNaN() || Point.GetAbsMax() > 10000000.0)
                return Fail(Context + TEXT(" contains non-finite or out-of-range coordinates."));
        if (bRoad)
        {
            for (int32 Point = 1; Point < Element.Points.Num(); ++Point)
                if (FVector::DistSquaredXY(Element.Points[Point - 1], Element.Points[Point]) < 2500.0)
                    return Fail(Context + TEXT(" has a road segment shorter than 50 cm in XY."));
            InstanceCount += Element.Points.Num() * 2 - 3; // Segments + square interior joins.
        }
        else
        {
            const FVector Size = (Element.Points[1] - Element.Points[0]).GetAbs();
            if (Size.X < 50 || Size.Y < 50) return Fail(Context + TEXT(" needs a rectangle at least 50 cm wide and long."));
            ++InstanceCount;
        }
        if (InstanceCount > MaxInstances) return Fail(TEXT("The layout exceeds the 50000 generated-instance budget."));
    }
    return true;
}

bool ATownAgeMapLayout::ValidateLayout(FString& Error) const
{
    if (!ValidTransform(GetActorTransform()))
    {
        Error = TEXT("Layout transform must be finite with positive scale between 0.001 and 100.");
        return false;
    }
    return ValidateData(Types, Elements, Error);
}

void ATownAgeMapLayout::RebuildLayout()
{
    if (bRebuilding || IsTemplate() || !GetWorld()) return;
    TGuardValue<bool> Guard(bRebuilding, true);
    FString Error;
    if (!ValidateLayout(Error) || !PlaceholderMesh)
    {
        UE_LOG(LogTownAgeMapLayout, Warning, TEXT("Layout preview retained: %s"), *Error);
        return;
    }
    InstanceElements.Reset();
    for (UInstancedStaticMeshComponent* Component : GeneratedComponents)
        if (IsValid(Component)) Component->DestroyComponent();
    GeneratedComponents.Reset();
    TMap<FName, UInstancedStaticMeshComponent*> Groups;
    auto GroupFor = [&](const FTownAgeMapType& Type)
    {
        if (UInstancedStaticMeshComponent** Existing = Groups.Find(Type.TypeId)) return *Existing;
        UStaticMesh* Mesh = Type.Mesh.IsNull() ? nullptr : Type.Mesh.LoadSynchronous();
        const bool bPlaceholder = Mesh == nullptr;
        if (!Type.Mesh.IsNull() && !Mesh)
            UE_LOG(LogTownAgeMapLayout, Warning, TEXT("Type %s mesh could not load; using placeholder."), *Type.TypeId.ToString());
        UInstancedStaticMeshComponent* Component = NewObject<UInstancedStaticMeshComponent>(this, NAME_None, RF_Transient);
        Component->CreationMethod = EComponentCreationMethod::UserConstructionScript;
        Component->SetupAttachment(LayoutRoot);
        // These transient components have no baked lightmap. Movable also lets
        // the entire plan transform safely during editor manipulation/import.
        Component->SetMobility(EComponentMobility::Movable);
        Component->SetStaticMesh(bPlaceholder ? PlaceholderMesh.Get() : Mesh);
        Component->SetCollisionProfileName(TEXT("BlockAll"));
        Component->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
        Component->SetGenerateOverlapEvents(false);
        Component->SetCastShadow(Type.Kind == ETownAgeMapElementKind::Building);
#if WITH_EDITOR
        Component->bHasPerInstanceHitProxies = true;
#endif
        UMaterialInterface* Override = Type.Material.IsNull() ? nullptr : Type.Material.LoadSynchronous();
        if (!Type.Material.IsNull() && !Override)
            UE_LOG(LogTownAgeMapLayout, Warning, TEXT("Type %s material could not load; retaining mesh material."), *Type.TypeId.ToString());
        if (!Override && bPlaceholder && PlaceholderMaterial)
        {
            UMaterialInstanceDynamic* Tint = UMaterialInstanceDynamic::Create(PlaceholderMaterial, Component);
            TArray<FMaterialParameterInfo> Parameters;
            TArray<FGuid> ParameterIds;
            PlaceholderMaterial->GetAllVectorParameterInfo(Parameters, ParameterIds);
            if (Parameters.ContainsByPredicate([](const FMaterialParameterInfo& Info) { return Info.Name == TEXT("Color"); }))
                Tint->SetVectorParameterValue(TEXT("Color"), Type.PreviewColor);
            Override = Tint;
        }
        if (Override)
            for (int32 Slot = 0; Slot < Component->GetNumMaterials(); ++Slot) Component->SetMaterial(Slot, Override);
        Component->RegisterComponent();
        GeneratedComponents.Add(Component);
        InstanceElements.Add(Component);
        Groups.Add(Type.TypeId, Component);
        return Component;
    };
    for (const FTownAgeMapElement& Element : Elements)
    {
        const FTownAgeMapType* Type = FindType(Element.TypeId);
        UInstancedStaticMeshComponent* Component = GroupFor(*Type);
        auto AddBox = [&](const FVector& Center, const FVector& Size, const FQuat& Rotation = FQuat::Identity)
        {
            Component->AddInstance(FitMesh(Component->GetStaticMesh(), Center, Size, Rotation));
            InstanceElements.FindChecked(Component).Add(Element.Id);
        };
        if (Element.Kind == ETownAgeMapElementKind::Road)
        {
            constexpr float Thickness = 8.f;
            for (int32 Point = 1; Point < Element.Points.Num(); ++Point)
            {
                const FVector Delta = Element.Points[Point] - Element.Points[Point - 1];
                AddBox((Element.Points[Point] + Element.Points[Point - 1]) * .5 + FVector(0, 0, Thickness * .5),
                    FVector(Delta.Size(), Element.WidthCm, Thickness), Delta.Rotation().Quaternion());
            }
            for (int32 Point = 1; Point + 1 < Element.Points.Num(); ++Point)
                AddBox(Element.Points[Point] + FVector(0, 0, Thickness * .5), FVector(Element.WidthCm, Element.WidthCm, Thickness));
        }
        else
        {
            const FVector A = Element.Points[0], B = Element.Points[1];
            const float Height = Element.Kind == ETownAgeMapElementKind::Building ? Element.HeightCm : 4.f;
            AddBox((A + B) * .5 + FVector(0, 0, Height * .5), FVector(FMath::Abs(B.X - A.X), FMath::Abs(B.Y - A.Y), Height));
        }
    }
}

FGuid ATownAgeMapLayout::GetElementIdForInstance(const UInstancedStaticMeshComponent* Component, int32 InstanceIndex) const
{
    const TArray<FGuid>* Ids = InstanceElements.Find(Component);
    return Ids && Ids->IsValidIndex(InstanceIndex) ? (*Ids)[InstanceIndex] : FGuid();
}

int32 ATownAgeMapLayout::GetGeneratedInstanceCount() const
{
    int32 Count = 0;
    for (const UInstancedStaticMeshComponent* Component : GeneratedComponents)
        if (IsValid(Component)) Count += Component->GetInstanceCount();
    return Count;
}

FString ATownAgeMapLayout::ExportLayoutJson() const
{
    FString Error;
    if (!ValidateLayout(Error))
    {
        UE_LOG(LogTownAgeMapLayout, Warning, TEXT("Cannot export invalid layout: %s"), *Error);
        return FString();
    }
    FTownAgeMapLayoutSnapshot Snapshot;
    Snapshot.LayoutTransform = GetActorTransform();
    Snapshot.Types = Types; Snapshot.Elements = Elements;
    FString Json;
    FJsonObjectConverter::UStructToJsonObjectString(Snapshot, Json);
    return Json;
}

bool ATownAgeMapLayout::ImportLayoutJson(const FString& Json, FString& Error)
{
    Error.Reset();
    if (Json.Len() == 0 || Json.Len() > MaxJsonCharacters)
    {
        Error = TEXT("Layout JSON must be nonempty and at most 8 Mi characters.");
        return false;
    }
    TSharedPtr<FJsonObject> Root;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid())
    { Error = TEXT("Malformed layout JSON object."); return false; }
    double Version = 0;
    if (!Root->TryGetNumberField(TEXT("schemaVersion"), Version) || Version != 1.0 ||
        !Root->HasField(TEXT("layoutTransform")) ||
        !Root->HasTypedField<EJson::Array>(TEXT("types")) || !Root->HasTypedField<EJson::Array>(TEXT("elements")))
    { Error = TEXT("Expected schemaVersion 1, layoutTransform, types and elements."); return false; }
    FTownAgeMapLayoutSnapshot Snapshot;
    FText Reason;
    if (!FJsonObjectConverter::JsonObjectToUStruct(Root.ToSharedRef(), &Snapshot, 0, 0, true, &Reason))
    { Error = TEXT("Invalid layout JSON: ") + Reason.ToString(); return false; }
    if (!ValidTransform(Snapshot.LayoutTransform))
    { Error = TEXT("Imported layout transform is invalid."); return false; }
    if (!ValidateData(Snapshot.Types, Snapshot.Elements, Error)) return false;
    // Validate everything first. Editor callers own the outer undo transaction.
    Modify();
    Types = MoveTemp(Snapshot.Types);
    Elements = MoveTemp(Snapshot.Elements);
    SetActorTransform(Snapshot.LayoutTransform);
    RebuildLayout();
    return true;
}
