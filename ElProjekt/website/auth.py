import os
import requests
from website import app

GOOGLE_CLIENT_ID = '476358247913-u7m802aipif8nnt7un4o8d46rldre87h.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = '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'  

OAUTH2_PROVIDERS = {
    'google': {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'authorize_url': 'https://accounts.google.com/o/oauth2/auth',
        'token_url': 'https://accounts.google.com/o/oauth2/token',
        'userinfo_endpoint': 'https://www.googleapis.com/oauth2/v3/userinfo',
        'userinfo_scope': 'email',
        'userinfo_parser': lambda json: json['email'],
    },
}

def get_user_info(access_token):
    userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
    headers = {'Authorization': 'Bearer {}'.format(access_token)}
    response = requests.get(userinfo_url, headers=headers)
    if response.status_code == 200:
        user_info = response.json()
        if user_info['email'].startswith('x'):
            user_info['role'] = 'student'
        else:
            user_info['role'] = 'teacher'
        return user_info
    else:
        print('Failed to fetch user info:', response.text)
        return None

