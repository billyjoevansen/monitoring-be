def test_health_check(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'


def test_health_check_message(client):
    response = client.get('/api/health')
    data = response.get_json()
    assert 'message' in data
