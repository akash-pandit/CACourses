#!/usr/bin/env python

import logging

import polars as pl
from utils import (
    extract_articulations_lazy,
    load_full_schema,
    timer,
    to_dnf,
    write_articulations_to_psql,
)
from utils.env import PSQL_URL
from utils.paths import DATA_DIR, SCHEMA_MAJOR_FP, SCHEMA_PREFIX_FP

"""
Query a local copy of the 2024-2025 ASSIST.org articulation
agreements and write them to a local (testing) postgres database.
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agreements_to_db")


@timer(label="Agreements to DB", logger=logger, level=logging.INFO)
def main() -> None:
    # 1. get polars schemas

    with timer("Load schemas", logger=logger, level=logging.INFO):
        # load schema for prefix-based data
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

    # 2. Extract Articulations as LazyFrames

    with timer(label="LF Extraction", logger=logger, level=logging.INFO):
        prefixes_lazy = pl.concat(
            (
                extract_articulations_lazy(fp=fp, schema=schema_prefix)
                for fp in DATA_DIR.glob("*/*prefixes.json")
            )
        ).with_columns(
            pl.col("articulation").map_elements(to_dnf, return_dtype=pl.String)
        )

        majors_lazy = pl.concat(
            (
                extract_articulations_lazy(fp=fp, schema=schema_major)
                for fp in DATA_DIR.glob("*/*majors.json")
            )
        ).with_columns(
            pl.col("articulation").map_elements(to_dnf, return_dtype=pl.String)
        )

    # 3. Collect Articulations

    with timer(label="LF Collection", logger=logger, level=logging.INFO):
        articulations = pl.concat((prefixes_lazy, majors_lazy)).unique().collect()
        logger.info(
            f" articulations DF estimated size: {articulations.estimated_size('mb'):.2f} megabytes, {len(articulations)} rows"
        )

        del prefixes_lazy, majors_lazy

    # 4. Write articulations to database

    with timer(label="Write to PgSQL", logger=logger, level=logging.INFO):
        write_articulations_to_psql(agreements=articulations, db_url=PSQL_URL)
    return


if __name__ == "__main__":
    main()
