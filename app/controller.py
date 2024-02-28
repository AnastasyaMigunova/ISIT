from fastapi import FastAPI

from ISIT.app import main

app = FastAPI()


@app.post("/number_images")
async def scrapingImages(number: int):
    await main.main(number, directory="images")
    return {"message": "scraping successfully"}
