import pytest
from fastapi.testclient import TestClient
from main import app, db

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    db.items_db.clear()
    db.cart_db.clear()
    db.purchases_db.clear()
    db.item_id_counter = 0
    db.purchase_id_counter = 0

valid_item_data = {
    "name": "Test Item",
    "description": "A valid test item",
    "price": 10.0,
    "category": "test",
    "stock": 5
}
# ===============================================================
# تست‌های مدیریت آیتم (Items Management)
# ===============================================================

def test_add_item():
    """تست اضافه کردن یک آیتم جدید به فروشگاه"""
    new_item = {
        "name": "Laptop",
        "description": "High-performance laptop",
        "price": 999.99,
        "category": "electronics",
        "stock": 10
    }
    response = client.post("/items", json=new_item)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Item added successfully"
    assert "item" in data
    assert data["item"]["name"] == "Laptop"
    assert data["item"]["id"] == 1
    assert db.items_db[1]["name"] == "Laptop"


def test_add_item_with_invalid_price():
    """تست اضافه کردن آیتم با قیمت نامعتبر (صفر یا منفی)"""
    new_item = {
        "name": "Invalid Item",
        "price": -10.0,
        "category": "invalid",
        "stock": 1
    }
    response = client.post("/items", json=new_item)
    assert response.status_code == 422
    assert "Input should be greater than 0" in response.json()["detail"][0]["msg"]


def test_add_item_with_invalid_stock():
    """تست اضافه کردن آیتم با موجودی نامعتبر (منفی)"""
    new_item = {
        "name": "Invalid Item",
        "price": 10.0,
        "category": "invalid",
        "stock": -1
    }
    response = client.post("/items", json=new_item)
    assert response.status_code == 422
    assert "Input should be greater than or equal to 0" in response.json()["detail"][0]["msg"]




def test_add_item_with_missing_name():
    """تست اضافه کردن آیتم با فیلد 'name' گم‌شده"""
    item_data = valid_item_data.copy()
    del item_data["name"]
    response = client.post("/items", json=item_data)
    assert response.status_code == 422
    assert "Field required" in response.json()["detail"][0]["msg"]

def test_add_item_with_missing_price():
    """تست اضافه کردن آیتم با فیلد 'price' گم‌شده"""
    item_data = valid_item_data.copy()
    del item_data["price"]
    response = client.post("/items", json=item_data)
    assert response.status_code == 422
    assert "Field required" in response.json()["detail"][0]["msg"]

def test_add_item_with_missing_category():
    """تست اضافه کردن آیتم با فیلد 'category' گم‌شده"""
    item_data = valid_item_data.copy()
    del item_data["category"]
    response = client.post("/items", json=item_data)
    assert response.status_code == 422
    assert "Field required" in response.json()["detail"][0]["msg"]

def test_add_item_with_missing_stock():
    """تست اضافه کردن آیتم با فیلد 'stock' گم‌شده"""
    item_data = valid_item_data.copy()
    del item_data["stock"]
    response = client.post("/items", json=item_data)
    assert response.status_code == 422
    assert "Field required" in response.json()["detail"][0]["msg"]


def test_add_item_with_missing_description_is_ok():
    """تست اضافه کردن آیتم با فیلد 'description' گم‌شده (نباید خطا دهد)"""
    item_data = valid_item_data.copy()
    del item_data["description"]
    response = client.post("/items", json=item_data)
    assert response.status_code == 200

def test_get_all_items():
    """تست دریافت تمام آیتم‌ها از فروشگاه"""
    # Arrange
    post_res1 = client.post("/items", json={"name": "Laptop", "price": 999.99, "category": "electronics", "stock": 10})
    post_res2 = client.post("/items", json={"name": "Mouse", "price": 25.0, "category": "accessories", "stock": 50})
    assert post_res1.status_code == 200
    assert post_res2.status_code == 200
    # Act
    response = client.get("/items")
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["items"][0]["name"] == "Laptop"
    assert data["items"][1]["name"] == "Mouse"


def test_get_single_item():
    """تست دریافت یک آیتم خاص بر اساس ID"""
    # Arrange
    post_res = client.post("/items", json={"name": "Keyboard", "price": 75.0, "category": "accessories", "stock": 20})
    assert post_res.status_code == 200
    # Act
    response = client.get("/items/1")
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["item"]["name"] == "Keyboard"
    assert data["item"]["id"] == 1


def test_get_non_existent_item():
    """تست دریافت یک آیتم با ID ناموجود"""
    # Act
    response = client.get("/items/999")
    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_update_item():
    """تست به‌روزرسانی یک آیتم موجود"""
    # Arrange
    post_res = client.post("/items", json={"name": "Laptop", "price": 999.99, "category": "electronics", "stock": 10})
    assert post_res.status_code == 200
    update_data = {"price": 899.99, "stock": 5}
    # Act
    response = client.put("/items/1", json=update_data)
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Item updated successfully"
    assert data["item"]["price"] == 899.99
    assert data["item"]["stock"] == 5
    assert db.items_db[1]["price"] == 899.99
    assert db.items_db[1]["stock"] == 5


def test_update_non_existent_item():
    """تست به‌روزرسانی یک آیتم با ID ناموجود"""
    update_data = {"price": 10.0}
    response = client.put("/items/999", json=update_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_delete_item():
    """تست حذف یک آیتم از فروشگاه"""
    # Arrange
    post_res = client.post("/items", json={"name": "Laptop", "price": 999.99, "category": "electronics", "stock": 10})
    assert post_res.status_code == 200
    # Act
    response = client.delete("/items/1")
    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "Item removed successfully"
    assert 1 not in db.items_db
    # بررسی می‌کنیم که آیا آیتم حذف شده واقعاً از پایگاه داده پاک شده است
    response_get = client.get("/items/1")
    assert response_get.status_code == 404


def test_delete_non_existent_item():
    """تست حذف آیتم با ID ناموجود"""
    response = client.delete("/items/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


# ===============================================================
# تست‌های مدیریت سبد خرید (Cart Management)
# ===============================================================

def test_add_item_to_cart():
    """تست اضافه کردن یک آیتم به سبد خرید"""
    # Arrange
    post_res = client.post("/items", json={"name": "Laptop", "price": 999.99, "category": "electronics", "stock": 10})
    assert post_res.status_code == 200
    cart_item_data = {"item_id": 1, "quantity": 2}
    # Act
    response = client.post("/cart/add", json=cart_item_data)
    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "Item added to cart successfully"
    assert db.cart_db[1] == 2


def test_add_item_exceeding_stock():
    """تست اضافه کردن آیتم بیش از موجودی به سبد خرید"""
    # Arrange
    post_res = client.post("/items", json={"name": "Laptop", "price": 999.99, "category": "electronics", "stock": 5})
    assert post_res.status_code == 200
    cart_item_data = {"item_id": 1, "quantity": 10}
    # Act
    response = client.post("/cart/add", json=cart_item_data)
    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient stock"
    assert 1 not in db.cart_db


def test_add_non_existent_item_to_cart():
    """تست اضافه کردن آیتم ناموجود به سبد خرید"""
    cart_item_data = {"item_id": 999, "quantity": 1}
    response = client.post("/cart/add", json=cart_item_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found in store"


def test_remove_item_partially_from_cart():
    """تست کم کردن تعداد از یک آیتم در سبد خرید"""
    # Arrange
    post_res = client.post("/items", json={"name": "Laptop", "price": 1000.0, "category": "electronics", "stock": 10})
    assert post_res.status_code == 200
    add_cart_res = client.post("/cart/add", json={"item_id": 1, "quantity": 5})
    assert add_cart_res.status_code == 200
    # Act
    response = client.delete("/cart/items/1?quantity=2")
    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "Item quantity updated in cart successfully"
    assert db.cart_db[1] == 3


def test_remove_item_fully_from_cart():
    """تست حذف کامل یک آیتم از سبد خرید"""
    # Arrange
    post_res = client.post("/items", json={"name": "Laptop", "price": 1000.0, "category": "electronics", "stock": 10})
    assert post_res.status_code == 200
    add_cart_res = client.post("/cart/add", json={"item_id": 1, "quantity": 3})
    assert add_cart_res.status_code == 200
    # Act
    response = client.delete("/cart/items/1?quantity=3")
    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "Item fully removed from cart successfully"
    assert 1 not in db.cart_db


def test_remove_non_existent_item_from_cart():
    """تست حذف یک آیتم ناموجود از سبد خرید"""
    response = client.delete("/cart/items/999?quantity=1")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not in cart"


def test_remove_more_items_than_in_cart():
    """تست حذف تعداد بیشتر از موجودی آیتم در سبد خرید"""
    post_res = client.post("/items", json={"name": "Laptop", "price": 1000.0, "category": "electronics", "stock": 10})
    assert post_res.status_code == 200
    add_cart_res = client.post("/cart/add", json={"item_id": 1, "quantity": 3})
    assert add_cart_res.status_code == 200
    response = client.delete("/cart/items/1?quantity=5")
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot remove more items than are in the cart"


def test_get_cart_contents():
    """تست دریافت محتویات سبد خرید با محاسبه قیمت کل"""
    # Arrange
    post_res1 = client.post("/items", json={"name": "Laptop", "price": 1000.0, "category": "electronics", "stock": 10})
    post_res2 = client.post("/items", json={"name": "Mouse", "price": 50.0, "category": "accessories", "stock": 50})
    assert post_res1.status_code == 200
    assert post_res2.status_code == 200
    add_cart_res1 = client.post("/cart/add", json={"item_id": 1, "quantity": 2})
    add_cart_res2 = client.post("/cart/add", json={"item_id": 2, "quantity": 3})
    assert add_cart_res1.status_code == 200
    assert add_cart_res2.status_code == 200
    # Act
    response = client.get("/cart")
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total_price"] == 2150.0  # (2 * 1000) + (3 * 50)
    assert data["total_items"] == 5


# ===============================================================
# تست نهایی کردن خرید (Finalize Cart)
# ===============================================================

def test_finalize_cart():
    """تست نهایی کردن یک سبد خرید موفق"""
    # Arrange
    post_res1 = client.post("/items", json={"name": "Laptop", "price": 1000.0, "category": "electronics", "stock": 10})
    post_res2 = client.post("/items", json={"name": "Mouse", "price": 50.0, "category": "accessories", "stock": 50})
    assert post_res1.status_code == 200
    assert post_res2.status_code == 200
    add_cart_res1 = client.post("/cart/add", json={"item_id": 1, "quantity": 2})
    add_cart_res2 = client.post("/cart/add", json={"item_id": 2, "quantity": 3})
    assert add_cart_res1.status_code == 200
    assert add_cart_res2.status_code == 200

    # Act
    response = client.post("/cart/finalize")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Cart finalized successfully"

    # تأیید می‌کنیم که سبد خرید خالی شده است
    assert not db.cart_db

    # تأیید می‌کنیم که یک خرید جدید ثبت شده است
    assert len(db.purchases_db) == 1

    # تأیید می‌کنیم که موجودی کالاها به‌روز شده است
    assert db.items_db[1]["stock"] == 8  # 10 - 2
    assert db.items_db[2]["stock"] == 47  # 50 - 3

    # تأیید می‌کنیم که قیمت کل خرید درست است
    assert data["purchase"]["total_price"] == 2150.0


def test_finalize_empty_cart():
    """تست نهایی کردن یک سبد خرید خالی"""
    response = client.post("/cart/finalize")
    assert response.status_code == 400
    assert response.json()["detail"] == "Cart is empty"
