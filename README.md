# CACourses

**A tool for CA students to find the perfect course replacement.**

- [CACourses](#cacourses)
  - [Description](#description)
  - [Motivations](#motivations)
  - [Installation](#installation)
    - [1. Clone \& enter the repository](#1-clone--enter-the-repository)
    - [2. Navigate to the frontend directory](#2-navigate-to-the-frontend-directory)
    - [3. Run a web server at your local directory](#3-run-a-web-server-at-your-local-directory)
    - [Other Modules](#other-modules)
  - [Architecture](#architecture)
    - [The Database](#the-database)
    - [The Data](#the-data)
    - [The ETL Pipeline](#the-etl-pipeline)
    - [The Backend](#the-backend)
    - [The Frontend](#the-frontend)
  - [Future Plans](#future-plans)
  - [Known bugs](#known-bugs)

## Description

This tool makes convenient one relatively niche edge use-case for an already fantastic tool, [ASSIST.org](https://assist.org). ASSIST allows users within the California public higher education system, particularly community college students, to find out exactly which community college courses their target 4-year university (a CSU or UC campus) accept. 

However, there are cases where a student knows they want to meet a particular course, and they just want to find all of their options. Maybe their community college does not offer an articulated course, or maybe it's not offered for the term that's needed.

ASSIST.org does not allow to filter by class, making the search for a replacement a tedious process of checking each community college one-by-one.

This tool allows you to simply pick your university and the course you want to replace, and all your choices will be laid out in front of you.

## Motivations

This project has its roots in a hackathon project I tried a couple years ago, where the farthest we got was a script that populated a SQLite database. 

At the time, I wanted to transfer from UC Santa Cruz to UC San Diego, and vividly remembered my frustration in finding Java community college classes to enroll in due to the constant "Will this college have them? Seems not..". With this tool, my search would have been cut down from hours to minutes.

This project also serves as a playground for me to hone my actual software engineering chops -- web development & data engineering, pipelines for data that doesn't come from a single-cell experiment, unit testing, and cloud. While not currently in use, an earlier version of this project was my introduction to writing my own Dockerfiles. 

## Installation

Below are instructions to run a locally hosted version of the website.

### 1. Clone & enter the repository
```bash
git clone https://github.com/akash-pandit/CACourses.git
cd CACourses
```
### 2. Navigate to the frontend directory
```bash
cd frontend
```
### 3. Run a web server at your local directory
With Python, you can do so by running:
```bash
python -m http.server 8000
```
Which begins a web server at `https://localhost:8000`, which you can navigate to in a web browser of your choice. 

Other programs (e.g. Node) have their own conventions for doing so, so use whatever you are familiar with.

### Other Modules
For those interested in building/running other modules (backend, etl_pipeline, etc.), please reference the READMEs in your subdirectory of interest.

## Architecture

This app is most aptly described as a database-driven web application, or as I like to think of it: postgres-but-prettier. There are two main portions to this project: a pipeline that populates the database, and the web app itself

### The Database
The centerpiece of this app is a PostgreSQL database hosted via Supabase with 2 primary tables: one that relates course IDs to their metadata (name, course code, units, etc.), and one that relates what community college course IDs transfer to a university course ID.

### The Data
The data comes from the 'scraping' of ASSIST's internal api, by repeatedly making calls (while following their rate limits) via a script `download_data.py` to their api, as if it were an end user individually scanning every university : college agreement. This data is stored locally as JSON to avoid needing to re-query ASSIST. This, along with mappings between institutional IDs and names, are stored in the `data/` directory, under subdirectories split by university ID.

### The ETL Pipeline
This is one of the main portions of this project, and one that I am unnecessarily proud of. The dependencies are managed by a `uv` environment, and two scripts (`agreements_to_db.py`, `glossary_to_db.py`) perform a series of polars transformations (with the help of some `utils` functions) to convert the heaping pile of JSON into two beautiful Postgres tables. Testing was done with a local postgres database + environment variables before using the production environment.

This portion of the project has received significant overhauls in a time period of over a year, becoming much more robust (notebooks and pip to standalone scripts with uv), and gaining massive performance benefits with a polars + adbc port from pandas + sqlalchemy. It is singlehandedly responsible for my understanding of uv, Python project structure, and polars.

### The Backend
This is part of the second main portion of this project, the web app. This is also the source of my 'i know AWS just trust me bro' claims. All cloud architecture decisions were made by picking whatever industry standard tooling I could use without giving extra money to the big man himself Jeffery Bezos. 

The 'backend' is two AWS Lambda functions written in Python that: make a database query or two, do light transformations on the results, and return them. 

The backend is also managed by a shared uv environment, as both functions only required the download of the `supabase` library. Older versions made raw `requests` calls at a great cost to readability and robustness, but had smaller packages. 

The backend is deployed via a script `deploy-lambdas.sh`, which will:
- validate dependencies (uv, aws cli + login, backend directory structure)
- zip each lambda function with its dependencies
- find/setup a new lambda policy (permissions)
- for each lambda function it will either:
  - update the existing function with the zip and config
  - create a new lambda function with the specified zip & args, give it a new function url, and set invocation permissions with the policy

### The Frontend
A simple frontend was designed with AI-assisted styling via TailwindCSS classes, and hosted via Vercel. Basic reactivity and interactivity were created with Alpine.js. It looks clean enough (one would hope), but it may be clear that frontend is not exactly my forte. Regardless, in project-land, one must wear many hats.

## Future Plans
- Build a comprehensive test suite (at least for backend + pipeline)
- Automatic monthly scraping of data and re-creation of DB
- Notice when query gives no articulations
- Automatically run a basic query on supabase to not get no-activity'd and paused every couple of weeks 🥲
- Filtering of articulations via community college
- Dockerize pipeline

## Known bugs
- Duplicate courses (course code, institution) may get past unique filters in database creation by virtue of different course IDs
  - hotfix: deleted duplicate row from production database
  - symptom: university with duplicates does not render course selection dropdown
  - cause: duplicate code as key in x-for element causes error & failure to execute/render
  - proposed solution: add filtering step in `glossary_to_db.py` to unique filter database by (inst,  course code), select latest added via 'begin' field before dropping