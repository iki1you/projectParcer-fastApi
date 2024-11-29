import asyncio
from functools import partial
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Field, SQLModel, create_engine, Session, select


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

class Item(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    price: str


app = FastAPI()
sqlite_url = "sqlite:///parser.db"
engine = create_engine(sqlite_url)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Depends(get_session)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


@app.on_event("startup")
async def startup_event():
    init_db()


async def add_item(item, session):
    if session.get(Item, item.id) is None:
        session.add(item)
        session.commit()
        session.refresh(item)


def background_parser(product, page_count):
    import time
    start = time.time()
    from parser import parser_maxidom
    products = parser_maxidom(product, page_count)
    end = time.time() - start
    print(f"Парсинг завершен за {round(end, 2)} с.")
    return products


def init_db():
    SQLModel.metadata.create_all(engine)


@app.post("/parse-items")
async def parse_items(item_name: str, page_count: int, session: Session = SessionDep):
    loop = asyncio.get_running_loop()
    sync_function_noargs = partial(background_parser, item_name, page_count)
    products = await loop.run_in_executor(None, sync_function_noargs)
    for p in products:
        item = Item(id=p[0], name=p[1], price=p[2])
        await add_item(item, session)
    return products


@app.get("/get-available-items")
async def get_available_items():
    return AVAILABLE_ITEMS


@app.get("/prices")
async def read_prices(session: Session = SessionDep, offset: int = 0, limit: int = 100):
    return session.exec(select(Item).offset(offset).limit(limit)).all()

@app.get("/prices/{item_id}")
async def read_item(item_id: int, session: Session = SessionDep):
    price = session.get(Item, item_id)
    if not price:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return price


@app.put("/prices/{item_id}")
async def update_item(item_id: int, data: Item, session: Session = SessionDep):
    price_db = session.get(Item, item_id)
    if not price_db:
        raise HTTPException(status_code=404, detail="Товар не найден")
    price_data = data.model_dump(exclude_unset=True)
    price_db.sqlmodel_update(price_data)
    session.add(price_db)
    session.commit()
    session.refresh(price_db)
    return price_db


@app.post("/prices/create")
async def create_item(item: Item, session: Session = SessionDep):
    await add_item(item, session)
    return item


@app.delete("/prices/{item_id}")
async def delete_item(item_id: int, session: Session = SessionDep):
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Товар не найден")
    session.delete(item)
    session.commit()
    return {"ok": True}
