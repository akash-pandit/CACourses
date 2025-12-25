#!/usr/bin/env python

import polars as pl
from functools import lru_cache

from pathlib import Path

from .utils.dnf_converter import to_dnf
from .utils.generate_schema import merge_schemas


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






