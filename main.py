import json
import nats
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import Field, SQLModel, create_engine, select
from sqlmodel.ext.asyncio.session import AsyncSession, Session
from starlette.websockets import WebSocket, WebSocketDisconnect


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



class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def message_handler(self, msg):
        subject = msg.subject
        reply = msg.reply
        data = msg.data.decode()
        print("Received a message on '{subject} {reply}': {data}".format(
            subject=subject, reply=reply, data=data))
        await self.broadcast(data)

    async def init(self):
        # await manager.broadcast(item.model_dump_json())
        self.nc = await nats.connect("nats://127.0.0.1:4222")
        # Simple publisher and async subscriber via coroutine.
        await self.nc.subscribe("create_item", cb=self.message_handler)
        await self.nc.subscribe("update_item", cb=self.message_handler)
        await self.nc.subscribe("delete_item", cb=self.message_handler)
        await self.nc.subscribe("parsing", cb=self.message_handler)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    async def broadcast(self, data: str):
        for conn in self.connections:
            await conn.send_text(data)


manager = ConnectionManager()
sqlite_url = "sqlite:///parser.db"
engine = create_engine(sqlite_url)


class Item(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    price: str


app = FastAPI()


def get_async_session():
    sqlite_url = "sqlite+aiosqlite:///parser.db"
    engine_2 = create_async_engine(sqlite_url)
    dbsession = async_sessionmaker(engine_2)
    return dbsession()


async def get_session():
    async with get_async_session() as session:
        yield session

SessionDep = Depends(get_session)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


@app.on_event("startup")
async def startup_event():
    init_db()
    await manager.init()


async def add_item(item, session):
    if await session.get(Item, item.id) is None:
        session.add(item)
        await session.commit()
        await session.refresh(item)


async def background_parser(product, page_count):
    import time
    start = time.time()
    from parser import parser_maxidom
    products = await parser_maxidom(product, page_count, manager)
    end = time.time() - start
    await manager.nc.publish("parsing", f"Парсинг завершен за {round(end, 2)} с.".encode())

    return products


def init_db():
    SQLModel.metadata.create_all(engine)


@app.post("/parse-items")
async def parse_items(item_name: str, page_count: int, session: AsyncSession = SessionDep):
    #loop = asyncio.get_running_loop()

    #sync_function_noargs = partial(background_parser, item_name, page_count)
    #products = await loop.run_in_executor(None, sync_function_noargs)

    products = await background_parser(item_name, page_count)

    for p in products:
        item = Item(id=p[0], name=p[1], price=p[2])
        await add_item(item, session)
    return products


@app.get("/get-available-items")
async def get_available_items():
    return AVAILABLE_ITEMS


@app.get("/prices")
async def read_prices(session: AsyncSession = SessionDep, offset: int = 0, limit: int = 100):
    return (await session.execute(select(Item).offset(offset).limit(limit))).scalars().all()


@app.get("/prices/{item_id}")
async def read_item(item_id: int, session: AsyncSession = SessionDep):
    price = await session.get(Item, item_id)
    if not price:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return price


@app.put("/prices/{item_id}")
async def update_item(item_id: int, data: Item, session: AsyncSession = SessionDep):
    price_db = await session.get(Item, item_id)
    if not price_db:
        raise HTTPException(status_code=404, detail="Товар не найден")
    price_data = data.model_dump(exclude_unset=True)
    price_db.sqlmodel_update(price_data)
    session.add(price_db)
    await session.commit()
    await session.refresh(price_db)


    data = json.dumps(data.model_dump())
    await manager.nc.publish("update_item", data.encode())

    return price_db


@app.post("/prices/create")
async def create_item(item: Item, session: AsyncSession = SessionDep):
    await add_item(item, session)

    data = json.dumps(item.model_dump())
    await manager.nc.publish("create_item", data.encode())
    return item


@app.delete("/prices/{item_id}")
async def delete_item(item_id: int, session: AsyncSession = SessionDep):
    item = await session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Товар не найден")
    await session.delete(item)
    await session.commit()

    data = json.dumps(item.model_dump())
    await manager.nc.publish("delete_item", data.encode())

    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(data)
    except WebSocketDisconnect:
        print(f"Client {websocket} disconnected")
