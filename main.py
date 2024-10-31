import asyncio
from functools import partial
from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI()

PRICES_DB = []
AVAILABLE_ITEMS = [
    "kraski-i-emali", "dreli", "sadovaya-tehnika",
    "zapchasti-dlya-sadovoy-tehniki", "unitazy",
    "mebel-dlya-vannyh-komnat", "oborudovanie-dlya-dusha",
    "smesiteli", "filtry-dlya-vody", "otopitelnoe-oborudovanie",
    "inzhenernaya-santehnika", "ventilyatsionnoe-oborudovanie",
    "aksessuary-dlya-vannoy-komnaty", "izmeritelnyy-instrument",
    "organizatsiya-rabochego-mesta", "otvertki", "klyuchi-golovki",
    "udarno-rychazhnyy-instrument", "svarochnoe-oborudovanie",
    "grunty-propitki-olify", "malyarno-shtukaturnyy-instrument",
    "sredstva-zaschitnye-dlya-dereva", "vyklyuchateli",
    "rozetki-ramki-dlya-rozetok", "vse-dlya-elektromontazha",
    "udliniteli-setevye-filtry-ibp", "stulya",
    "melkaya-tehnika-dlya-kuhni", "posuda-i-pribory-dlya-vypechki"
]

class Item(BaseModel):
    id: str
    name: str
    price: str


def background_parser(product, page_count):
    import time
    start = time.time()
    from parser import parser_maxidom
    products = parser_maxidom(product, page_count)
    end = time.time() - start
    print(f"Парсинг завершен за {round(end, 2)} с.")
    return products


@app.post("/parse-items")
async def parse_items(item_name: str, page_count: int):
    loop = asyncio.get_running_loop()
    sync_function_noargs = partial(background_parser, item_name, page_count)
    products = await loop.run_in_executor(None, sync_function_noargs)
    for p in products:
        item = Item(id=p[0], name=p[1], price=p[2])
        if item not in PRICES_DB:
            PRICES_DB.append(item)
            print(1)
    return products


@app.get("/get-available-items")
async def get_available_items():
    return AVAILABLE_ITEMS


@app.get("/prices_async")
async def read_prices():
    return PRICES_DB


@app.get("/prices/{item_id}")
async def read_item(item_id: int):
    return PRICES_DB[item_id]


@app.put("/prices/{item_id}")
async def update_item(item_id: int, data: Item):
    PRICES_DB[item_id] = data
    return PRICES_DB[item_id]


@app.post("/prices/create")
async def create_item(item: Item):
    PRICES_DB.append(item)
    return PRICES_DB[-1]


@app.delete("/prices/{item_id}")
async def delete_item(item_id: int):
    try:
        item = PRICES_DB[item_id]
        PRICES_DB.remove(item)
        return {"status": "ok"}
    except IndexError as e:
        return {"error": str(e)}