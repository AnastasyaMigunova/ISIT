import base64
import logging
import os
import asyncio
import hashlib
from io import BytesIO

import httpx
from PIL import Image
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from model.imageData import ImageData, Base

VISITED_URLS_FILE = 'visited_urls.txt'
DATABASE_URL = "postgresql://postgres:migunova1405@localhost:5432/test"


async def fetch(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text


async def extract_images(html):
    soup = BeautifulSoup(html, 'html.parser')
    image_urls = [img['src'] for img in soup.find_all('img') if
                  (img['src'].startswith('http://') or img['src'].startswith('https://')) and img['src'].endswith(
                      '.jpg')]
    return image_urls


async def compress_image(image, max_size=1024 * 1024):
    img = Image.open(BytesIO(image))
    width, height = img.size
    if width * height > max_size:
        img.thumbnail(max_size)
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        return buffer.getvalue()
    return image


async def download_image(url, session):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

        if response.status_code == 200:
            compressed_data = await compress_image(response.content)
            checksum = hashlib.md5(compressed_data).hexdigest()
            imageBase64 = base64.b64encode(compressed_data).decode('utf-8')
            image = ImageData(id=checksum, data=imageBase64)
            session.add(image)


async def process_page(url, session, number):
    currentNumber = number
    html = await fetch(url)
    image_urls = await extract_images(html)

    if len(image_urls) < currentNumber:
        currentNumber -= len(image_urls)
    else:
        image_urls = image_urls[:number]
        currentNumber = 0

    tasks = []
    for img_url in image_urls:
        tasks.append(download_image(img_url, session))

    await asyncio.gather(*tasks)
    return currentNumber


async def crawler(start_url, session, visited_urls, count, number):
    currentNumber = number

    if start_url not in visited_urls:
        visited_urls.add(start_url)
        with open(VISITED_URLS_FILE, "a") as f:
            f.write(start_url + "\n")

        currentNumber = await process_page(start_url, session, number)

    if currentNumber > 0:
        count += 1
        html = await fetch(start_url)
        soup = BeautifulSoup(html, 'html.parser')

        nextPage = soup.find("a", class_="pager__link", string=str(count))
        if nextPage:
            nextPageUrl = "https://wallpaperscraft.com" + nextPage.get("href")
            await crawler(nextPageUrl, session, visited_urls, count, number)
        else:
            logging.info("Page not found")
    else:
        logging.info("The required number of images has been downloaded")


async def main(number: int):
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    start_url = "https://wallpaperscraft.com/"
    visited_urls = set()
    i = 1

    if os.path.exists(VISITED_URLS_FILE):
        with open(VISITED_URLS_FILE, "r") as f:
            visited_urls = set(f.read().splitlines())

    await crawler(start_url, session, visited_urls, i, number)
    session.commit()
    session.close()


if __name__ == "__main__":
    asyncio.run(main(number=10))
