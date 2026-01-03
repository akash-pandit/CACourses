#!/usr/bin/env python

import json
import os
from typing import Any

from postgrest.exceptions import APIError
from supabase import Client, create_client

# set up globals to init once per 'cold start'
SUPA_URL: str | None = os.getenv("SUPABASE_URL")
SUPA_KEY: str | None = os.getenv("SUPABASE_ANON_KEY")

if not (SUPA_URL and SUPA_KEY):
    raise RuntimeError("Could not find environment variables SUPA_URL or SUPA_KEY.")

SUPA_CLIENT: Client = create_client(supabase_url=SUPA_URL, supabase_key=SUPA_KEY)


def create_response(status_code: int, body: Any):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json", 
            'Access-Control-Allow-Origin': '*'
        },
        "body": json.dumps(body)
    }


def get_courses(inst_id: int):
    try:
        query = (
            SUPA_CLIENT
            .table("glossary")
            .select("course_id", "course_code", "course_name")
            .eq("inst_id", inst_id)
            .execute()
        )

        return create_response(200, query.data)

    except APIError as e:
        print(f"Database error: {e}")
        return create_response(502, {"error": "Database connection failed"})
    except Exception as e:
        print(f"Unexpected error: {e}")


def lambda_handler(event, context):
    params = event.get('queryStringParameters') or {}

    if not (inst_id_raw := params.get("inst_id")):
        return create_response(400, {"message": "Missing inst_id parameter"})

    try:
        inst_id_raw = int(inst_id_raw)
    except ValueError:
        return create_response(400, {"message": "inst_id must be an integer"})
    
    return get_courses(inst_id_raw)