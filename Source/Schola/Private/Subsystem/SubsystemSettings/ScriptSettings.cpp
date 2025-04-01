// Copyright (c) 2024-2025 Advanced Micro Devices, Inc. All Rights Reserved.

#pragma once
#include "Subsystem/SubsystemSettings/ScriptSettings.h"

inline FString WithQuotes(FString Input)
{
	return FString("\"") + Input + FString("\"");
}

FString FScriptSettings::GetTrainingArgs(int Port) const
{
	FScriptArgBuilder ArgBuilder = FScriptArgBuilder();
	switch (ScriptType)
	{
		case (EScriptType::Python):
			switch (PythonScriptType)
			{
				case (EPythonScript::SB3):
					this->SB3Settings.GenerateTrainingArgs(Port, ArgBuilder);
					break;
				case (EPythonScript::RLLIB):
					this->RLlibSettings.GenerateTrainingArgs(Port, ArgBuilder);
					break;
				default:
					this->CustomPythonScriptSettings.GenerateTrainingArgs(Port, ArgBuilder);
					break;
			}
			break;

		default:
			this->CustomScriptSettings.GenerateTrainingArgs(Port, ArgBuilder);
			break;
	}
	return ArgBuilder.Build();
}

FFilePath FScriptSettings::GetScriptPath() const
{
	switch (ScriptType)
	{
		case (EScriptType::Python):
			switch (PythonScriptType)
			{
				case (EPythonScript::SB3):
					return FFilePath{ IPluginManager::Get().FindPlugin(TEXT("Schola"))->GetBaseDir() + FString("/Resources/python/schola/scripts/sb3/launch.py") };

				case (EPythonScript::RLLIB):
					return FFilePath{ IPluginManager::Get().FindPlugin(TEXT("Schola"))->GetBaseDir() + FString("/Resources/python/schola/scripts/ray/launch.py") };

				default:
					return CustomPythonScriptSettings.LaunchScript;
			}

		default:
			return CustomScriptSettings.LaunchScript;
	}
}

FLaunchableScript FScriptSettings::GetLaunchableScript() const
{
	switch (ScriptType)
	{
		case (EScriptType::Python):
			switch (EnvType)
			{
				case (EPythonEnvironmentType::Conda):
					return FLaunchableScript(FString("conda"), FString("run --live-stream -n ") + this->CondaEnvName + FString(" python ") + WithQuotes(this->GetScriptPath().FilePath));

				case (EPythonEnvironmentType::VEnv):
					return FLaunchableScript(this->CustomPythonPath.FilePath, WithQuotes(this->GetScriptPath().FilePath));

				case (EPythonEnvironmentType::SystemPath):
					return FLaunchableScript(FString("python"), WithQuotes(this->GetScriptPath().FilePath));

				default:
					EnsureScholaIsInstalled();
					return FLaunchableScript(GetBuiltInPythonPath(), WithQuotes(this->GetScriptPath().FilePath));
			}

		default:
			return FLaunchableScript(this->GetScriptPath().FilePath);
	}
}

FString FScriptSettings::GetBuiltInPythonPath() const
{
#if PLATFORM_WINDOWS
	return FPaths::Combine(FPaths::EngineDir(), TEXT("Binaries/ThirdParty/Python3/Win64/python.exe"));
#elif PLATFORM_MAC
	return FPaths::Combine(FPaths::EngineDir(), TEXT("Binaries/ThirdParty/Python3/Mac/bin/python3"));
#elif PLATFORM_LINUX
	return FPaths::Combine(FPaths::EngineDir(), TEXT("Binaries/ThirdParty/Python3/Linux/bin/python3"));
#else
	UE_LOG(LogSchola, Warning, TEXT("Unsupported platform, defaulting to Linux Python path"));
	return FPaths::Combine(FPaths::EngineDir(), TEXT("Binaries/ThirdParty/Python3/Linux/bin/python3"));
#endif
}

void FScriptSettings::EnsureScholaIsInstalled() const
{
	FString PythonPath = GetBuiltInPythonPath();
	int32 ReturnCode;
	FString StdOut;
	FString StdErr;
	FPlatformProcess::ExecProcess(*PythonPath, TEXT("-m pip show schola"), &ReturnCode, &StdOut, &StdErr);

	// if not installed, install it
	if (ReturnCode != 0)
	{
		FString Command = FString::Printf(TEXT("-m pip install %s[all]"), *(*IPluginManager::Get().FindPlugin(TEXT("Schola"))->GetBaseDir() + FString("/Resources/python")));
		FPlatformProcess::ExecProcess(*PythonPath, *Command, &ReturnCode, &StdOut, &StdErr);
		if (ReturnCode != 0)
		{
			UE_LOG(LogSchola, Error, TEXT("Failed to install Schola python package: %s \n%s"), *StdOut, *StdErr);
		} else{
			UE_LOG(LogSchola, Log, TEXT("Installed Schola python package"));
		}	
	}
}

FScriptSettings::~FScriptSettings()
{
}