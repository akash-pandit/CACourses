#!/usr/bin/env python

import polars as pl
import itertools
from functools import lru_cache

from pathlib import Path

"""
Query a local copy of the 2024-2025 ASSIST.org articulation
agreements and write them to a local (testing) postgres database.
"""

def extract_articulations(fp: Path, schema: pl.Schema | None) -> pl.DataFrame:
    uni = int(fp.parts[-2])
    cc  = int(fp.parts[-1].split('to')[0])

    lf = pl.read_json(source=fp, schema=schema).lazy()

    # Normalize structure (Explode list vs Rename single)
    if "prefixes" in str(fp):
        lf = lf.explode("articulations")
    else:
        lf = lf.rename({"articulation": "articulations"})

    return (
        lf
        # 1. Filter empty articulations immediately
        .filter(
            pl.col("articulations")
            .struct.field("sendingArticulation")
            .struct.field("items")
            .list.len() > 0
        )
        # 2. Extract Fields & Merge Source IDs
        .select(
            # Extract Series IDs (List[Int]) and Single IDs (Int)
            series_ids=pl.col("articulations").struct.field("series").struct.field("courses")
                     .list.eval(pl.element().struct.field("courseIdentifierParentId")),
            
            root_id=pl.col("articulations").struct.field("course").struct.field("courseIdentifierParentId"),

            # Extract Destination Data
            sending_items=pl.col("articulations").struct.field("sendingArticulation").struct.field("items"),
            
            # Global Conjunction
            global_conj=(
                pl.col("articulations")
                .struct.field("sendingArticulation")
                .struct.field("courseGroupConjunctions")
                .list.first()
                .struct.field("groupConjunction")
                .fill_null("Or")
            )
        )
        # 3. Safe Explode Logic
        # Coalesce series list with root_id (wrapped in a list) so we never drop rows
        .with_columns(
            source_id_list=pl.coalesce(
                pl.col("series_ids"), 
                pl.concat_list(pl.col("root_id")) 
            )
        )
        .explode("source_id_list") # Now safe to explode
        
        # 4. Final Construction
        .select(
            cc=pl.lit(cc),
            uni=pl.lit(uni),
            course_id=pl.col("source_id_list"),
            articulation=pl.struct(
                conj=pl.col("global_conj"),
                items=pl.col("sending_items").list.eval(
                    pl.struct(
                        conj=pl.element().struct.field("courseConjunction"),
                        items=pl.element().struct.field("items").list.eval(
                            pl.element().struct.field("courseIdentifierParentId")
                        )
                    )
                )
            )
        )
        .group_by(
            pl.col("course_id"),
            pl.col("cc"),
            pl.col("uni")
        ).all()
        .select(
            course_id=pl.col("course_id"),
            cc=pl.col("cc"),
            uni=pl.col("uni"),
            articulation=pl.struct(
                conj=pl.lit("Or"),
                items=pl.col("articulation")
            )
        )
        .collect()
    )




@lru_cache(maxsize=128)
def _resolve_supertype(dtype1: pl.DataType, dtype2: pl.DataType) -> pl.DataType:
    """
    Caches the expensive supertype resolution.
    This bypasses creating dummy Series for repetitive primitive merges
    (e.g., merging Int64 and Float64 thousands of times).
    """
    try:
        # diagonal_relaxed allows Polars to determine the common supertype
        return pl.concat(
            [pl.Series([None], dtype=dtype1), pl.Series([None], dtype=dtype2)],
            how="diagonal_relaxed",
        ).dtype
    except Exception:
        raise TypeError(f"Could not merge incompatible types: {dtype1} and {dtype2}")
    return


def _merge_dtypes_optimized(dtype1: pl.DataType, dtype2: pl.DataType) -> pl.DataType:
    """Optimized recursive merge."""
    # 1. Identity Check (Fastest exit)
    if dtype1 == dtype2:
        return dtype1

    # 2. Null Handling
    if isinstance(dtype1, pl.Null): return dtype2
    if isinstance(dtype2, pl.Null): return dtype1

    # 3. Recursive List Merge
    if isinstance(dtype1, pl.List) and isinstance(dtype2, pl.List):
        return pl.List(_merge_dtypes_optimized(dtype1.inner, dtype2.inner))

    # 4. Recursive Struct Merge
    if isinstance(dtype1, pl.Struct) and isinstance(dtype2, pl.Struct):
        # Convert both to dictionaries once
        f1 = dtype1.to_schema()
        f2 = dtype2.to_schema()
        
        # Start with f1's fields
        merged_fields = f1.copy()
        
        # Only iterate over fields in f2
        for key, type2 in f2.items():
            type1 = merged_fields.get(key)
            if type1 is not None:
                # Recursively merge only if types differ
                if type1 != type2:
                    merged_fields[key] = _merge_dtypes_optimized(type1, type2)
            else:
                # New field from f2
                merged_fields[key] = type2
        
        return pl.Struct(merged_fields)

    # 5. Cached Primitive Resolution
    # We use the cached function for scalar types (Int, Float, String, etc.)
    return _resolve_supertype(dtype1, dtype2)


def merge_schemas(schemas: list[pl.Schema]) -> pl.Schema:
    """
    Optimized schema merging.
    """
    if not schemas:
        return pl.Schema()

    current_schema_map = dict(schemas[0])

    for schema in schemas[1:]:
        # Iterate only over the new schema's items
        for field_name, new_dtype in schema.items():
            existing_dtype = current_schema_map.get(field_name)
            
            if existing_dtype is None:
                # Fast path: New field
                current_schema_map[field_name] = new_dtype
            elif existing_dtype != new_dtype:
                # Slow path: Conflict resolution
                current_schema_map[field_name] = _merge_dtypes_optimized(existing_dtype, new_dtype)
    
    return pl.Schema(current_schema_map)


