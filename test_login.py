import re, sys
try:
    import requests
    import jwt
    from app.config import settings
    res = requests.post('http://localhost:8000/api/v1/auth/signup', json={'email': 'realuser123@gmail.com', 'password': 'Password123!', 'name': 'Real User'})
    if not res.ok:
        print('Failed to signup:', res.text)
        res = requests.post('http://localhost:8000/api/v1/auth/login', json={'email': 'realuser123@gmail.com', 'password': 'Password123!'})
        print('Tried login:', res.text)
    token = res.json().get('access_token')
    if not token:
        sys.exit(1)
    print('Token:', token[:20] + '...')
    # Decode without verify
    payload = jwt.decode(token, options={'verify_signature': False})
    print('Payload:', payload)
    # Decode with verify
    try:
        jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=['HS256'], audience='authenticated')
        print('Verify OK')
    except Exception as e:
        print('Decode Error:', e)
except Exception as exc:
    import traceback; traceback.print_exc()
