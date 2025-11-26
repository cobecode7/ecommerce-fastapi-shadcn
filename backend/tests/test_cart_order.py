from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
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
    with Session(engine) as session:
        # Populate mock product data
        from main import mock_products_data, Product
        if not session.exec(select(Product)).first():
            for prod_data in mock_products_data:
                product = Product.model_validate(prod_data)
                session.add(product)
            session.commit()
    with TestClient(app) as c:
        yield c
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="test_user_token")
def test_user_token_fixture(client: TestClient):
    # Register a user
    client.post("/api/register", json={"username": "testuser", "password": "testpassword"})
    # Log in the user and get a token
    response = client.post("/api/login", json={"username": "testuser", "password": "testpassword"})
    token = response.json()["access_token"]
    return token

@pytest.fixture(name="test_product_id")
def test_product_id_fixture(client: TestClient, test_user_token: str):
    # Add a product to the database
    headers = {"Authorization": f"Bearer {test_user_token}"}
    # This is a mock product, in a real scenario, you would have an admin endpoint to add products
    # For now, we'll assume there's a product with ID 1 already in the database from the lifespan function
    # Or we can add one directly to the session if needed for testing
    # For simplicity, let's assume product with ID 1 exists.
    return 1

# --- Cart Tests ---

def test_add_item_to_cart(client: TestClient, test_user_token: str, test_product_id: int):
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = client.post(
        "/api/cart/items",
        json={"product_id": test_product_id, "quantity": 1},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == test_product_id
    assert data["quantity"] == 1

def test_add_existing_item_to_cart(client: TestClient, test_user_token: str, test_product_id: int):
    headers = {"Authorization": f"Bearer {test_user_token}"}
    client.post(
        "/api/cart/items",
        json={"product_id": test_product_id, "quantity": 1},
        headers=headers,
    )
    response = client.post(
        "/api/cart/items",
        json={"product_id": test_product_id, "quantity": 2},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == test_product_id
    assert data["quantity"] == 3  # 1 (initial) + 2 (added) = 3

def test_get_user_cart(client: TestClient, test_user_token: str, test_product_id: int):
    headers = {"Authorization": f"Bearer {test_user_token}"}
    client.post(
        "/api/cart/items",
        json={"product_id": test_product_id, "quantity": 1},
        headers=headers,
    )
    response = client.get("/api/cart", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["cart_items"]) == 1
    assert data["cart_items"][0]["product_id"] == test_product_id

def test_remove_item_from_cart(client: TestClient, test_user_token: str, test_product_id: int):
    headers = {"Authorization": f"Bearer {test_user_token}"}
    add_response = client.post(
        "/api/cart/items",
        json={"product_id": test_product_id, "quantity": 1},
        headers=headers,
    )
    item_id = add_response.json()["id"]
    response = client.delete(f"/api/cart/items/{item_id}", headers=headers)
    assert response.status_code == 204
    cart_response = client.get("/api/cart", headers=headers)
    assert cart_response.status_code == 404 # Cart not found because it's empty

def test_update_cart_item_quantity(client: TestClient, test_user_token: str, test_product_id: int):
    headers = {"Authorization": f"Bearer {test_user_token}"}
    add_response = client.post(
        "/api/cart/items",
        json={"product_id": test_product_id, "quantity": 1},
        headers=headers,
    )
    item_id = add_response.json()["id"]
    response = client.put(
        f"/api/cart/items/{item_id}",
        json={"quantity": 5},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["quantity"] == 5

# --- Order Tests ---

def test_create_order_from_cart(client: TestClient, test_user_token: str, test_product_id: int):
    headers = {"Authorization": f"Bearer {test_user_token}"}
    client.post(
        "/api/cart/items",
        json={"product_id": test_product_id, "quantity": 2},
        headers=headers,
    )
    response = client.post("/api/orders", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 1 # Assuming testuser has id 1
    assert data["total_amount"] > 0
    assert len(data["order_items"]) == 1

def test_get_user_orders(client: TestClient, test_user_token: str, test_product_id: int):
    headers = {"Authorization": f"Bearer {test_user_token}"}
    client.post(
        "/api/cart/items",
        json={"product_id": test_product_id, "quantity": 1},
        headers=headers,
    )
    client.post("/api/orders", headers=headers)
    response = client.get("/api/orders", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 1

def test_get_single_order(client: TestClient, test_user_token: str, test_product_id: int):
    headers = {"Authorization": f"Bearer {test_user_token}"}
    client.post(
        "/api/cart/items",
        json={"product_id": test_product_id, "quantity": 1},
        headers=headers,
    )
    order_response = client.post("/api/orders", headers=headers)
    order_id = order_response.json()["id"]
    response = client.get(f"/api/orders/{order_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == order_id
    assert data["user_id"] == 1
