#!/usr/bin/env python

import os

from dotenv import load_dotenv

from .paths import ETL_DIR

load_dotenv(dotenv_path=ETL_DIR/".env")
psql_user =   os.getenv("POSTGRES_USER")
psql_pwd =    os.getenv("POSTGRES_PWD")
psql_host =   os.getenv("POSTGRES_HOSTNAME")
psql_port =   os.getenv("POSTGRES_PORT")
psql_dbname = os.getenv("POSTGRES_DBNAME")
PSQL_URL = f"postgresql://{psql_user}:{psql_pwd}@{psql_host}:{psql_port}/{psql_dbname}"