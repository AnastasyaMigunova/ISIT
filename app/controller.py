from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
import main
from ISIT.app.context import ctx

router = APIRouter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx.make_directory()
    ctx.init_visited_pages()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)


@app.post("/imageCount")
async def scrapeImages(imageCount: int):
    await main.main(next_url=ctx.startUrl,
                    directory=ctx.directory,
                    number=imageCount,
                    visited_urls=ctx.visitedPages,
                    start_url=ctx.startUrl,
                    session=ctx.async_session)
    return {"message": "scraping is successful"}
