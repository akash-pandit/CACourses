#!/usr/bin/env python

import logging
import os
from pathlib import Path
import polars as pl
# from sqlalchemy import 

from utils import (
    create_glossary,
    load_full_schema,
    timer,
    write_glossary_to_psql
)

"""
Query a local copy of the 2024-2025 ASSIST.org articulations and
build a reference glossary of every mentioned course by course id
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agreements_to_db")


@timer(label="Glossary to DB", logger=logger, level=logging.INFO)
def main():

    # 1. Load relevant variables

    PROJECTDIR = Path("/home/akash/Main/projects/CACourses")
    DATA_DIR = PROJECTDIR/"data"
    ETL_DIR = PROJECTDIR/"etl_pipeline"
    schema_prefix_fp = ETL_DIR / "schemas/schema_prefix.pickle"
    schema_major_fp = ETL_DIR / "schemas/schema_major.pickle"
    
    # get environment variables
    psql_user =   os.getenv("POSTGRES_USER")
    psql_pwd =    os.getenv("POSTGRES_PWD")
    psql_host =   os.getenv("POSTGRES_HOSTNAME")
    psql_port =   os.getenv("POSTGRES_PORT")
    psql_dbname = os.getenv("POSTGRES_DBNAME")
    psql_url = f"postgresql://{psql_user}:{psql_pwd}@{psql_host}:{psql_port}/{psql_dbname}"
    
    # 2. get polars schemas

    with timer("Load schemas", logger=logger, level=logging.INFO):
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

    # 3. Extract & concatenate glossary dataframes
    
    with timer("Extract & Concat DFs", logger):
        prefixes_agg = pl.concat(
            (create_glossary(fp=fp, schema=schema_prefix) for fp in DATA_DIR.glob("*/*prefixes.json"))
        ).unique()
        majors_agg = pl.concat(
            (create_glossary(fp=fp, schema=schema_major) for fp in DATA_DIR.glob("*/*majors.json"))
        ).unique()
        
        qmap = {'W': 1, 'S': 2, 'Su': 3, 'F': 4}

        courses = (
            pl.concat((prefixes_agg, majors_agg), rechunk=True)
            .unique()
            .with_columns(
                eterm=(
                    pl.col("end").replace("", None).str.slice(-4).cast(pl.UInt16) * 10 +
                    pl.col("end").replace("", None).str.head(-4).replace_strict(qmap, return_dtype=pl.UInt16)
                )
                .fill_null(99999)
            )
            .sort("eterm", descending=True)
            .drop("begin", "end", "eterm")
            .unique(subset=["course_id"], keep="first")
        )
        logger.info(f" glossary DF estimated size: {courses.estimated_size("mb"):.2f} megabytes, {len(courses)} rows")
        
        del prefixes_agg, majors_agg

    # 4. Write glossary to db

    with timer(label="Write to PgSQL", logger=logger, level=logging.INFO):
        write_glossary_to_psql(
            glossary=courses,
            db_url=psql_url
        )


if __name__ == "__main__":
    main()
