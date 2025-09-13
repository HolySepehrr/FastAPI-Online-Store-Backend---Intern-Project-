# main.py (نسخه نهایی و قطعی)

from fastapi import FastAPI, Path, HTTPException, Query, Depends
from pydantic import BaseModel, Field
import sqlite3
from contextlib import asynccontextmanager

# نام دیتابیس به عنوان یک متغیر سراسری تعریف می‌شود تا در تست‌ها قابل تغییر باشد
DATABASE = 'database.db'

def get_db_connection():
    """یک کانکشن جدید به دیتابیس برمی‌گرداند."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    """جداول را فقط یک بار در دیتابیس مشخص شده ایجاد می‌کند."""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            description TEXT, price REAL NOT NULL, category TEXT, stock INTEGER NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            item_id INTEGER PRIMARY KEY, quantity INTEGER NOT NULL,
            FOREIGN KEY (item_id) REFERENCES items (item_id)
        )
    ''')
    conn.commit()
    conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """مدیریت چرخه حیات اپلیکیشن برای اجرای کد در استارتاپ."""
    setup_database()
    yield

app = FastAPI(lifespan=lifespan)

def get_db():
    """Dependency برای مدیریت خودکار باز و بسته کردن کانکشن‌ها."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

# --- مدل‌های Pydantic ---
class Item(BaseModel):
    name: str; description: str | None = None; price: float = Field(gt=0); category: str; stock: int = Field(ge=0)
class ItemUpdate(BaseModel):
    name: str | None = None; description: str | None = None; price: float | None = Field(None, gt=0); category: str | None = None; stock: int | None = Field(None, ge=0)
class CartItem(BaseModel):
    item_id: int; quantity: int = Field(gt=0)

# --- Endpoints ---
@app.post("/items", tags=[" Items Management"])
def add_item_endpoint(item: Item, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO items (name, description, price, category, stock) VALUES (?, ?, ?, ?, ?)", (item.name, item.description, item.price, item.category, item.stock))
    new_item_id = cursor.lastrowid
    conn.commit()
    return {"message": "Item added successfully", "item_id": new_item_id}

@app.get("/items", tags=[" Items Management"])
def get_all_items(conn: sqlite3.Connection = Depends(get_db)):
    items = conn.execute("SELECT * FROM items").fetchall()
    return {"items": [dict(row) for row in items]}

# ... (بقیه endpoint های شما هم به همین شکل صحیح هستند و نیازی به تغییر ندارند)
@app.get("/items/{item_id}", tags=[" Items Management"])
def get_single_item(item_id: int = Path(..., gt=0), conn: sqlite3.Connection = Depends(get_db)):
    item = conn.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()
    if not item: raise HTTPException(status_code=404, detail="Item not found")
    return {"item": dict(item)}

@app.put("/items/{item_id}", tags=[" Items Management"])
def update_item_endpoint(item_id: int, item_update: ItemUpdate, conn: sqlite3.Connection = Depends(get_db)):
    update_data = item_update.model_dump(exclude_unset=True)
    if not update_data: raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()]); values = list(update_data.values()); values.append(item_id)
    cursor = conn.cursor()
    if not cursor.execute("SELECT item_id FROM items WHERE item_id = ?", (item_id,)).fetchone(): raise HTTPException(status_code=404, detail="Item not found")
    cursor.execute(f"UPDATE items SET {set_clause} WHERE item_id = ?", tuple(values))
    conn.commit()
    return {"message": "Item updated successfully"}

@app.delete("/items/{item_id}", tags=[" Items Management"])
def remove_item_endpoint(item_id: int, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    if not cursor.execute("SELECT item_id FROM items WHERE item_id = ?", (item_id,)).fetchone(): raise HTTPException(status_code=404, detail="Item not found")
    cursor.execute("DELETE FROM items WHERE item_id = ?", (item_id,)); cursor.execute("DELETE FROM cart WHERE item_id = ?", (item_id,))
    conn.commit()
    return {"message": "Item removed successfully"}

@app.post("/cart/add", tags=[" Cart Management"])
def add_item_to_cart_endpoint(cart_item: CartItem, conn: sqlite3.Connection = Depends(get_db)):
    item = conn.execute("SELECT stock FROM items WHERE item_id = ?", (cart_item.item_id,)).fetchone()
    if not item: raise HTTPException(status_code=404, detail="Item not found in store")
    if item["stock"] < cart_item.quantity: raise HTTPException(status_code=400, detail="Insufficient stock")
    conn.execute("INSERT INTO cart (item_id, quantity) VALUES (?, ?) ON CONFLICT(item_id) DO UPDATE SET quantity = quantity + excluded.quantity;",(cart_item.item_id, cart_item.quantity))
    conn.commit()
    return {"message": "Item added to cart successfully"}

@app.get("/cart", tags=[" Cart Management"])
def get_cart_contents_endpoint(conn: sqlite3.Connection = Depends(get_db)):
    cart_items = conn.execute("SELECT i.item_id, i.name, i.price, c.quantity FROM cart c JOIN items i ON c.item_id = i.item_id").fetchall()
    items_list = [{"item_id": r["item_id"], "name": r["name"], "price": r["price"], "quantity": r["quantity"], "subtotal": r["price"] * r["quantity"]} for r in cart_items]
    return {"items": items_list, "total_items": sum(r["quantity"] for r in items_list), "total_price": sum(r["subtotal"] for r in items_list)}

@app.delete("/cart/items/{item_id}", tags=[" Cart Management"])
def remove_item_from_cart_endpoint(item_id: int, quantity: int = Query(..., gt=0), conn: sqlite3.Connection = Depends(get_db)):
    cart_item = conn.execute("SELECT quantity FROM cart WHERE item_id = ?", (item_id,)).fetchone()
    if not cart_item: raise HTTPException(status_code=404, detail="Item not in cart")
    if quantity >= cart_item["quantity"]: conn.execute("DELETE FROM cart WHERE item_id = ?", (item_id,))
    else: conn.execute("UPDATE cart SET quantity = quantity - ? WHERE item_id = ?", (quantity, item_id))
    conn.commit()
    return {"message": "Cart updated successfully"}

@app.post("/cart/finalize", tags=[" Cart Management"])
def finalize_cart_endpoint(conn: sqlite3.Connection = Depends(get_db)):
    cart_items = conn.execute("SELECT c.item_id, c.quantity, i.stock FROM cart c JOIN items i ON c.item_id = i.item_id").fetchall()
    if not cart_items: raise HTTPException(status_code=400, detail="Cart is empty")
    try:
        for item in cart_items:
            if item["stock"] < item["quantity"]: raise ValueError(f"Insufficient stock for item ID {item['item_id']}")
            new_stock = item["stock"] - item["quantity"]; conn.execute("UPDATE items SET stock = ? WHERE item_id = ?", (new_stock, item["item_id"]))
        conn.execute("DELETE FROM cart")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to finalize purchase: {e}")
    return {"message": "Cart finalized successfully, stock updated."}