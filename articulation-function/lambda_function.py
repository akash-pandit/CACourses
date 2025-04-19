import os
import json
import requests

# Grab these from your Lambda’s Environment Variables
SUPA_URL = os.environ['SUPABASE_URL'].rstrip('/')
SUPA_KEY = os.environ['SUPABASE_ANON_KEY']

def lambda_handler(event, context):
    # 1) Extract the course_id query parameter
    params = event.get('queryStringParameters') or {}
    course_id = params.get('course_id')
    if not course_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing course_id parameter'})
        }

    # 2) Build the Supabase REST URL and query
    url = f"{SUPA_URL}/rest/v1/articulations"
    query = {
        'select': 'articulation',
        'course_id': f'eq.{course_id}',
    }
    headers = {
        'apikey': SUPA_KEY,
        'Authorization': f'Bearer {SUPA_KEY}',
        'Accept': 'application/json'
    }

    # 3) Call Supabase and return the JSON array of { articulation: "…" }
    resp = requests.get(url, params=query, headers=headers)
    resp.raise_for_status()

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*'
        },
        'body': resp.text
    }
