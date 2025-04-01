// Copyright (c) 2023-2024 Advanced Micro Devices, Inc. All Rights Reserved.

#include "Common/Points/BoxPoint.h"
#include "Common/Points/PointVisitor.h"

void FBoxPoint::Accept(PointVisitor& Visitor)
{
	Visitor.Visit(*this);
}

void FBoxPoint::Accept(ConstPointVisitor& Visitor) const
{
	Visitor.Visit(*this);
}