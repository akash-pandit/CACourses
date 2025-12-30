# ETL Pipeline

A series of scripts that process a local copy of ASSIST.org's articulations into a PostgreSQL database. Currently, this is 3,314 nested JSON files summing up to ~2.7 Gigabytes of data. A scrappy version thrown together via `glossary_to_db.ipynb` generated the first copy of the db for a MVP, and a more stable, 'production-grade' variant is currently under development.