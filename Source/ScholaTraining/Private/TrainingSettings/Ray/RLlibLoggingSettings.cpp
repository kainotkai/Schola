// Copyright (c) 2024-2025 Advanced Micro Devices, Inc. All Rights Reserved.

#pragma once
#include "TrainingSettings/Ray/RLlibLoggingSettings.h"

void FRLlibLoggingSettings::GenerateTrainingArgs(FScriptArgBuilder& ArgBuilder) const
{
	ArgBuilder.AddIntArg(TEXT("logging-settings.schola-verbosity"), EnvLoggingVerbosity);
	ArgBuilder.AddIntArg(TEXT("logging-settings.rllib-verbosity"), TrainerLoggingVerbosity);
}

FRLlibLoggingSettings::~FRLlibLoggingSettings()
{
    
}