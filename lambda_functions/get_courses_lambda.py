import os, json
import requests

SUPA_URL = os.environ['SUPABASE_URL'].rstrip('/')
SUPA_KEY = os.environ['SUPABASE_ANON_KEY']

def lambda_handler(event, context):
    # grab the query param
    params = event.get('queryStringParameters') or {}
    uni = params.get('uni')
    if not uni:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing uni parameter'}),
        }

    # build the REST URL for your table
    url = f"{SUPA_URL}/rest/v1/course_glossary"
    # Supabase expects filters like inst_id=eq.120
    query = {
        'select': 'course_id,course_code,course_name',
        'inst_id': f'eq.{uni}',
    }
    headers = {
        'apikey': SUPA_KEY,
        'Authorization': f'Bearer {SUPA_KEY}',
        'Accept': 'application/json',
    }

    # fire the request
    resp = requests.get(url, params=query, headers=headers)
    resp.raise_for_status()

    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': resp.text  # already JSON
    }
