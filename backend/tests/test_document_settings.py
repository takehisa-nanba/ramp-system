from backend.tests.test_job_retention_auth import auth_setup, get_headers


def test_document_settings_office_route_is_registered(app, auth_setup):
    client = app.test_client()
    staff = auth_setup["staff_a"]

    response = client.get(
        "/api/consents/settings/office",
        headers=get_headers(f"staff:{staff.id}"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["office_id"] == staff.office_id
    assert "electronic_document_enabled" in payload
    assert "can_edit" in payload


def test_document_settings_office_route_rejects_user_actor(app, auth_setup):
    client = app.test_client()
    user = auth_setup["user_a"]

    response = client.get(
        "/api/consents/settings/office",
        headers=get_headers(f"user:{user.id}"),
    )

    assert response.status_code == 403
