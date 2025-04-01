// Copyright (c) 2023-2024 Advanced Micro Devices, Inc. All Rights Reserved.

#pragma once

#include "Common/Points/BoxPoint.h"
#include "Common/Points/DiscretePoint.h"
#include "Common/Points/BinaryPoint.h"

/**
 * @brief A base class for objects that can operate on any point. This is used to implement the visitor pattern
 */
class PointVisitor
{
public:
	virtual void Visit(FBinaryPoint& Point) = 0;

	virtual void Visit(FDiscretePoint& Point) = 0;

	virtual void Visit(FBoxPoint& Point) = 0;

};
/**
 * @brief A base class for objects that can operate on any const point. This is used to implement the visitor pattern
 */
class ConstPointVisitor
{
public:
	virtual void Visit(const FBinaryPoint& Point) = 0;

	virtual void Visit(const FDiscretePoint& Point) = 0;

	virtual void Visit(const FBoxPoint& Point) = 0;

};
