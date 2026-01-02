#!/usr/bin/env python

import polars as pl
from pathlib import Path


def extract_articulations_lazy(fp: Path, schema: pl.Schema) -> pl.LazyFrame:
    uni = int(fp.parts[-2])
    cc  = int(fp.parts[-1].split('to')[0])

    lf = pl.read_json(source=fp, schema=schema).lazy()

    # Normalize structure (Explode list vs Rename single)
    if "prefixes" in str(fp):
        lf = lf.explode("articulations").rename({"articulations": "articulation"})

    return (
        lf
        .filter(  # 1. Filter empty articulations immediately
            pl.col("articulation")
            .struct.field("sendingArticulation")
            .struct.field("items")
            .list.len() > 0
        )
        .select(  # 2. Extract Fields & Merge Source IDs
            series_ids=(  # list of university course ids in series
                pl.col("articulation")
                .struct.field("series")
                .struct.field("courses")
                .list.eval(
                    pl.element()
                    .struct.field("courseIdentifierParentId")
                )
            ),
            root_id=(  # university course id for individual courses
                pl.col("articulation")
                .struct.field("course")
                .struct.field("courseIdentifierParentId")
            ),
            sending_items=(  # articulation data
                pl.col("articulation")
                .struct.field("sendingArticulation")
                .struct.field("items")
            ),
            global_conj=(
                pl.col("articulation")
                .struct.field("sendingArticulation")
                .struct.field("courseGroupConjunctions")
                .list.first()
                .struct.field("groupConjunction")
                .fill_null("Or")
            )
        )
        .unique()
        .with_columns(  # coalesce series + indiv course ids itno single column
            source_ids=pl.coalesce(
                pl.col("series_ids"), 
                pl.concat_list(pl.col("root_id")) 
            )
        )
        .explode("source_ids")
        .drop_nulls("source_ids")  # handle non-class requirements "need 1 literature class (pick 1 of any of these)"
        # 4. Final Construction
        .select(
            cc=pl.lit(cc),
            uni=pl.lit(uni),
            course_id=pl.col("source_ids"),
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
    )
