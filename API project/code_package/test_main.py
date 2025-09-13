# test_main.py (نسخه نهایی با تمام ۲۵ تست)

import pytest
import os
import sqlite3
from fastapi.testclient import TestClient

# برای تغییر متغیر DATABASE در main، خود ماژول را وارد می‌کنیم
import main

TEST_DB_PATH = "test_database.db"


# Override می‌کنیم تا از دیتابیس تستی استفاده شود
def override_get_db_connection():
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


main.app.dependency_overrides[main.get_db_connection] = override_get_db_connection


@pytest.fixture
def client():
    """
    این فیکسچر یک کلاینت تستی ایزوله با دیتابیس تمیز برای هر تست ایجاد می‌کند.
    """
    # متغیر سراسری در ماژول main را به مسیر دیتابیس تستی تغییر می‌دهیم
    main.DATABASE = TEST_DB_PATH

    # فایل قدیمی را برای اطمینان پاک می‌کنیم
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    # 'with' باعث اجرای lifespan و ساخت جداول در دیتابیس تستی می‌شود
    with TestClient(main.app) as test_client:
        yield test_client

    # بعد از اتمام تست، فایل دیتابیس تستی را پاک می‌کنیم
    main.DATABASE = 'database.db'  # برگرداندن به حالت اولیه
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


# --- تمام ۲۵ تست شما با دریافت 'client' به عنوان آرگومان ---
valid_item_data = {
    "name": "Test Item", "description": "A valid test item",
    "price": 10.0, "category": "test", "stock": 5
}


def test_add_item(client):
    response = client.post("/items", json=valid_item_data)
    assert response.status_code == 200
    item_id = response.json()["item_id"]
    get_response = client.get(f"/items/{item_id}")
    assert get_response.status_code == 200
    assert get_response.json()["item"]["name"] == "Test Item"


def test_add_item_with_invalid_price(client):
    item_data = valid_item_data.copy();
    item_data["price"] = -10.0
    response = client.post("/items", json=item_data)
    assert response.status_code == 422


def test_add_item_with_invalid_stock(client):
    item_data = valid_item_data.copy();
    item_data["stock"] = -1
    response = client.post("/items", json=item_data)
    assert response.status_code == 422


def test_add_item_with_missing_name(client):
    item_data = valid_item_data.copy();
    del item_data["name"]
    response = client.post("/items", json=item_data)
    assert response.status_code == 422


def test_add_item_with_missing_price(client):
    item_data = valid_item_data.copy();
    del item_data["price"]
    response = client.post("/items", json=item_data)
    assert response.status_code == 422


def test_add_item_with_missing_category(client):
    item_data = valid_item_data.copy();
    del item_data["category"]
    response = client.post("/items", json=item_data)
    assert response.status_code == 422


def test_add_item_with_missing_stock(client):
    item_data = valid_item_data.copy();
    del item_data["stock"]
    response = client.post("/items", json=item_data)
    assert response.status_code == 422


def test_add_item_with_missing_description_is_ok(client):
    item_data = valid_item_data.copy();
    del item_data["description"]
    response = client.post("/items", json=item_data)
    assert response.status_code == 200


def test_get_all_items(client):
    client.post("/items", json={"name": "Laptop", "price": 999.99, "category": "electronics", "stock": 10})
    client.post("/items", json={"name": "Mouse", "price": 25.0, "category": "accessories", "stock": 50})
    response = client.get("/items")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["items"][0]["name"] == "Laptop"
    assert data["items"][1]["name"] == "Mouse"


def test_get_single_item(client):
    post_res = client.post("/items", json={"name": "Keyboard", "price": 75.0, "category": "accessories", "stock": 20})
    item_id = post_res.json()["item_id"]
    response = client.get(f"/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["item"]["name"] == "Keyboard"


def test_get_non_existent_item(client):
    response = client.get("/items/999")
    assert response.status_code == 404


def test_update_item(client):
    post_res = client.post("/items", json=valid_item_data)
    item_id = post_res.json()["item_id"]
    update_data = {"price": 899.99, "stock": 5}
    client.put(f"/items/{item_id}", json=update_data)
    get_response = client.get(f"/items/{item_id}")
    updated_item = get_response.json()["item"]
    assert updated_item["price"] == 899.99
    assert updated_item["stock"] == 5


def test_update_non_existent_item(client):
    response = client.put("/items/999", json={"price": 10.0})
    assert response.status_code == 404


def test_delete_item(client):
    post_res = client.post("/items", json=valid_item_data)
    item_id = post_res.json()["item_id"]
    client.delete(f"/items/{item_id}")
    get_response = client.get(f"/items/{item_id}")
    assert get_response.status_code == 404


def test_delete_non_existent_item(client):
    response = client.delete("/items/999")
    assert response.status_code == 404


def test_add_item_to_cart(client):
    post_res = client.post("/items", json=valid_item_data)
    item_id = post_res.json()["item_id"]
    client.post("/cart/add", json={"item_id": item_id, "quantity": 2})
    cart_contents = client.get("/cart").json()
    assert cart_contents["items"][0]["quantity"] == 2


def test_add_item_exceeding_stock(client):
    post_res = client.post("/items", json={"name": "Limited", "price": 10, "category": "cat", "stock": 5})
    item_id = post_res.json()["item_id"]
    response = client.post("/cart/add", json={"item_id": item_id, "quantity": 10})
    assert response.status_code == 400


def test_add_non_existent_item_to_cart(client):
    response = client.post("/cart/add", json={"item_id": 999, "quantity": 1})
    assert response.status_code == 404


def test_remove_item_partially_from_cart(client):
    post_res = client.post("/items", json=valid_item_data)
    item_id = post_res.json()["item_id"]
    client.post("/cart/add", json={"item_id": item_id, "quantity": 5})
    client.delete(f"/cart/items/{item_id}?quantity=2")
    cart_contents = client.get("/cart").json()
    assert cart_contents["items"][0]["quantity"] == 3


def test_remove_item_fully_from_cart(client):
    post_res = client.post("/items", json=valid_item_data)
    item_id = post_res.json()["item_id"]
    client.post("/cart/add", json={"item_id": item_id, "quantity": 3})
    client.delete(f"/cart/items/{item_id}?quantity=3")
    cart_contents = client.get("/cart").json()
    assert len(cart_contents["items"]) == 0


def test_remove_non_existent_item_from_cart(client):
    response = client.delete("/cart/items/999?quantity=1")
    assert response.status_code == 404


def test_remove_more_items_than_in_cart(client):
    post_res = client.post("/items", json=valid_item_data)
    item_id = post_res.json()["item_id"]
    client.post("/cart/add", json={"item_id": item_id, "quantity": 3})
    client.delete(f"/cart/items/{item_id}?quantity=5")
    cart_contents = client.get("/cart").json()
    assert len(cart_contents["items"]) == 0


def test_get_cart_contents(client):
    post_res1 = client.post("/items", json={"name": "Laptop", "price": 1000.0, "category": "e", "stock": 10})
    post_res2 = client.post("/items", json={"name": "Mouse", "price": 50.0, "category": "a", "stock": 50})
    item_id1, item_id2 = post_res1.json()["item_id"], post_res2.json()["item_id"]
    client.post("/cart/add", json={"item_id": item_id1, "quantity": 2})
    client.post("/cart/add", json={"item_id": item_id2, "quantity": 3})
    response = client.get("/cart")
    data = response.json()
    assert data["total_price"] == 2150.0
    assert data["total_items"] == 5


def test_finalize_cart(client):
    post_res1 = client.post("/items", json={"name": "Laptop", "price": 1000.0, "category": "e", "stock": 10})
    post_res2 = client.post("/items", json={"name": "Mouse", "price": 50.0, "category": "a", "stock": 50})
    item_id1, item_id2 = post_res1.json()["item_id"], post_res2.json()["item_id"]
    client.post("/cart/add", json={"item_id": item_id1, "quantity": 2})
    client.post("/cart/add", json={"item_id": item_id2, "quantity": 3})
    client.post("/cart/finalize")
    cart_contents = client.get("/cart").json()
    assert cart_contents["total_items"] == 0
    item1 = client.get(f"/items/{item_id1}").json()["item"]
    item2 = client.get(f"/items/{item_id2}").json()["item"]
    assert item1["stock"] == 8
    assert item2["stock"] == 47


def test_finalize_empty_cart(client):
    response = client.post("/cart/finalize")
    assert response.status_code == 400