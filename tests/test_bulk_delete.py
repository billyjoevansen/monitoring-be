def test_bulk_delete_archive_missing_body(client):
    response = client.post('/api/archive/bulk-delete', json=None)
    assert response.status_code == 400


def test_bulk_delete_archive_missing_type(client):
    response = client.post('/api/archive/bulk-delete', json={'session_ids': [1, 2]})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_bulk_delete_archive_invalid_type(client):
    response = client.post('/api/archive/bulk-delete', json={'type': 'invalid', 'session_ids': [1]})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_bulk_delete_archive_missing_session_ids(client):
    response = client.post('/api/archive/bulk-delete', json={'type': 'reconcile'})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_bulk_delete_archive_empty_session_ids(client):
    response = client.post('/api/archive/bulk-delete', json={'type': 'reconcile', 'session_ids': []})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_bulk_delete_users_missing_body(client):
    response = client.post('/api/users/bulk-delete', json=None)
    assert response.status_code == 400


def test_bulk_delete_users_missing_user_ids(client):
    response = client.post('/api/users/bulk-delete', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_bulk_delete_users_empty_user_ids(client):
    response = client.post('/api/users/bulk-delete', json={'user_ids': []})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_bulk_delete_logs_missing_body(client):
    response = client.post('/api/logs/bulk-delete', json=None)
    assert response.status_code == 400


def test_bulk_delete_logs_missing_log_ids(client):
    response = client.post('/api/logs/bulk-delete', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_bulk_delete_logs_empty_log_ids(client):
    response = client.post('/api/logs/bulk-delete', json={'log_ids': []})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
