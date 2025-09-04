import os
import json
import requests

SUPA_URL = os.environ['SUPABASE_URL'].rstrip('/')
SUPA_KEY = os.environ['SUPABASE_ANON_KEY']

def lambda_handler(event, context):
    # 1) Get course_id param
    params = event.get('queryStringParameters') or {}
    course_id = params.get('course_id')
    if not course_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing course_id parameter'})
        }

    headers = {
        'apikey': SUPA_KEY,
        'Authorization': f'Bearer {SUPA_KEY}',
        'Accept': 'application/json'
    }

    # 2) Fetch raw articulations (with cc)
    art_url = f"{SUPA_URL}/rest/v1/articulations"
    art_query = {
        'select': 'cc,articulation',
        'course_id': f'eq.{course_id}'
    }
    art_res = requests.get(art_url, params=art_query, headers=headers)
    art_res.raise_for_status()
    articulations = art_res.json()

    # 3) Collect all referenced course_ids
    ids = set()
    for rec in articulations:
        art = rec.get('articulation')
        if isinstance(art, str):
            try:
                art = json.loads(art)
            except json.JSONDecodeError:
                continue
        for group in art.get('items', []):
            for pid in group.get('items', []):
                ids.add(pid)

    # 4) Fetch course details in one go
    courses_map = {}
    if ids:
        courses_url = f"{SUPA_URL}/rest/v1/course_glossary"
        id_list = ','.join(str(i) for i in ids)
        courses_query = {
            'select': 'course_id,course_code,course_name,min_units,max_units',
            'course_id': f'in.({id_list})'
        }
        course_res = requests.get(courses_url, params=courses_query, headers=headers)
        course_res.raise_for_status()
        courses = course_res.json()
        # build mapping: course_id -> course object
        courses_map = {
            str(c['course_id']): c
            for c in courses
        }

    # 5) Return [original articulations, courses_map]
    payload = [articulations, courses_map]
    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(payload)
    }
