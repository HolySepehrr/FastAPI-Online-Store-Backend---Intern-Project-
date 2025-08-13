from fastapi import FastAPI, Path, HTTPException, Query
from pydantic import BaseModel, Field
import datetime



# متغیرهای سراسری را در یک ماژول یا فایل جداگانه تعریف می‌کنیم
# تا توسط تست‌ها قابل اشتراک و ریست شدن باشند.
class GlobalDB:
    def __init__(self):
        self.items_db = {}
        self.cart_db = {}
        self.item_id_counter = 0
        self.purchases_db = {}
        self.purchase_id_counter = 0


db = GlobalDB()

app = FastAPI()


class Item(BaseModel):
    name: str
    description: str | None = None
    price: float = Field(gt=0)
    category: str
    stock: int = Field(ge=0)


# یک مدل جدید برای به‌روزرسانی آیتم‌ها با فیلدهای اختیاری
class ItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = Field(None, gt=0)
    category: str | None = None
    stock: int | None = Field(None, ge=0)


class CartItem(BaseModel):
    item_id: int
    quantity: int = Field(gt=0)


@app.post("/items", tags=[" Items Management"])
def add_item_endpoint(item: Item):
    db.item_id_counter += 1
    item_with_id = item.model_dump()
    item_with_id["id"] = db.item_id_counter
    db.items_db[db.item_id_counter] = item_with_id
    return {"message": "Item added successfully", "item": item_with_id}


@app.get("/items", tags=[" Items Management"])
def get_all_items():
    return {"items": list(db.items_db.values())}


@app.get("/items/{item_id}", tags=[" Items Management"])
def get_single_item(item_id: int = Path(..., gt=0)):
    if item_id not in db.items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item": db.items_db[item_id]}


@app.put("/items/{item_id}", tags=[" Items Management"])
def update_item_endpoint(item_id: int = Path(..., gt=0), item_update: ItemUpdate = ...):
    if item_id not in db.items_db:
        raise HTTPException(status_code=404, detail="Item not found")

    existing_item = db.items_db[item_id]
    updated_data = item_update.model_dump(exclude_unset=True)
    existing_item.update(updated_data)

    return {"message": "Item updated successfully", "item": existing_item}


@app.delete("/items/{item_id}", tags=[" Items Management"])
def remove_item_endpoint(item_id: int = Path(..., gt=0)):
    if item_id not in db.items_db:
        raise HTTPException(status_code=404, detail="Item not found")

    del db.items_db[item_id]

    if item_id in db.cart_db:
        del db.cart_db[item_id]

    return {"message": "Item removed successfully"}


@app.post("/cart/add", tags=[" Cart Management"])
def add_item_to_cart_endpoint(cart_item: CartItem):
    if cart_item.item_id not in db.items_db:
        raise HTTPException(status_code=404, detail="Item not found in store")

    item = db.items_db[cart_item.item_id]
    if item["stock"] < cart_item.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    current_quantity = db.cart_db.get(cart_item.item_id, 0)
    db.cart_db[cart_item.item_id] = current_quantity + cart_item.quantity

    return {"message": "Item added to cart successfully"}


@app.get("/cart", tags=[" Cart Management"])
def get_cart_contents_endpoint():
    cart_items_list = []
    total_price = 0
    total_items_count = 0

    for item_id, quantity in db.cart_db.items():
        if item_id in db.items_db:
            item_details = db.items_db[item_id]
            subtotal = item_details["price"] * quantity
            total_price += subtotal
            total_items_count += quantity

            cart_items_list.append({
                "item_id": item_id,
                "name": item_details["name"],
                "price": item_details["price"],
                "quantity": quantity,
                "subtotal": subtotal
            })

    return {
        "items": cart_items_list,
        "total_items": total_items_count,
        "total_price": total_price
    }


@app.delete("/cart/items/{item_id}", tags=[" Cart Management"])
def remove_item_from_cart_endpoint(item_id: int = Path(..., gt=0), quantity: int = Query(..., gt=0)):
    if item_id not in db.cart_db:
        raise HTTPException(status_code=404, detail="Item not in cart")

    current_quantity_in_cart = db.cart_db[item_id]

    if quantity > current_quantity_in_cart:
        raise HTTPException(status_code=400, detail="Cannot remove more items than are in the cart")

    if quantity == current_quantity_in_cart:
        del db.cart_db[item_id]
        return {"message": "Item fully removed from cart successfully"}

    else:
        db.cart_db[item_id] -= quantity
        return {"message": "Item quantity updated in cart successfully"}


@app.post("/cart/finalize", tags=[" Cart Management"])
def finalize_cart_endpoint():
    if not db.cart_db:
        raise HTTPException(status_code=400, detail="Cart is empty")

    db.purchase_id_counter += 1
    new_purchase = {
        "id": db.purchase_id_counter,
        "items": [],
        "timestamp": str(datetime.datetime.now()),
        "total_price": 0
    }

    total_price = 0

    for item_id, quantity in db.cart_db.items():
        if item_id not in db.items_db:
            raise HTTPException(status_code=500,
                                detail=f"Item with ID {item_id} not found in store, cannot finalize cart.")

        item_details = db.items_db[item_id]
        item_details["stock"] -= quantity

        subtotal = item_details["price"] * quantity
        total_price += subtotal
        new_purchase["items"].append({
            "item_id": item_id,
            "name": item_details["name"],
            "price": item_details["price"],
            "quantity": quantity,
            "subtotal": subtotal
        })

    new_purchase["total_price"] = total_price

    db.purchases_db[db.purchase_id_counter] = new_purchase

    db.cart_db.clear()

    return {"message": "Cart finalized successfully", "purchase": new_purchase}
