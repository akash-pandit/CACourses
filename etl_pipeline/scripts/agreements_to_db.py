#!/usr/bin/env python

from dotenv import load_dotenv
import logging
import os
import polars as pl
from pathlib import Path
from sqlalchemy import text, create_engine, JSON

from utils import (
    extract_articulations_lazy,
    load_full_schema,
    to_dnf,
    timer
)

"""
Query a local copy of the 2024-2025 ASSIST.org articulation
agreements and write them to a local (testing) postgres database.
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agreements_to_db")


def write_to_db(agreements: pl.DataFrame, db_url: str) -> None:
    
    engine = create_engine(db_url)

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS articulations;"))
        conn.execute(text("""
            CREATE TABLE articulations(
                course_id INT4 NOT NULL,
                cc INT2 NOT NULL,
                uni INT2 NOT NULL,
                articulation JSONB NOT NULL,
                PRIMARY KEY (course_id, cc, uni)
            );
        """))

        agreements.write_database(
            table_name="articulations",
            connection=conn,
            if_table_exists="append",
            engine="sqlalchemy",
            engine_options={"dtype": {"articulation": JSON}}
        )


@timer(label="Agreements to DB", logger=logger, level=logging.INFO)
def main() -> None:
    
    # 1. Load relevant variables

    PROJECTDIR = Path("/home/akash/Main/projects/CACourses")
    DATA_DIR = PROJECTDIR/"data"
    ETL_DIR = PROJECTDIR/"etl_pipeline"
    schema_prefix_fp = ETL_DIR / "schemas/schema_prefix.pickle"
    schema_major_fp = ETL_DIR / "schemas/schema_major.pickle"
    
    load_dotenv(dotenv_path=ETL_DIR/".env")
    psql_user =   os.getenv("POSTGRES_USER")
    psql_pwd =    os.getenv("POSTGRES_PWD")
    psql_host =   os.getenv("POSTGRES_HOSTNAME")
    psql_port =   os.getenv("POSTGRES_PORT")
    psql_dbname = os.getenv("POSTGRES_DBNAME")
    psql_url = f"postgresql+psycopg://{psql_user}:{psql_pwd}@{psql_host}:{psql_port}/{psql_dbname}"

    # 2. get polars schemas

    with timer("Load schemas", logger=logger, level=logging.INFO):
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

    # 3. Extract Articulations as LazyFrames

    with timer(label="LF Extraction", logger=logger, level=logging.INFO):
        prefixes_lazy = (
            pl.concat((
                extract_articulations_lazy(fp=fp, schema=schema_prefix) 
                for fp in DATA_DIR.glob("*/*prefixes.json")
            ))
            .with_columns(pl.col("articulation").map_elements(to_dnf, return_dtype=pl.String))
        )

        majors_lazy = (
            pl.concat((
                extract_articulations_lazy(fp=fp, schema=schema_major ) 
                for fp in DATA_DIR.glob("*/*majors.json")
            ))
            .with_columns(pl.col("articulation").map_elements(to_dnf, return_dtype=pl.String))
        )

    # 4. Collect Articulations
    
    with timer(label="LF Collection", logger=logger, level=logging.INFO):
        articulations = pl.concat((prefixes_lazy, majors_lazy)).unique().collect()
        logger.info(f" articulations DF estimated size: {articulations.estimated_size("mb"):.2f} megabytes, {len(articulations)} rows")

        del prefixes_lazy, majors_lazy

    # 5. Write articulations to database
    
    with timer(label="Write to PgSQL", logger=logger, level=logging.INFO):
        write_to_db(
            agreements=articulations,
            db_url=psql_url
        )
    return

    
if __name__ == "__main__":
    main()
