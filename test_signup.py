import requests, sys
email='marveljj5@gmail.com'
password='Password123!'
res = requests.post('http://localhost:8000/api/v1/auth/signup', json={'email': email, 'password': password, 'name': 'Marvel'})
print('Signup:', res.text)
if res.ok:
    token = res.json().get('access_token')
    print('Token:', token)
    if token:
        res2 = requests.get('http://localhost:8000/api/v1/users/me', headers={'Authorization': f'Bearer {token}'})
        print('/users/me:', res2.status_code, res2.text)
