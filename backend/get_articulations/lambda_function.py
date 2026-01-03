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
            'Access-Control-Allow-Origin': '*',
        },
        "body": json.dumps(body)
    }


def get_articulations(course_id: int):
    try:
        query = (
            SUPA_CLIENT
            .table("articulations")
            .select("cc", "articulation")
            .eq("course_id", course_id)
            .execute()
        )
        
        # Transform data into the desired dictionary format
        articulation_map: dict[int, str] = {
            elem.get("cc"): elem.get("articulation") 
            for elem in query.data 
            if isinstance(elem, dict)
        } # type: ignore

        course_id_set = set()
        for articulation_str in articulation_map.values():
            articulation = json.loads(articulation_str)
            for and_group in articulation.get("items"):
                course_id_set.update(and_group.get("items"))
        
        query = (
            SUPA_CLIENT
            .table("glossary")
            .select("*")
            .in_("course_id", course_id_set)
            .execute()
        )
        
        glossary_map: dict[int, str] = {
            elem.get("course_id"): elem
            for elem in query.data
            if isinstance(elem, dict)
        } # type: ignore

        return create_response(200, [articulation_map, glossary_map])
        
    except APIError as e:
        print(f"Database error: {e}") # Log for CloudWatch
        return create_response(502, {"error": "Database connection failed"})
    except Exception as e:
        print(f"Unexpected error: {e}")
        return create_response(500, {"error": "Internal server error"})
    

def lambda_handler(event, context):
    params = event.get('queryStringParameters') or {}

    # 1. Validation: Check existence
    if not (course_id_raw := params.get("course_id")) :
        return create_response(400, {"message": "Missing course_id parameter"})

    # 2. Validation: Check type
    try:
        course_id = int(course_id_raw)
    except ValueError:
        return create_response(400, {"message": "course_id must be an integer"})

    # 3. 
    return get_articulations(course_id)
