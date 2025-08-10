from fastapi import FastAPI, Path
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    description: str
    price: float = Path(gt= 0)
    category: str
    stock: int = Path(ge=0)

@app.post("/item")
def add_item_endpoint(item: Item):
    pass


@app.get("/items")
def get_all_items(item: Item):
    pass

@app.get("/items/{item_id}")
def get_single_item(item: Item, item_id: int):
    pass

@app.put("/item/{item_id}")
def update_item_endpoint(item: Item):
    pass


@app.delete("/item/{item_id}")
def remove_item_endpoint(item: Item):
    pass

@app.post("/cart/add")
def add_item_to_cart_endpoint(item: Item):
    pass

@app.get("/cart")
def get_cart_contents_endpoint(item: Item):
    pass

@app.delete("/cart/items/{item_id}")
def remove_item_from_cart_endpoint(item: Item):
    pass