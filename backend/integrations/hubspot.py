# hubspot.py

import json
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import base64
import requests
from integrations.integration_item import IntegrationItem
from os import environ
import urllib.parse
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

CLIENT_ID = environ.get("HUBSPOT_CLIENT_ID") if environ.get("HUBSPOT_CLIENT_ID",None)is not  None else 'xxx'
CLIENT_SECRET = environ.get("HUBSPOT_CLIENT_SECRET") if environ.get("HUBSPOT_CLIENT_SECRET",None)is not None else 'xxx'
REDIRECT_URI = environ.get("HUBSPOT_REDIRECT_URI") if environ.get("HUBSPOT_REDIRECT_URI",None)is not None else 'http://localhost:8000/integrations/hubspot/oauth2callback'
authorization_url = f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={urllib.parse.quote_plus(REDIRECT_URI)}'
scope = 'crm.objects.contacts.read crm.objects.companies.read crm.objects.deals.read'

async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode('utf-8')).decode('utf-8')

    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', json.dumps(state_data), expire=600)

    return f'{authorization_url}&state={encoded_state}&scope={scope}'

async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error_description', request.query_params.get('error')))
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    state_data = json.loads(base64.urlsafe_b64decode(encoded_state).decode('utf-8'))

    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')

    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')

    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                'https://api.hubapi.com/oauth/v3/token',
                data={
                    'grant_type': 'authorization_code',
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                    'redirect_uri': REDIRECT_URI,
                    'code': code,
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                }
            ),
            delete_key_redis(f'hubspot_state:{org_id}:{user_id}'),
        )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=response.json())

    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)

    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)

async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    credentials = json.loads(credentials)
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    return credentials

def _get_property(properties, *keys):
    """Return the first non-empty property value among the given keys."""
    for key in keys:
        if key in properties and properties.get(key):
            return properties[key]
    return None

async def create_integration_item_metadata_object(
    response_json: str, item_type: str, parent_id=None, parent_name=None
) -> IntegrationItem:
    properties = response_json.get('properties', {})

    if item_type == 'Contact':
        firstname = _get_property(properties, 'firstname')
        lastname = _get_property(properties, 'lastname')
        email = _get_property(properties, 'email')
        name = ' '.join(filter(None, [firstname, lastname])) or email
    elif item_type == 'Company':
        name = _get_property(properties, 'name', 'domain')
    else:
        name = _get_property(properties, 'dealname', 'hs_object_id')

    integration_item_metadata = IntegrationItem(
        id=response_json.get('id', None) + '_' + item_type,
        name=name,
        type=item_type,
        parent_id=parent_id,
        parent_path_or_name=parent_name,
        creation_time=response_json.get('createdAt', None),
        last_modified_time=response_json.get('updatedAt', None),
    )

    return integration_item_metadata

def fetch_items(access_token: str, url: str, aggregated_response: list, after=None) -> dict:
    """Fetching the list of CRM objects with pagination"""
    params = {'limit': 100}
    if after is not None:
        params['after'] = after
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        results = response.json().get('results', [])
        after = response.json().get('paging', {}).get('next', {}).get('after', None)

        for item in results:
            aggregated_response.append(item)

        if after is not None:
            fetch_items(access_token, url, aggregated_response, after)
        else:
            return

async def get_items_hubspot(credentials) -> list[IntegrationItem]:
    credentials = json.loads(credentials)
    access_token = credentials.get('access_token')
    object_types = {'contacts': 'Contact', 'companies': 'Company', 'deals': 'Deal'}
    list_of_integration_item_metadata = []

    for object_type, item_type in object_types.items():
        url = f'https://api.hubapi.com/crm/v3/objects/{object_type}'
        list_of_responses = []
        fetch_items(access_token, url, list_of_responses)
        for response in list_of_responses:
            list_of_integration_item_metadata.append(
                await create_integration_item_metadata_object(response, item_type)
            )

    print(f'list_of_integration_item_metadata: {list_of_integration_item_metadata}')
    return list_of_integration_item_metadata