// Copyright (c) 2025 Advanced Micro Devices, Inc. All Rights Reserved.

#include "Misc/AutomationTest.h"

#include "Misc/FileHelper.h"
#include "HAL/PlatformFileManager.h"
#include "NNEModelData.h"
#include "Policies/NNEPolicy.h"
#include "Common/InteractionDefinition.h"
#include "Spaces/DictSpace.h"
#include "Spaces/BoxSpace.h"
#include "Spaces/DiscreteSpace.h"
#include "Points/DictPoint.h"
#include "Points/BoxPoint.h"
#include "Points/MultiDiscretePoint.h"
#include "Spaces/MultiDiscreteSpace.h"
#include "Points/DiscretePoint.h"

#define TestEqualExactFloat(TestMessage, Actual, Expected) TestEqual(TestMessage, (float)Actual, (float)Expected, 0.0001f)

/**
 * Helper function to create a test ONNX model data object
 */
UNNEModelData* CreateTestModelData(FAutomationTestBase& Test, const FString& ModelPath)
{
    // Check if file exists first
    if (!FPlatformFileManager::Get().GetPlatformFile().FileExists(*ModelPath))
    {
        Test.AddError(FString::Printf(TEXT("Test model file does not exist at path: %s"), *ModelPath));
        return nullptr;
    }

    // Load the ONNX file
    TArray<uint8> FileData;
    if (!FFileHelper::LoadFileToArray(FileData, *ModelPath))
    {
        Test.AddError(FString::Printf(TEXT("Failed to load test model file from: %s"), *ModelPath));
        return nullptr;
    }

    // Create UNNEModelData object with proper outer
    UNNEModelData* ModelData = NewObject<UNNEModelData>(GetTransientPackage());
    if (!ModelData)
    {
        Test.AddError(TEXT("Failed to create UNNEModelData object"));
        return nullptr;
    }

    // Initialize the model data with the ONNX file
    ModelData->Init(TEXT("onnx"), FileData);
    
    return ModelData;
}

/**
 * Helper function to create the interaction definition that matches our test model
 */
FInteractionDefinition CreateBasicTestInteractionDefinition()
{
    FInteractionDefinition Definition;

    // Create observation space: DictSpace with Position_X_-500,00_500,00 -> BoxSpace(-500, 500)
    TInstancedStruct<FSpace> ObsSpace;
    ObsSpace.InitializeAs<FDictSpace>();
    FDictSpace& ObsDictSpace = ObsSpace.GetMutable<FDictSpace>();
    
    TInstancedStruct<FSpace> PositionSpace;
    PositionSpace.InitializeAs<FBoxSpace>();
    FBoxSpace& BoxSpace = PositionSpace.GetMutable<FBoxSpace>();
    BoxSpace.Add(-500.0f, 500.0f);
    
    ObsDictSpace.Spaces.Add(TEXT("Position_X_-500,00_500,00"), PositionSpace);
    Definition.ObsSpaceDefn = ObsSpace;

    // Create action space: DictSpace with Teleport_X_100,00 -> DiscreteSpace(3)
    TInstancedStruct<FSpace> ActionSpace;
    ActionSpace.InitializeAs<FDictSpace>();
    FDictSpace& ActionDictSpace = ActionSpace.GetMutable<FDictSpace>();
    
    TInstancedStruct<FSpace> TeleportSpace;
    TeleportSpace.InitializeAs<FMultiDiscreteSpace>();
    FMultiDiscreteSpace& DiscreteSpace = TeleportSpace.GetMutable<FMultiDiscreteSpace>();
    DiscreteSpace.Add(3); // 3 discrete actions
    
    ActionDictSpace.Spaces.Add(TEXT("Teleport_X_100,00"), TeleportSpace);
    Definition.ActionSpaceDefn = ActionSpace;

    return Definition;
}

/**
 * Helper function to create a test observation
 */
TInstancedStruct<FPoint> CreateTestObservation(float PositionValue)
{
    TInstancedStruct<FPoint> Observation;
    Observation.InitializeAs<FDictPoint>();
    FDictPoint& DictPoint = Observation.GetMutable<FDictPoint>();
    
    TInstancedStruct<FPoint> PositionPoint;
    PositionPoint.InitializeAs<FBoxPoint>();
    FBoxPoint& BoxPoint = PositionPoint.GetMutable<FBoxPoint>();
    BoxPoint.Values.Add(PositionValue);
    
    DictPoint.Points.Add(TEXT("Position_X_-500,00_500,00"), PositionPoint);
    
    return Observation;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FNNEPolicyRuntimeAvailabilityTest, "Schola.Policies.NNE.NNEPolicy.RuntimeAvailability Test", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FNNEPolicyRuntimeAvailabilityTest::RunTest(const FString& Parameters)
{
    UNNEPolicy* Policy = NewObject<UNNEPolicy>(GetTransientPackage());
    TestTrue(TEXT("Policy should be created"), Policy != nullptr);

    TArray<FString> RuntimeNames = Policy->GetRuntimeNames();
    if (RuntimeNames.Num() == 0)
    {
        AddWarning(TEXT("No runtimes available, skipping test"));
        return false;
    }

    IRuntimeInterface* Runtime = Policy->GetRuntime(RuntimeNames[0]);
    TestTrue(FString::Printf(TEXT("Should be able to get runtime: %s"), *RuntimeNames[0]), Runtime != nullptr);

    if (Runtime)
    {
        TestTrue(FString::Printf(TEXT("Runtime %s should be valid"), *RuntimeNames[0]), Runtime->IsValid());
        // Do not delete unless API guarantees caller ownership.
        // delete Runtime;
    }

    IRuntimeInterface* InvalidRuntime = Policy->GetRuntime(TEXT("NonExistentRuntime"));
    TestTrue(TEXT("Should return null for invalid runtime"), InvalidRuntime == nullptr);

    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FNNEPolicyThinkBeforeInitTest, "Schola.Policies.NNE.NNEPolicy.ThinkBeforeInit Test", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FNNEPolicyThinkBeforeInitTest::RunTest(const FString& Parameters)
{
    UNNEPolicy* Policy = NewObject<UNNEPolicy>(GetTransientPackage());
    TestTrue(TEXT("Policy should be created"), Policy != nullptr);
    
    // Try to call Think before Init
    TInstancedStruct<FPoint> Observation = CreateTestObservation(100.0f);
    TInstancedStruct<FPoint> Action;
    
    bool ThinkResult = Policy->Think(Observation, Action);
    TestFalse(TEXT("Think should fail when called before Init"), ThinkResult);
    
    return true;
}
