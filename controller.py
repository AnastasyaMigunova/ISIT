from fastapi import FastAPI

import main

app = FastAPI()


@app.post("/number_images")
async def scrapingImages(number: int):
    await main.main(number)
    return {"message": "scraping successfully"}
