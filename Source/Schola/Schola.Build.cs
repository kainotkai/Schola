// Copyright (c) 2025 Advanced Micro Devices, Inc. All Rights Reserved.

using UnrealBuildTool;

public class Schola : ModuleRules
{
    public Schola(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicIncludePaths.AddRange(new string[] { });

        PrivateIncludePaths.AddRange(new string[] { "Schola/Private"});

        PublicDependencyModuleNames.AddRange(new string[] {
            "Core",
            "InputCore",
            "AIModule",
            "Json", 
            "JsonUtilities",
        });

        PrivateIncludePathModuleNames.AddRange(new string[] { });
        PrivateDependencyModuleNames.AddRange(new string[] {
            "CoreUObject",
            "Engine",
            "Slate",
            "SlateCore",
            "Projects"
        });
        
        // BlueprintGraph is only needed for the editor so we can raise BlueprintErrors
        if (Target.bBuildEditor)
        {
            PrivateDependencyModuleNames.Add("BlueprintGraph");
        }
        
        DynamicallyLoadedModuleNames.AddRange(new string[] { });
    }
}
