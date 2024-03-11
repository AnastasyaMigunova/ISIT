import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from ISIT.config import config

load_dotenv()


class Context:
    visitedPages = set()
    startUrl = os.getenv("START_URL")
    directory = os.getenv("DIRECTORY")
    visited_urls = config.VISITED_URLS

    engine = create_async_engine(os.getenv("DATABASE_URL"))
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, future=True)

    def init_visited_pages(self):
        if os.path.exists(self.visited_urls):
            with open(self.visited_urls, "r") as f:
                self.visitedPages = set(f.read().splitlines())

    def make_directory(self):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)


ctx = Context()