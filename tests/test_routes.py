import pytest, sys
sys.path.append('C:\\Users\\Patrick\\Documents\\FACULDADE\\PROJETO INTEGRADOR\\FINAL')
from app import app as flask_app # type: ignore

def test_api_scams(client):
    # 1. Crie um usuário de teste primeiro
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "123456",
        "type_user": "noob",
        "confidence": 1.5,
        "age": 25,
        "city": "Test City",
        "state": "TS",
        "civil_state": "single"
    }
    client.post('/api/users', json=user_data)

    # 2. Faça login para obter token
    login_resp = client.post('/api/login', json={
        "email": "test@example.com",
        "password": "123456"
    })
    token = login_resp.json['access_token']

    # 3. Teste POST com autenticação
    scam_data = {
        "name": "Phishing Test",
        "type_scam": "Fraude",
        "danger_level": 1.0,
        "damage_level": 1.5,
        "evidence": "proof.jpg"
    }
    post_resp = client.post(
        '/api/scams',
        json=scam_data,
        headers={'Authorization': f'Bearer {token}'}
    )
    assert post_resp.status_code == 201
    assert 'id' in post_resp.json

    # 4. Teste GET
    get_resp = client.get('/api/scams')
    assert get_resp.status_code == 200
    assert isinstance(get_resp.json, list)
    assert any(s['name'] == "Phishing Test" for s in get_resp.json)


    