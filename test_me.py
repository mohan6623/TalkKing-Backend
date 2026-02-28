import requests, sys
email='marveljj4@gmail.com'
password='Password123!'
res = requests.post('http://localhost:8000/api/v1/auth/login', json={'email': email, 'password': password})
if not res.ok:
    print('Login failed:', res.text); sys.exit(1)
token = res.json().get('access_token')
print('Token:', token[:20])
res2 = requests.get('http://localhost:8000/api/v1/users/me', headers={'Authorization': f'Bearer {token}'})
print('/users/me response:', res2.status_code, res2.text)
