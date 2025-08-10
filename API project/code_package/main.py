from fastapi import FastAPI, Path
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    description: str
    price: float = Path(gt= 0)
    category: str
    stock: int = Path(ge=0)


@app.get("/test")
def root(item: Item):
    return item

