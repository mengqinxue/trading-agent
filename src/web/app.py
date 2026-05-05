"""FastAPI Web 应用"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path

from .routes import tasks, chat, catalog


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    yield


app = FastAPI(
    title="Trading Agent",
    description="A股交易辅助系统 - LangGraph 多 agent 分析",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(catalog.router, prefix="/api/catalog", tags=["catalog"])


@app.get("/api/stocks/{code}/name")
async def get_stock_name(code: str):
    """获取股票名称 - 使用 DataAdapter 统一接口"""
    from src.data.data_adapter import get_adapter

    adapter = get_adapter()
    name = adapter.get_stock_info(code).get("name", "未知")

    return {"code": code, "name": name}

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """主页"""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Trading Agent</h1><p>Web界面正在建设中...</p>")