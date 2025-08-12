from fastapi import FastAPI, Path, HTTPException, Query
from pydantic import BaseModel, Field
import datetime

app = FastAPI()

items_db = {}
cart_db = {}
item_id_counter = 0

purchases_db = {}
purchase_id_counter = 0


class Item(BaseModel):
    name: str
    description: str | None = None
    price: float = Field(gt=0)
    category: str
    stock: int = Field(ge=0)


class CartItem(BaseModel):
    item_id: int
    quantity: int = Field(gt=0)


@app.post("/items", tags=[" Items Management"])
def add_item_endpoint(item: Item):
    global item_id_counter
    item_id_counter += 1
    item_with_id = item.model_dump()
    item_with_id["id"] = item_id_counter
    items_db[item_id_counter] = item_with_id
    return {"message": "Item added successfully", "item": item_with_id}


@app.get("/items", tags=[" Items Management"])
def get_all_items():
    return {"items": list(items_db.values())}


@app.get("/items/{item_id}", tags=[" Items Management"])
def get_single_item(item_id: int = Path(..., gt=0)):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item": items_db[item_id]}


@app.put("/items/{item_id}", tags=[" Items Management"])
def update_item_endpoint(item_id: int, item_update: Item):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")

    existing_item = items_db[item_id]
    updated_data = item_update.model_dump(exclude_unset=True)
    existing_item.update(updated_data)

    return {"message": "Item updated successfully", "item": existing_item}


@app.delete("/items/{item_id}", tags=[" Items Management"])
def remove_item_endpoint(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")

    del items_db[item_id]

    if item_id in cart_db:
        del cart_db[item_id]

    return {"message": "Item removed successfully"}


@app.post("/cart/add", tags=[" Cart Management"])
def add_item_to_cart_endpoint(cart_item: CartItem):
    if cart_item.item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found in store")

    item = items_db[cart_item.item_id]
    if item["stock"] < cart_item.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    current_quantity = cart_db.get(cart_item.item_id, 0)
    cart_db[cart_item.item_id] = current_quantity + cart_item.quantity

    return {"message": "Item added to cart successfully"}


@app.get("/cart", tags=[" Cart Management"])
def get_cart_contents_endpoint():
    cart_items_list = []
    total_price = 0
    total_items_count = 0

    for item_id, quantity in cart_db.items():
        if item_id in items_db:
            item_details = items_db[item_id]
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
def remove_item_from_cart_endpoint(item_id: int, quantity: int = Query(..., gt=0)):
    if item_id not in cart_db:
        raise HTTPException(status_code=404, detail="Item not in cart")

    current_quantity_in_cart = cart_db[item_id]

    if quantity > current_quantity_in_cart:
        raise HTTPException(status_code=400, detail="Cannot remove more items than are in the cart")

    if quantity == current_quantity_in_cart:
        del cart_db[item_id]
        return {"message": "Item fully removed from cart successfully"}

    else:
        cart_db[item_id] -= quantity
        return {"message": "Item quantity updated in cart successfully"}


@app.post("/cart/finalize", tags=[" Cart Management"])
def finalize_cart_endpoint():
    global purchase_id_counter

    if not cart_db:
        raise HTTPException(status_code=400, detail="Cart is empty")

    purchase_id_counter += 1
    new_purchase = {
        "id": purchase_id_counter,
        "items": [],
        "timestamp": str(datetime.datetime.now()),
        "total_price": 0
    }

    total_price = 0

    for item_id, quantity in cart_db.items():
        if item_id not in items_db:
            raise HTTPException(status_code=500,
                                detail=f"Item with ID {item_id} not found in store, cannot finalize cart.")

        item_details = items_db[item_id]
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

    purchases_db[purchase_id_counter] = new_purchase

    cart_db.clear()

    return {"message": "Cart finalized successfully", "purchase": new_purchase}
