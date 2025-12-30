#!/usr/bin/env python

from dotenv import load_dotenv
import logging
import os
from pathlib import Path
import polars as pl
# from sqlalchemy import 

from utils.generate_schema import load_full_schema


def create_glossary_lazy(fp: Path, schema: pl.Schema) -> pl.LazyFrame:
    uni = int(fp.parts[-2])
    cc  = int(fp.parts[-1].split('to')[0])

    lf = pl.read_json(source=fp, schema=schema).lazy()

    if "prefixes" in str(fp):
        lf = lf.explode("articulations").rename({"articulations": "articulation"})

    # utility functions
    def coalesce_courses(field: str):
        return pl.coalesce([
            pl.col("uni_courses").struct.field(field),
            pl.col("uni_series_courses").struct.field(field)
        ])
    
    def concat_coalesce_courses(*fields):
        return pl.coalesce([
            pl.concat_str([pl.col("uni_series_courses").struct.field(f) for f in fields], separator=" "),
            pl.concat_str([pl.col("uni_courses").struct.field(f) for f in fields], separator=" ")
        ])

    return (
        lf.select(
            uni_courses=pl.col("articulation").struct.field("course"),
            uni_series_courses=pl.col("articulation").struct.field("series").struct.field("courses")
        )
        .explode("uni_series_courses")
        .select(
            courses=pl.struct(
                course_id=coalesce_courses("courseIdentifierParentId"),
                course_code=concat_coalesce_courses("prefix", "courseNumber"),
                course_title=coalesce_courses("courseTitle"),
                min_units=coalesce_courses("minUnits"),
                max_units=coalesce_courses("maxUnits"),
                begin=coalesce_courses("begin"),
                end=coalesce_courses("end")
            )
        ).unnest("courses")
        .unique()
    ).with_columns(cc=pl.lit(cc), uni=pl.lit(uni))


def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("agreements_to_db")

    # file paths
    PROJECTDIR = Path("/home/akash/Main/projects/CACourses")
    DATA_DIR = PROJECTDIR/"data"
    ETL_DIR = PROJECTDIR/"etl_pipeline"
    schema_prefix_fp = ETL_DIR / "schemas/schema_prefix.pickle"
    schema_major_fp = ETL_DIR / "schemas/schema_major.pickle"
    
    # get environment variables
    load_dotenv(dotenv_path=ETL_DIR/".env")
    psql_user =   os.getenv("LOCALDB_USER")
    psql_pwd =    os.getenv("LOCALDB_PWD")
    psql_dbname = os.getenv("LOCALDB_NAME")
    db_url = f"postgresql+psycopg2://{psql_user}:{psql_pwd}@localhost:5432/{psql_dbname}"
    # logger.debug(f"db url: {db_url}")

    # load schema for prefix-based data
    schema_prefix = load_full_schema(
        schema_fp=schema_prefix_fp,
        data_dir=DATA_DIR,
        data_glob="*/*prefixes.json",
        logger=logger
    )

    # load schema for major-based data
    schema_major = load_full_schema(
        schema_fp=schema_major_fp,
        data_dir=DATA_DIR,
        data_glob="*/*majors.json",
        logger=logger
    )