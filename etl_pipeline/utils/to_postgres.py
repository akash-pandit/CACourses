#!/usr/bin/env python

from adbc_driver_postgresql import dbapi
import polars as pl


def write_articulations_to_psql(agreements: pl.DataFrame, db_url: str) -> None:
    tablename = "articulations"

    agreements = agreements.cast({
        "course_id": pl.Int32,
        "cc": pl.Int16,
        "uni": pl.Int16,
        "articulation": pl.String
    })

    with dbapi.connect(db_url) as conn:
        with conn.cursor() as cur:
            
            cur.execute(f"DROP TABLE IF EXISTS {tablename};")
            cur.execute(f"""
                CREATE TABLE {tablename} (
                    course_id INT4 NOT NULL,
                    cc INT2 NOT NULL,
                    uni INT2 NOT NULL,
                    articulation TEXT NOT NULL,
                    PRIMARY KEY (course_id, cc, uni)
                );
            """)
        conn.commit()
    
    agreements.write_database(
        table_name=tablename,
        connection=db_url,
        if_table_exists="append",
        engine="adbc"
    )


def write_glossary_to_psql(glossary: pl.DataFrame, db_url: str) -> None:
    tablename = "glossary"

    glossary = glossary.select([
        "course_id",
        "inst_id",
        "course_code",
        "course_name",
        "min_units",
        "max_units"
    ]).cast({
        "course_id": pl.Int32,
        "inst_id": pl.Int16,
        "course_code": pl.String,
        "course_name": pl.String,
        "min_units": pl.Float32,
        "max_units": pl.Float32
    })

    with dbapi.connect(uri=db_url) as conn:
        with conn.cursor() as cur:

            cur.execute(f"DROP TABLE IF EXISTS {tablename};")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {tablename} (
                    course_id INT4 PRIMARY KEY,
                    inst_id INT2 NOT NULL,
                    course_code TEXT NOT NULL,
                    course_name TEXT NOT NULL,
                    min_units REAL NOT NULL,
                    max_units REAL NOT NULL
                );
            """)
        conn.commit()

    glossary.write_database(
        table_name=tablename,
        connection=db_url,
        if_table_exists="append",
        engine="adbc"
    )
