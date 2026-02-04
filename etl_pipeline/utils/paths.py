#!/usr/bin/env python

from pathlib import Path

# common ETL pipeline paths

PROJECTDIR = Path("/home/akash/Main/projects/CACourses")
DATA_DIR = PROJECTDIR / "data"
ETL_DIR = PROJECTDIR / "etl_pipeline"
SCHEMA_PREFIX_FP = ETL_DIR / "schemas/schema_prefix.pickle"
SCHEMA_MAJOR_FP = ETL_DIR / "schemas/schema_major.pickle"
