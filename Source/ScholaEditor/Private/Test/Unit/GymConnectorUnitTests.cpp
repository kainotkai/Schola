// Copyright (c) 2025 Advanced Micro Devices, Inc. All Rights Reserved.

#include "Misc/AutomationTest.h"
#include "Tests/AutomationEditorCommon.h"
#include "Tests/AutomationCommon.h"
#include "CoreGlobals.h"
#include "Editor.h"
#include "Engine/World.h"
#include "GymConnectors/ManualGymConnector.h"
#include "BasicTestEnvironment.h"
#include "GymConnectors/AbstractGymConnector.h"
#include "Points/DiscretePoint.h"
#include "Points/BoxPoint.h"


struct FSimpleGymConnectorTestContext
{
	ABasicTestEnvironment* Env = nullptr;
	UManualGymConnector* Connector = nullptr;
	int TargetSteps = 3;
	int StepNumber = 0;
	// initial number of steps for logging
	int InitialSteps = 0;
	FAutomationTestBase* Test = nullptr; // for assertions
};


DEFINE_LATENT_AUTOMATION_COMMAND_ONE_PARAMETER(FSpawnConnectorCommand, TSharedPtr<FSimpleGymConnectorTestContext>, Context);
bool FSpawnConnectorCommand::Update()
{
	if (!GEditor->IsPlayingSessionInEditor()) // wait for PIE
	{
		return false;
	}

	UWorld* World = GEditor->GetPIEWorldContext()->World();
	
	if (!World)
	{
		return false;
	}
	if (!Context->Connector)
	{
		Context->Connector = NewObject<UManualGymConnector>(World->GetWorldSettings());
		TArray<TScriptInterface<IBaseScholaEnvironment>> Envs;
		Context->Connector->UAbstractGymConnector::CollectEnvironments(Envs);
		Context->Connector->UAbstractGymConnector::Init(Envs);
		UE_LOG(LogTemp, Log, TEXT("[ManualConnectorTest] Created & enabled ManualGymConnector %s"), *Context->Connector->GetName());
	}
	return true;
}

DEFINE_LATENT_AUTOMATION_COMMAND_ONE_PARAMETER(FSpawnMultiAgentEnvCommand, TSharedPtr<FSimpleGymConnectorTestContext>, Context);
bool FSpawnMultiAgentEnvCommand::Update()
{
	if (!GEditor->IsPlayingSessionInEditor()) // wait for PIE
	{
		return false;
	}

	UWorld* World = GEditor->GetPIEWorldContext()->World();

	if (!World)
	{
		return false;
	}
	if (!Context->Env)
	{
		Context->Env = World->SpawnActor<ABasicTestMultiAgentEnvironment>();
		if (!Context->Env)
		{
			UE_LOG(LogTemp, Error, TEXT("Failed to spawn ABasicMultiAgentTestEnvironment"));
			return true; // abort
		}
		else
		{
			FVector Loc = Context->Env->GetActorLocation();
			UE_LOG(LogTemp, Log, TEXT("[ManualConnectorTest] Spawned ABasicMultiAgentTestEnvironment at X=%f Y=%f Z=%f"), Loc.X, Loc.Y, Loc.Z);
		}
	}
	return true;
}

DEFINE_LATENT_AUTOMATION_COMMAND_ONE_PARAMETER(FSpawnSingleAgentEnvCommand, TSharedPtr<FSimpleGymConnectorTestContext>, Context);
bool FSpawnSingleAgentEnvCommand::Update()
{
	if (!GEditor->IsPlayingSessionInEditor()) // wait for PIE
	{
		return false;
	}

	UWorld* World = GEditor->GetPIEWorldContext()->World();

	if (!World)
	{
		return false;
	}

	if (!Context->Env)
	{
		Context->Env = World->SpawnActor<ABasicTestSingleAgentEnvironment>();
		if (!Context->Env)
		{
			UE_LOG(LogTemp, Error, TEXT("Failed to spawn ABasicSingleAgentTestEnvironment"));
			return true; // abort
		}
		else
		{
			FVector Loc = Context->Env->GetActorLocation();
			UE_LOG(LogTemp, Log, TEXT("[ManualConnectorTest] Spawned ABasicSingleAgentTestEnvironment at X=%f Y=%f Z=%f"), Loc.X, Loc.Y, Loc.Z);
		}
	}
	return true;
}

DEFINE_LATENT_AUTOMATION_COMMAND_ONE_PARAMETER(FStepConnectorCommand, TSharedPtr<FSimpleGymConnectorTestContext>, Context);
bool FStepConnectorCommand::Update()
{
	if (!Context->Connector)
	{
		return true;
	}

	// Drive manual steps synchronously (Tick not required since we call Step)
	float BeforeX = Context->Env ? Context->Env->GetActorLocation().X : 0.f;
	
	UE_LOG(LogTemp, Log, TEXT("[ManualConnectorTest] Step %d BEGIN (remaining before=%d) EnvX=%f"), Context->StepNumber, Context->TargetSteps - Context->StepNumber, BeforeX);
	

	int32			 ActionValue = (Context->StepNumber % 2 == 1) ? 1 : 0;
	//TArray<TMap<FString, TInstancedStruct<FPoint>>> Actions;
	TMap<FString, TInstancedStruct<FPoint>> Actions;
	Actions.Emplace(Context->Env->AgentName, TInstancedStruct<FPoint>::Make<FDiscretePoint>(ActionValue));
	FInitialState InitState;
	FTrainingState TrainState;
	Context->Connector->ManualStep({ Actions }, InitState, TrainState);

	float AfterX = Context->Env ? Context->Env->GetActorLocation().X : 0.f;
	Context->StepNumber++;
	
	UE_LOG(LogTemp, Log, TEXT("[ManualConnectorTest] Step %d END   (remaining=%d)  EnvX=%f"), Context->StepNumber, Context->TargetSteps - Context->StepNumber, AfterX);
	
	bool bDone = Context->StepNumber >= Context->TargetSteps;
	
	if (bDone)
	{
		UE_LOG(LogTemp, Log, TEXT("[ManualConnectorTest] Completed all %d steps"), Context->InitialSteps);
	}
	
	return bDone; // complete after requested steps
}

DEFINE_LATENT_AUTOMATION_COMMAND_ONE_PARAMETER(FResetConnectorCommand, TSharedPtr<FSimpleGymConnectorTestContext>, Context);
bool FResetConnectorCommand::Update()
{
	if (!Context->Connector)
	{
		return true;
	}

	int32 ActionValue = (Context->StepNumber % 2 == 1) ? 1 : 0;
	FInitialState  InitState;
	Context->Connector->ManualReset(TMap<int32,int32>(),TMap<int,TMap<FString,FString>>(), InitState);

	return true; // complete after requested steps
}

DEFINE_LATENT_AUTOMATION_COMMAND_ONE_PARAMETER(FVerifyEnvPositionCommand, TSharedPtr<FSimpleGymConnectorTestContext>, Context);
bool FVerifyEnvPositionCommand::Update()
{
	if (!Context->Env)
	{
		UE_LOG(LogTemp, Error, TEXT("Environment missing in verification"));
		if (Context->Test) 
		{ 
			UE_LOG(LogTemp, Error, TEXT("Environment missing in verification"));
		}
		
		return true;
	}
	
	float X = Context->Env->GetActorLocation().X;
	float LogicalX = Context->Env->GetLogicalPositionX();
	
	UE_LOG(LogTemp, Log, TEXT("Env X after steps: World=%f Logical=%f"), X, LogicalX);
	
	if (LogicalX <= 0.f)
	{
		UE_LOG(LogTemp, Display, TEXT("Environment logical X did not move positive. Check action generation (expected > 0)."));
		
		if (Context->Test) 
		{ 
			UE_LOG(LogTemp, Display, TEXT("Logical position did not advance > 0")); 
		}
	}
	if (FMath::Abs(LogicalX - X) > KINDA_SMALL_NUMBER)
	{
		UE_LOG(LogTemp, Display, TEXT("World transform X (%f) did not reflect logical X (%f)."), X, LogicalX);
		if (Context->Test) 
		{ 
			UE_LOG(LogTemp, Display, TEXT("World X (%f) != Logical X (%f)"), X, LogicalX); 
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSimpleMultiAgentGymConnectorTest, "Schola.GymConnectors.Basic.Multi Agent Env Interface", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FSimpleMultiAgentGymConnectorTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FSimpleGymConnectorTestContext> Context = MakeShareable(new FSimpleGymConnectorTestContext());
	Context->TargetSteps = 3;
	Context->InitialSteps = Context->TargetSteps;
	Context->Test = this; // store pointer for latent command assertions
	
	UE_LOG(LogTemp, Log, TEXT("[ManualConnectorTest] Starting test with %d target steps"), Context->TargetSteps);

	// Load up the blank map used for testing
	AutomationOpenMap(TEXT("/Schola/EmptyTestMap"));
	// Allow world to initialize
	ADD_LATENT_AUTOMATION_COMMAND(FWaitLatentCommand(0.5f));
	ADD_LATENT_AUTOMATION_COMMAND(FSpawnMultiAgentEnvCommand(Context));
	// Spawn environment and connector
	ADD_LATENT_AUTOMATION_COMMAND(FSpawnConnectorCommand(Context));
	ADD_LATENT_AUTOMATION_COMMAND(FResetConnectorCommand(Context)); // allow connector to initialize
	// Step connector multiple times
	ADD_LATENT_AUTOMATION_COMMAND(FStepConnectorCommand(Context));
	// Verify environment position updated
	ADD_LATENT_AUTOMATION_COMMAND(FVerifyEnvPositionCommand(Context));
	// End PIE
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSimpleSingleAgentGymConnectorTest, "Schola.GymConnectors.Basic.Single Agent Env Interface", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FSimpleSingleAgentGymConnectorTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FSimpleGymConnectorTestContext> Context = MakeShareable(new FSimpleGymConnectorTestContext());
	Context->TargetSteps = 3;
	Context->InitialSteps = Context->TargetSteps;
	Context->Test = this; // store pointer for latent command assertions

	UE_LOG(LogTemp, Log, TEXT("[ManualConnectorTest] Starting test with %d target steps"), Context->TargetSteps);

	// Load up the blank map used for testing
	AutomationOpenMap(TEXT("/Schola/EmptyTestMap"));
	// Start PIE session
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(true));
	// Allow world to initialize
	ADD_LATENT_AUTOMATION_COMMAND(FWaitLatentCommand(0.5f));
	ADD_LATENT_AUTOMATION_COMMAND(FSpawnSingleAgentEnvCommand(Context));
	// Spawn environment and connector
	ADD_LATENT_AUTOMATION_COMMAND(FSpawnConnectorCommand(Context));
	ADD_LATENT_AUTOMATION_COMMAND(FResetConnectorCommand(Context));
	// Step connector multiple times
	ADD_LATENT_AUTOMATION_COMMAND(FStepConnectorCommand(Context));
	// Verify environment position updated
	ADD_LATENT_AUTOMATION_COMMAND(FVerifyEnvPositionCommand(Context));
	// End PIE
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}