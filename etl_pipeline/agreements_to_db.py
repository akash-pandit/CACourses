#!/usr/bin/env python

from dotenv import load_dotenv
import logging
import os
import polars as pl
from pathlib import Path
import pickle
from sqlalchemy import text, create_engine, JSON

from utils.dnf_converter import to_dnf
from utils.generate_schema import merge_schemas


"""
Query a local copy of the 2024-2025 ASSIST.org articulation
agreements and write them to a local (testing) postgres database.
"""

def extract_articulations(fp: Path, schema: pl.Schema) -> pl.DataFrame:
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
        .collect()
    )


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


def main() -> None:
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
    if schema_prefix_fp.exists():
        logger.info("Loading precomputed schema for prefix-based articulations")
        with schema_prefix_fp.open(mode='rb') as fp:
            schema_prefix: pl.Schema = pickle.load(file=fp)
    else:
        logger.info("Precomputed prefix schema not found, inferring from data")
        schema_list_prefix = [pl.read_json(fp, infer_schema_length=None).schema for fp in DATA_DIR.glob("*/*prefixes.json")]
        schema_prefix = merge_schemas(schemas=schema_list_prefix)
        with schema_prefix_fp.open(mode='wb') as fp:
            pickle.dump(obj=schema_prefix, file=fp)

    # load schema for major-based data
    if schema_major_fp.exists():
        logger.info("Loading precomputed schema for major-based articulations")
        with schema_major_fp.open(mode='rb') as fp:
            schema_major: pl.Schema = pickle.load(file=fp)
    else:
        logger.info("Precomputed major schema not found, inferring from data")
        schema_list_major  = [pl.read_json(fp, infer_schema_length=None).schema for fp in DATA_DIR.glob("*/*majors.json")]
        schema_major  = merge_schemas(schema_list_major)
        with schema_major_fp.open(mode="wb") as fp:
            pickle.dump(obj=schema_major, file=fp)


    # extract articulations
    logger.info("Extracting articulations")
    prefixes_agg = [
        extract_articulations(fp=fp, schema=schema_prefix)
        .with_columns(
            pl.col("articulation")
            .map_elements(to_dnf, return_dtype=pl.Struct)
        )
        for fp in DATA_DIR.glob("*/*prefixes.json")
    ]
    majors_agg = [
        extract_articulations(fp=fp, schema=schema_major)
        .with_columns(
            pl.col("articulation")
            .map_elements(to_dnf, return_dtype=pl.Struct)
        )
        for fp in DATA_DIR.glob("*/*majors.json")
    ]
    articulations = pl.concat(prefixes_agg + majors_agg).with_columns(
        pl.col("articulation")
        .struct.json_encode()
    )

    # write articulations to database
    logger.info("Writing articulations to database")
    write_to_db(
        agreements=articulations,
        db_url=db_url
    )
    logger.info("Transaction complete")
    return

    
if __name__ == "__main__":
    main()
