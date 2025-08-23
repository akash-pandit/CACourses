#!/usr/bin/python

import json
import os
import pandas as pd
import polars as pl

from collections import defaultdict
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

"""
Query a local copy of the 2024-2025 ASSIST.org articulation
agreements and write them to a local (testing) postgres database.
"""

def get_query(cc_id: int, uni_id: int) -> list[dict]:
    """
    fetch local copy of agreement
    
    - cc_id: internal ASSIST id for california community college
    - uni_id: internal ASSIST id for california public university

    returns:
    - python representation of JSON file (list of dicts)
    """
    with open(f"./data/{uni_id}/{cc_id}to{uni_id}.json", "r") as fp:
        out = json.load(fp)
    return out


def extract_articulations(cc: int, uni: int) -> pl.DataFrame:
    """
    Performs a series of polars dataframe transformations on query to
    assemble dataframe of articulations mapping uni courses to json relations
    of cc courses.

    Initially reads in df as pandas dataframe due to looser data structuring
    requirements, casts to polars dataframe, then applies series of vectorized
    transformations.

    - cc_id: internal ASSIST id for california community college
    - uni_id: internal ASSIST id for california public university

    returns:
    - polars dataframe with (uni course id: int, cc relation: json string) relation
    """

    # extract data from query & construct polars dataframe
    articulations: pl.DataFrame = pl.from_pandas(pd.DataFrame(get_query(cc, uni)))
    
    colname = "articulation"
    if "articulations" in articulations.columns:
        articulations = articulations.explode("articulations")
        colname = "articulations"
    articulations_struct = articulations.get_column(colname).struct

    articulations = pl.concat((
        articulations_struct.field("course").struct.field("courseIdentifierParentId").rename("course_id").to_frame(),
        articulations_struct.field("series").to_frame(),
        articulations_struct.field("sendingArticulation").to_frame()
    ), how="horizontal")
    
    articulations = articulations.with_columns(
        pl.lit(cc).alias("cc"),
        pl.lit(uni).alias("uni")
    )
    
    
    # transform into mapping of course id : relationship to course ids that articulate to it
    articulations = (
        articulations
        # extract courses from uni series objects and treat them as individual courses
        # premise: A and B articulates to C and D => A and B articulates to C and A and B articulates D
        .with_columns(pl.col("series").struct.field("courses"))
        .explode("courses")
        # extract sendingArticulation field (contains A and B) and id of C/D courses
        .with_columns(
            course_id=pl.coalesce(
                "course_id",
                pl.col("courses").struct.field("courseIdentifierParentId")
            ),
            items=(
                pl.when(pl.col("sendingArticulation").struct.field("items").list.len() > 0)
                .then(pl.col("sendingArticulation").struct.field("items"))
                .otherwise(None)
            )
        )
        # transform sendingArticulation to only keep course ids from whole course structs for C/D
        .with_columns(
            pl.col("items").list.eval(
                pl.struct([
                    pl.element().struct.field("courseConjunction").alias("conj"),
                    pl.element().struct.field("items").list.eval(
                        pl.element().struct.field("courseIdentifierParentId")
                    ).alias("items")
                ])#.struct.json_encode()  # uncomment to convert struct to json string
            )
        )
        # ensure AND groupings are grouped together by the proper group conjunction
        # with OR as the default if articulation exists else null
        .with_columns(
            pl.when(pl.col("items").is_not_null())
            .then(
                    pl.struct([
                    pl.when(
                        pl.col("sendingArticulation")
                        .struct.field("courseGroupConjunctions")
                        .list.len() > 0
                    )
                    .then(
                        pl.col("sendingArticulation")
                        .struct.field("courseGroupConjunctions")
                        .list.first()
                        .struct.field("groupConjunction")
                    )
                    .otherwise(pl.lit("Or"))
                    .alias("groupConj"),
                    
                    pl.col("items")
                ])
            )
            .otherwise(None)
        )
        # drop intermediary columns
        .drop(["series", "courses", "sendingArticulation", "items"])
    ).rename({"groupConj": "articulation"})
    
    return articulations


def aggregate_agreements(errored: defaultdict) -> pl.DataFrame:
    with open("./data/institutions_cc.json", "r") as cc_fp, open("./data/institutions_state.json", "r") as uni_fp:
        cc_ids = json.load(cc_fp).keys()
        uni_ids = json.load(uni_fp).keys()
    
    articulations = []
    for uni in uni_ids:
        for cc in cc_ids:
            if not os.path.exists(f"./data/{uni}/{cc}to{uni}.json"):
                continue
            try:
                articulations.append(extract_articulations(int(cc), int(uni)))
            except Exception:
                errored[uni].append(cc)
        print(f"Extracted articulations for {uni=}")
    with open("data/known_errors_agreements.json", "w") as fp:
        json.dump(errored, fp, indent=2)
    return pl.concat(articulations)


def process_agreements(agreements: pl.DataFrame) -> pl.DataFrame:
    filtered = agreements.drop_nulls().unique()
    return (
        filtered
        .with_columns(gc=pl.col("articulation").struct.field("groupConj"))  # get group conjunction
        .group_by(['course_id', 'cc', 'uni'])
        .all()  # collapse multiple articulations per agreement into 1 entry
        .with_columns(articulation=pl.struct(superConj=pl.lit("Or"), items=pl.col("articulation")))
        # recreate articulation entry
        .drop("gc")
    )


def write_to_db(agreements: pl.DataFrame) -> None:
    user =   os.environ["LOCALDB_USER"]
    pwd =    os.environ["LOCALDB_PWD"]
    dbname = os.environ["LOCALDB_NAME"]

    db_url = f"postgresql+psycopg2://{user}:{pwd}@localhost:5432/{dbname}"
    engine = create_engine(db_url)

    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS articulations;"))
        conn.execute(text("""
            CREATE TABLE articulations(
                course_id INT4 NOT NULL,
                cc INT2 NOT NULL,
                uni INT2 NOT NULL,
                articulation JSON NOT NULL,
                PRIMARY KEY (course_id, cc, uni)
            );
        """))

        agreements.write_database(
            table_name="articulations",
            connection=conn,
            if_table_exists="append",
            engine="sqlalchemy"
        )


def main():
    errored_agreements = defaultdict(list)
    raw_agreements = aggregate_agreements(errored_agreements)
    print("Raw agreements queried")
    processed_agreements = process_agreements(raw_agreements)
    print("Agreements processed")

    if load_dotenv():
        write_to_db(processed_agreements)
        print("Agreements written to db")


if __name__ == "__main__":
    main()
