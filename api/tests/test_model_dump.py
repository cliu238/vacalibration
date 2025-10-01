#!/usr/bin/env python3
"""Test how Pydantic serializes CalibrationRequest"""

import sys
sys.path.append('/Users/ericliu/projects5/vacalibration/api')

from app.main_direct import CalibrationRequest
import json

# Create request with same data
request = CalibrationRequest(
    data_source="sample",
    sample_dataset="comsamoz_broad",
    age_group="child",
    country="Mozambique",
    mmat_type="prior",
    ensemble=False,
    async_=False
)

# See what model_dump produces
dump = request.model_dump()
print("model_dump() output:")
print(json.dumps(dump, indent=2, default=str))

print("\n\nChecking age_group type:")
print(f"  Type: {type(dump['age_group'])}")
print(f"  Value: {dump['age_group']}")
print(f"  Repr: {repr(dump['age_group'])}")