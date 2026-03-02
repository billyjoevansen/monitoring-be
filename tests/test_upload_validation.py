def test_reconcile_missing_files(client):
    response = client.post('/api/reconcile')
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_train_missing_files(client):
    response = client.post('/api/train')
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_model_info_no_model(client):
    response = client.get('/api/model/info')
    assert response.status_code == 404
