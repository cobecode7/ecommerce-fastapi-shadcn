from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from main import app, get_session
import pytest

DATABASE_URL = "sqlite:///test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Dependency override for tests
def get_test_session():
    with Session(engine) as session:
        yield session

app.dependency_overrides[get_session] = get_test_session

@pytest.fixture(scope="function")
def client():
    SQLModel.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c
    SQLModel.metadata.drop_all(engine)

def test_register_user(client):
    response = client.post("/api/register", json={"username": "testuser", "password": "testpassword"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data

def test_register_existing_user(client):
    client.post("/api/register", json={"username": "testuser", "password": "testpassword"})
    response = client.post("/api/register", json={"username": "testuser", "password": "testpassword"})
    assert response.status_code == 400

def test_login(client):
    client.post("/api/register", json={"username": "testuser", "password": "testpassword"})
    response = client.post("/api/login", json={"username": "testuser", "password": "testpassword"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client):
    client.post("/api/register", json={"username": "testuser", "password": "testpassword"})
    response = client.post("/api/login", json={"username": "testuser", "password": "wrongpassword"})
    assert response.status_code == 401

def test_login_wrong_username(client):
    client.post("/api/register", json={"username": "testuser", "password": "testpassword"})
    response = client.post("/api/login", json={"username": "wronguser", "password": "testpassword"})
    assert response.status_code == 401

def test_access_protected_route_with_valid_token(client):
    client.post("/api/register", json={"username": "testuser", "password": "testpassword"})
    login_response = client.post("/api/login", json={"username": "testuser", "password": "testpassword"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"

def test_access_protected_route_with_invalid_token(client):
    headers = {"Authorization": "Bearer invalidtoken"}
    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 401
