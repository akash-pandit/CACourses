#!/usr/bin/env python

import logging

import polars as pl
from utils import create_glossary, load_full_schema, timer, write_glossary_to_psql
from utils.env import PSQL_URL
from utils.paths import DATA_DIR, SCHEMA_MAJOR_FP, SCHEMA_PREFIX_FP

"""
Query a local copy of the 2024-2025 ASSIST.org articulations and
build a reference glossary of every mentioned course by course id
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agreements_to_db")


@timer(label="Glossary to DB", logger=logger, level=logging.INFO)
def main():

    # 1. get polars schemas

    with timer("Load schemas", logger=logger, level=logging.INFO):
        schema_prefix = load_full_schema(
            schema_fp=SCHEMA_PREFIX_FP,
            data_dir=DATA_DIR,
            data_glob="*/*prefixes.json",
            logger=logger,
        )

        # load schema for major-based data
        schema_major = load_full_schema(
            schema_fp=SCHEMA_MAJOR_FP,
            data_dir=DATA_DIR,
            data_glob="*/*majors.json",
            logger=logger,
        )

    # 2. Extract & concatenate glossary dataframes

    with timer("Extract & Concat DFs", logger):
        prefixes_agg = pl.concat(
            (
                create_glossary(fp=fp, schema=schema_prefix)
                for fp in DATA_DIR.glob("*/*prefixes.json")
            )
        ).unique()
        majors_agg = pl.concat(
            (
                create_glossary(fp=fp, schema=schema_major)
                for fp in DATA_DIR.glob("*/*majors.json")
            )
        ).unique()

        qmap = {"W": 1, "S": 2, "Su": 3, "F": 4}

        courses = (
            pl.concat((prefixes_agg, majors_agg), rechunk=True)
            .unique()
            .with_columns(
                eterm=(
                    pl.col("end").replace("", None).str.slice(-4).cast(pl.UInt16) * 10
                    + pl.col("end")
                    .replace("", None)
                    .str.head(-4)
                    .replace_strict(qmap, return_dtype=pl.UInt16)
                ).fill_null(99999)
            )
            .sort("eterm", descending=True)
            .drop("begin", "end", "eterm")
            .unique(subset=["course_id"], keep="first")
            .unique(subset=["course_code", "inst_id"], keep="first")
        )
        logger.info(
            f" glossary DF estimated size: {courses.estimated_size('mb'):.2f} megabytes, {len(courses)} rows"
        )

        del prefixes_agg, majors_agg

    # 3. Write glossary to db

    with timer(label="Write to PgSQL", logger=logger, level=logging.INFO):
        write_glossary_to_psql(glossary=courses, db_url=PSQL_URL)


if __name__ == "__main__":
    main()
