import pytest

VALID = {"name": "Ada Lovelace", "email": "ada@example.com"}


def create(client, **overrides):
    return client.post("/v1/customers", json={**VALID, **overrides})


# --- create ---------------------------------------------------------------------------


def test_create_customer_returns_201_with_body_and_location(client):
    response = create(client)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ada Lovelace"
    assert body["email"] == "ada@example.com"
    assert isinstance(body["id"], int)
    assert "created_at" in body
    assert response.headers["Location"] == f"/v1/customers/{body['id']}"


def test_create_customer_trims_name_and_lowercases_email(client):
    response = create(client, name="  Ada  ", email="ADA@Example.COM")

    assert response.status_code == 201
    assert response.json()["name"] == "Ada"
    assert response.json()["email"] == "ada@example.com"


def test_duplicate_email_returns_409(client):
    assert create(client).status_code == 201

    response = create(client, name="Someone Else")

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_duplicate_email_is_case_insensitive(client):
    assert create(client, email="ada@example.com").status_code == 201
    assert create(client, email="ADA@EXAMPLE.COM").status_code == 409


def test_failed_duplicate_does_not_lose_earlier_customers(client):
    first = create(client).json()
    create(client)  # 409, triggers a rollback inside the service

    assert client.get(f"/v1/customers/{first['id']}").status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Ada"},  # email missing
        {"email": "ada@example.com"},  # name missing
        {"name": "", "email": "ada@example.com"},  # empty name
        {"name": "   ", "email": "ada@example.com"},  # whitespace-only name
        {"name": "x" * 201, "email": "ada@example.com"},  # name too long
        {"name": "Ada", "email": "not-an-email"},
        {"name": "Ada", "email": 123},
        {},
    ],
)
def test_invalid_create_payload_returns_422(client, payload):
    assert client.post("/v1/customers", json=payload).status_code == 422


def test_client_cannot_set_server_controlled_fields(client):
    response = create(client, id=999, created_at="2000-01-01T00:00:00")

    assert response.status_code == 201
    assert response.json()["id"] != 999
    assert not response.json()["created_at"].startswith("2000")


# --- read -----------------------------------------------------------------------------


def test_get_customer_returns_200(client):
    created = create(client).json()

    response = client.get(f"/v1/customers/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_customer_returns_404(client):
    response = client.get("/v1/customers/123456")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_get_customer_with_non_integer_id_returns_422(client):
    assert client.get("/v1/customers/abc").status_code == 422


# --- list -----------------------------------------------------------------------------


def test_list_customers_empty(client):
    response = client.get("/v1/customers")

    assert response.status_code == 200
    assert response.json() == []


def test_list_customers_is_ordered_and_paginated(client):
    ids = [create(client, email=f"c{i}@example.com").json()["id"] for i in range(5)]

    page1 = client.get("/v1/customers", params={"limit": 2, "offset": 0}).json()
    page2 = client.get("/v1/customers", params={"limit": 2, "offset": 2}).json()
    page3 = client.get("/v1/customers", params={"limit": 2, "offset": 4}).json()

    assert [c["id"] for c in page1] == ids[0:2]
    assert [c["id"] for c in page2] == ids[2:4]
    assert [c["id"] for c in page3] == ids[4:5]


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "many"}],
)
def test_list_customers_rejects_bad_pagination(client, params):
    assert client.get("/v1/customers", params=params).status_code == 422
