def test_get_config(client):
    response = client.get('/api/config')
    assert response.status_code == 200
    data = response.get_json()
    assert 'config' in data
    assert 'hyperparameters' in data['config']
    assert 'training_config' in data['config']


def test_get_config_has_param_rules(client):
    response = client.get('/api/config')
    data = response.get_json()
    assert 'param_rules' in data


def test_update_config_empty_body(client):
    response = client.put('/api/config', json=None)
    assert response.status_code == 400


def test_reset_config(client):
    response = client.post('/api/config/reset')
    assert response.status_code == 200
    data = response.get_json()
    assert data['config']['hyperparameters']['n_estimators'] == 200
