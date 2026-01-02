import polars as pl
from pathlib import Path


def _coalesce_courses(field: str):
    return pl.coalesce([
        pl.col("uni_courses").struct.field(field),
        pl.col("uni_series_courses").struct.field(field)
        # pl.col("cc_courses")
    ])


def _concat_coalesce_courses(*fields):
    return pl.coalesce([
        pl.concat_str([pl.col("uni_series_courses").struct.field(f) for f in fields], separator=" "),
        pl.concat_str([pl.col("uni_courses").struct.field(f) for f in fields], separator=" ")
    ])


def create_glossary(fp: Path, schema: pl.Schema) -> pl.DataFrame:
    uni = int(fp.parts[-2])
    cc  = int(fp.parts[-1].split('to')[0])

    lf = pl.read_json(source=fp, schema=schema).lazy()

    if "prefix" in fp.name:
        lf = lf.explode("articulations").rename({"articulations": "articulation"})

    cc_courses = (
        lf
        .select(cc_courses=(
            pl.col("articulation")
            .struct.field("sendingArticulation")
            .drop_nulls()
            .struct.field("items")
            .explode()
            .struct.field("items")
            .explode()
        ))
        .select(
                course_id=pl.col("cc_courses").struct.field("courseIdentifierParentId"),
                course_code=pl.col("cc_courses").struct.field("prefix") + " " + pl.col("cc_courses").struct.field("courseNumber"),
                course_name=pl.col("cc_courses").struct.field("courseTitle"),
                min_units=pl.col("cc_courses").struct.field("minUnits"),
                max_units=pl.col("cc_courses").struct.field("maxUnits"),
                begin=pl.col("cc_courses").struct.field("begin"),
                end=pl.col("cc_courses").struct.field("end"),
                inst_id=pl.lit(cc)
        )
    )

    uni_courses = (
        lf
        .select(
            uni_courses=pl.col("articulation").struct.field("course"),
            uni_series_courses=pl.col("articulation").struct.field("series").struct.field("courses")
        )
        .explode("uni_series_courses")
        .select(
                course_id=_coalesce_courses("courseIdentifierParentId"),
                course_code=_concat_coalesce_courses("prefix", "courseNumber"),
                course_name=_coalesce_courses("courseTitle"),
                min_units=_coalesce_courses("minUnits"),
                max_units=_coalesce_courses("maxUnits"),
                begin=_coalesce_courses("begin"),
                end=_coalesce_courses("end"),
                inst_id=pl.lit(uni)
        )
    )

    return (
        pl.concat([cc_courses, uni_courses])
        .drop_nulls()
        .collect()
    )