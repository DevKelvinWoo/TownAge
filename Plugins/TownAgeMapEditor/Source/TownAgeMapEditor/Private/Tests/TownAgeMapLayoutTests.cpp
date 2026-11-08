#include "TownAgeMapLayout.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/HitResult.h"
#include "Engine/World.h"
#include "Internationalization/Regex.h"
#include "Misc/AutomationTest.h"
#include <limits>

#if WITH_DEV_AUTOMATION_TESTS
namespace
{
    // Never replace GWorld or call CreateNewMap: these tests may run beside an
    // unsaved authoring level, so all actors belong to a private transient world.
    struct FLayoutTestWorld
    {
        UWorld* World = nullptr;
        explicit FLayoutTestWorld(EWorldType::Type WorldType = EWorldType::Editor)
        {
            const UWorld::InitializationValues Settings = UWorld::InitializationValues()
                .AllowAudioPlayback(false).CreatePhysicsScene(true).CreateNavigation(false)
                .CreateAISystem(false).ShouldSimulatePhysics(false).CreateFXSystem(false).EnableTraceCollision(true);
            World = UWorld::CreateWorld(WorldType, false, NAME_None, nullptr, true,
                ERHIFeatureLevel::Num, &Settings);
        }
        ~FLayoutTestWorld() { if (World) World->DestroyWorld(false); }
        ATownAgeMapLayout* Spawn() const
        {
            return World ? World->SpawnActor<ATownAgeMapLayout>() : nullptr;
        }
    };

    FTownAgeMapElement Element(ETownAgeMapElementKind Kind, FName Type, const TCHAR* Label,
        FVector A, FVector B)
    {
        FTownAgeMapElement Result;
        Result.Id = FGuid::NewGuid();
        Result.Label = Label;
        Result.Kind = Kind;
        Result.TypeId = Type;
        Result.Points = {A, B};
        return Result;
    }

    TArray<FTownAgeMapElement> SampleElements()
    {
        return {
            Element(ETownAgeMapElementKind::Road, TEXT("road.path"), TEXT("Main path"), FVector(0, 0, 0), FVector(1500, 0, 0)),
            Element(ETownAgeMapElementKind::Field, TEXT("field.soil"), TEXT("Vegetables"), FVector(0, 500, 0), FVector(1000, 1500, 0)),
            Element(ETownAgeMapElementKind::Building, TEXT("building.house"), TEXT("Village home"), FVector(2000, 500, 0), FVector(2800, 1100, 0))
        };
    }

    int32 InstanceCount(ATownAgeMapLayout* Layout)
    {
        TInlineComponentArray<UInstancedStaticMeshComponent*> Components(Layout);
        int32 Count = 0;
        for (const UInstancedStaticMeshComponent* Component : Components) Count += Component->GetInstanceCount();
        return Count;
    }
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTownAgeMapLayoutValidationTest, "TownAge.MapLayout.Validation",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FTownAgeMapLayoutValidationTest::RunTest(const FString& Parameters)
{
    const ATownAgeMapLayout* Defaults = GetDefault<ATownAgeMapLayout>();
    TestEqual(TEXT("Six independent starter types"), Defaults->Types.Num(), 6);
    for (const auto& Expected : TArray<TPair<FName, ETownAgeMapElementKind>> {
        {TEXT("road.path"), ETownAgeMapElementKind::Road}, {TEXT("road.stone"), ETownAgeMapElementKind::Road},
        {TEXT("field.soil"), ETownAgeMapElementKind::Field}, {TEXT("field.orchard"), ETownAgeMapElementKind::Field},
        {TEXT("building.house"), ETownAgeMapElementKind::Building}, {TEXT("building.shop"), ETownAgeMapElementKind::Building}})
    {
        const FTownAgeMapType* Type = Defaults->FindType(Expected.Key);
        TestNotNull(Expected.Key.ToString(), Type);
        if (Type) TestTrue(TEXT("Starter kind matches stable type key"), Type->Kind == Expected.Value);
    }
    const auto Types = Defaults->Types;
    const auto Valid = SampleElements();
    FString Error;
    TestTrue(TEXT("Road, field and building records form a valid plan"), ATownAgeMapLayout::ValidateData(Types, Valid, Error));
    TestTrue(TEXT("Empty new plan is valid"), ATownAgeMapLayout::ValidateData(Types, {}, Error));
    auto Reject = [&](const TCHAR* Reason, const TArray<FTownAgeMapElement>& Data)
    {
        Error.Reset();
        TestFalse(Reason, ATownAgeMapLayout::ValidateData(Types, Data, Error));
        TestFalse(TEXT("Rejected geometry explains its problem"), Error.IsEmpty());
    };
    auto Bad = Valid; Bad[0].TypeId = TEXT("road.unregistered"); Reject(TEXT("Unknown type rejected"), Bad);
    Bad = Valid; Bad[1].TypeId = TEXT("building.house"); Reject(TEXT("Type/category mismatch rejected"), Bad);
    Bad = Valid; Bad[1].Id = Bad[0].Id; Reject(TEXT("Duplicate placement identity rejected"), Bad);
    Bad = Valid; Bad[0].Id.Invalidate(); Reject(TEXT("Missing placement identity rejected"), Bad);
    Bad = Valid; Bad[0].Points[1] = Bad[0].Points[0]; Reject(TEXT("Zero-length road rejected"), Bad);
    Bad = Valid; Bad[1].Points[1].X = Bad[1].Points[0].X; Reject(TEXT("Zero-area field rejected"), Bad);
    Bad = Valid; Bad[2].Points.Pop(); Reject(TEXT("Incomplete rectangle rejected"), Bad);
    Bad = Valid; Bad[0].WidthCm = 49.f; Reject(TEXT("Too-narrow road rejected"), Bad);
    Bad = Valid; Bad[0].WidthCm = 3001.f; Reject(TEXT("Excessive road width rejected"), Bad);
    Bad = Valid; Bad[2].HeightCm = 10001.f; Reject(TEXT("Excessive building height rejected"), Bad);
    Bad = Valid; Bad[0].Points[1].X = std::numeric_limits<double>::quiet_NaN(); Reject(TEXT("Non-finite coordinates rejected"), Bad);
    auto BadTypes = Types; BadTypes.Add(Types[0]);
    TestFalse(TEXT("Duplicate catalog keys rejected"), ATownAgeMapLayout::ValidateData(BadTypes, Valid, Error));
    BadTypes = Types; BadTypes[0].TypeId = NAME_None;
    TestFalse(TEXT("Empty catalog key rejected"), ATownAgeMapLayout::ValidateData(BadTypes, Valid, Error));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTownAgeMapLayoutPrePlayCollisionTest, "TownAge.MapLayout.PrePlayCollision",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FTownAgeMapLayoutPrePlayCollisionTest::RunTest(const FString& Parameters)
{
    FLayoutTestWorld Scene(EWorldType::Game);
    ATownAgeMapLayout* Layout = Scene.Spawn();
    if (!TestNotNull(TEXT("Private game-world layout"), Layout)) return false;
    Layout->Elements = SampleElements();
    Layout->RebuildLayout();
    TestTrue(TEXT("Authoring fixture has disposable preview geometry"), Layout->GetGeneratedInstanceCount() >= 3);

    // Cooked levels retain the authored records, but not transient components.
    // Remove the authoring preview to reproduce that load state explicitly.
    TInlineComponentArray<UInstancedStaticMeshComponent*> Preview(Layout);
    for (UInstancedStaticMeshComponent* Component : Preview) Component->DestroyComponent();
    TestEqual(TEXT("Cooked-load fixture has no generated collision"), InstanceCount(Layout), 0);
    TestFalse(TEXT("Game world has not begun play"), Scene.World->HasBegunPlay());
    TestFalse(TEXT("Layout has not begun play"), Layout->HasActorBegunPlay());

    Layout->PostInitializeComponents();
    const int32 InitializedCount = Layout->GetGeneratedInstanceCount();
    TestTrue(TEXT("Map initialization creates proxies before player spawning"), InitializedCount >= 3);
    TestFalse(TEXT("Geometry does not require BeginPlay"), Layout->HasActorBegunPlay());
    TInlineComponentArray<UInstancedStaticMeshComponent*> RuntimeComponents(Layout);
    for (const UInstancedStaticMeshComponent* Component : RuntimeComponents)
    {
        TestTrue(TEXT("Runtime collision component is registered"), Component->IsRegistered());
        TestTrue(TEXT("Runtime component blocks queries and physics"), Component->GetCollisionEnabled() == ECollisionEnabled::QueryAndPhysics);
    }

    FHitResult Hit;
    const bool bHit = Scene.World->LineTraceSingleByChannel(Hit, FVector(2400, 800, 1000), FVector(2400, 800, -100), ECC_Visibility);
    TestTrue(TEXT("A pre-BeginPlay trace finds the authored building"), bHit);
    if (bHit)
    {
        TestTrue(TEXT("Pre-play collision belongs to this layout"), Hit.GetActor() == Layout);
        TestTrue(TEXT("Collision hit resolves the authored placement identity"),
            Layout->GetElementIdForInstance(Cast<UInstancedStaticMeshComponent>(Hit.GetComponent()), Hit.Item) == Layout->Elements[2].Id);
    }
    Layout->PostInitializeComponents();
    TestEqual(TEXT("Repeated initialization does not duplicate geometry"), Layout->GetGeneratedInstanceCount(), InitializedCount);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTownAgeMapLayoutRoundtripTest, "TownAge.MapLayout.JsonAtomicRoundtrip",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FTownAgeMapLayoutRoundtripTest::RunTest(const FString& Parameters)
{
    FLayoutTestWorld Scene;
    ATownAgeMapLayout* Source = Scene.Spawn();
    ATownAgeMapLayout* Target = Scene.Spawn();
    if (!TestNotNull(TEXT("Private source plan"), Source) || !TestNotNull(TEXT("Private target plan"), Target)) return false;
    Source->Elements = SampleElements();
    Source->Types[0].DisplayName = FText::FromString(TEXT("Village lane"));
    Source->Elements[1].Label = TEXT("딸기 밭");
    Source->SetActorTransform(FTransform(FRotator(0, 27, 0), FVector(1234, -800, 75), FVector(1.25)));
    Source->RebuildLayout();
    const FString Json = Source->ExportLayoutJson();
    TestFalse(TEXT("Export contains a snapshot"), Json.IsEmpty());
    FString Error;
    if (!TestTrue(TEXT("Export can be imported"), Target->ImportLayoutJson(Json, Error)))
    { AddError(Error); return false; }
    TestTrue(TEXT("Plan transform is portable"), Target->GetActorTransform().Equals(Source->GetActorTransform(), .001));
    TestEqual(TEXT("All type definitions retained"), Target->Types.Num(), Source->Types.Num());
    TestEqual(TEXT("All placements retained"), Target->Elements.Num(), Source->Elements.Num());
    if (Target->Elements.Num() != Source->Elements.Num() || Target->Types.Num() != Source->Types.Num()) return false;
    TestEqual(TEXT("Catalog display metadata retained"), Target->Types[0].DisplayName.ToString(), Source->Types[0].DisplayName.ToString());
    TestEqual(TEXT("Unicode placement label retained"), Target->Elements[1].Label, Source->Elements[1].Label);
    for (int32 I = 0; I < Source->Elements.Num(); ++I)
    {
        TestTrue(TEXT("Placement identity retained"), Target->Elements[I].Id == Source->Elements[I].Id);
        TestEqual(TEXT("Replacement type key retained"), Target->Elements[I].TypeId, Source->Elements[I].TypeId);
        TestTrue(TEXT("Local footprint retained"), Target->Elements[I].Points == Source->Elements[I].Points);
    }
    const FString Before = Target->ExportLayoutJson();
    const int32 BeforeInstances = Target->GetGeneratedInstanceCount();
    TestFalse(TEXT("Malformed JSON rejected"), Target->ImportLayoutJson(TEXT("{ not json"), Error));
    TestEqual(TEXT("Malformed import retains complete data"), Target->ExportLayoutJson(), Before);
    TestEqual(TEXT("Malformed import retains preview"), Target->GetGeneratedInstanceCount(), BeforeInstances);
    TestFalse(TEXT("Unsupported schema rejected"), Target->ImportLayoutJson(TEXT("{\"schemaVersion\":999,\"types\":[],\"elements\":[]}"), Error));
    TestEqual(TEXT("Schema rejection retains data"), Target->ExportLayoutJson(), Before);

    FRegexMatcher Width(FRegexPattern(TEXT("\"widthCm\"\\s*:\\s*[-+0-9.eE]+")), Json);
    if (TestTrue(TEXT("Portable width field is present"), Width.FindNext()))
    {
        const FString BadGeometry = Json.Left(Width.GetMatchBeginning()) + TEXT("\"widthCm\":-1") + Json.Mid(Width.GetMatchEnding());
        TestFalse(TEXT("Semantically invalid JSON rejected"), Target->ImportLayoutJson(BadGeometry, Error));
        TestEqual(TEXT("Invalid geometry import retains data"), Target->ExportLayoutJson(), Before);
        TestEqual(TEXT("Invalid geometry import retains preview"), Target->GetGeneratedInstanceCount(), BeforeInstances);
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTownAgeMapLayoutGeometryTest, "TownAge.MapLayout.RebuildAndReplacement",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FTownAgeMapLayoutGeometryTest::RunTest(const FString& Parameters)
{
    FLayoutTestWorld Scene;
    ATownAgeMapLayout* Layout = Scene.Spawn();
    if (!TestNotNull(TEXT("Private preview plan"), Layout)) return false;
    Layout->Elements = SampleElements();
    Layout->RebuildLayout();
    const int32 InitialCount = Layout->GetGeneratedInstanceCount();
    TestTrue(TEXT("All three authored categories produce geometry"), InitialCount >= 3);
    TestEqual(TEXT("Reported preview count matches owned component instances"), InstanceCount(Layout), InitialCount);
    TInlineComponentArray<UInstancedStaticMeshComponent*> InitialComponents(Layout);
    Layout->RebuildLayout(); Layout->RebuildLayout();
    TInlineComponentArray<UInstancedStaticMeshComponent*> RebuiltComponents(Layout);
    TestEqual(TEXT("Rebuild does not accumulate components"), RebuiltComponents.Num(), InitialComponents.Num());
    TestEqual(TEXT("Rebuild does not accumulate instances"), Layout->GetGeneratedInstanceCount(), InitialCount);
    TSet<FGuid> PickedIds;
    for (UInstancedStaticMeshComponent* Component : RebuiltComponents)
    {
        for (int32 Index = 0; Index < Component->GetInstanceCount(); ++Index)
        {
            const FGuid Id = Layout->GetElementIdForInstance(Component, Index);
            TestTrue(TEXT("Every generated instance can be picked by stable identity"), Id.IsValid());
            PickedIds.Add(Id);
        }
        TestFalse(TEXT("Invalid picking index cannot select a placement"), Layout->GetElementIdForInstance(Component, -1).IsValid());
    }
    for (const FTownAgeMapElement& Record : Layout->Elements)
        TestTrue(TEXT("Each authored record has a selectable proxy"), PickedIds.Contains(Record.Id));

    // An arbitrary replacement mesh uses its real bounds, not an assumed cube size.
    UStaticMesh* Cylinder = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    if (!TestNotNull(TEXT("Engine replacement fixture mesh"), Cylinder)) return false;
    Layout->Elements = { Element(ETownAgeMapElementKind::Building, TEXT("building.house"), TEXT("Replaced home"), FVector(200, 300, 0), FVector(1000, 900, 0)) };
    Layout->Elements[0].HeightCm = 500.f;
    for (FTownAgeMapType& Type : Layout->Types)
        if (Type.TypeId == TEXT("building.house")) Type.Mesh = Cylinder;
    Layout->RebuildLayout();
    TInlineComponentArray<UInstancedStaticMeshComponent*> CustomComponents(Layout);
    bool bCheckedReplacement = false;
    for (UInstancedStaticMeshComponent* Component : CustomComponents)
    {
        if (Component->GetStaticMesh() != Cylinder || Component->GetInstanceCount() == 0) continue;
        FTransform Instance;
        TestTrue(TEXT("Replacement instance transform is available"), Component->GetInstanceTransform(0, Instance, true));
        const FVector Size = Cylinder->GetBoundingBox().TransformBy(Instance).GetSize();
        TestTrue(TEXT("Replacement mesh fits authored width"), FMath::IsNearlyEqual(Size.X, 800.0, .5));
        TestTrue(TEXT("Replacement mesh fits authored depth"), FMath::IsNearlyEqual(Size.Y, 600.0, .5));
        TestTrue(TEXT("Replacement mesh fits authored height"), FMath::IsNearlyEqual(Size.Z, 500.0, .5));
        bCheckedReplacement = true;
    }
    TestTrue(TEXT("Type-specific replacement mesh was actually generated"), bCheckedReplacement);
    return true;
}
#endif
