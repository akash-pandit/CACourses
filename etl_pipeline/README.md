# ETL Pipeline

A series of scripts that process a local copy of ASSIST.org's articulations into a PostgreSQL database. Currently, this is 3,314 nested JSON files summing up to ~2.7 Gigabytes of data. A scrappy version thrown together via `glossary_to_db.ipynb` generated the first copy of the db for a MVP, and a more stable, 'production-grade' variant is currently under development.

## Installation

### Prerequisites
 * Python 3.12
 * The [uv](https://github.com/astral-sh/uv) package manager
   * Install on MacOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   * Install on Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex`
 * PostgreSQL (either a local instance or remote access)

### 1. Navigate to this directory
```bash
cd ./etl_pipeline
```
### 2. Set up `.env`
A `.env.template` file has been provided with all fields needed to fill in. Afterwards, copy it with the name `.env`.
```bash
cp .env.template .env
```
### 3. Sync dependencies and set up your virtual environment
```bash
uv sync
```
### 4. Running Scripts
Use `uv run` to execute scripts to ensure environment variables and dependencies are properly loaded. Main scripts follow a `{psql table-to-populate}_to_db.py` naming scheme.

#### NOTE: `etl_pipeline/` assumes a sister directory `data/`, containing articulation data at `data/{uni}/{cc}to{uni}-{majors,prefixes}.json`. To populate this, please run `download_data.py` in the project root.

```bash
uv run scripts/agreements_to_db.py
uv run scripts/glossary_to_db.py 
```
Each script logs execution metrics (elapsed time, dataframe size) via Python's logging library, you can capture these by redirecting `stderr` to a file or nullify them via `/dev/null`. e.g.
```bash
uv run scripts/agreements_to_db.py 2> agreements_to_db.log  # saves logging output to agreements_to_db.log
uv run scripts/glossary_to_db.py 2> /dev/null               # runs script quietly
```