import logging
import os
import asyncio
import hashlib
from io import BytesIO
from dotenv import load_dotenv
import httpx
from PIL import Image
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ISIT.app.model.imageData import ImageData, Base
from ISIT.config import config

load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"))
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()


async def fetch(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text


async def extract_images_urls(html):
    soup = BeautifulSoup(html, 'html.parser')

    image_urls = []
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and (src.startswith('http://') or src.startswith('https://')) and src.endswith('.jpg'):
            image_urls.append(src)

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


async def download_image(url, session, directory):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

        if response.status_code == 200:
            compressed_data = await compress_image(response.content)
            checksum = hashlib.md5(compressed_data).hexdigest()

            image_path = os.path.join(directory, f"{checksum}.jpg")
            with open(image_path, "wb") as f:
                f.write(compressed_data)

            image = ImageData(id=checksum, data=image_path)
            session.add(image)


async def process_page(url, session, number, directory):
    html = await fetch(url)
    image_urls = await extract_images_urls(html)

    tasks = []
    semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_TASKS)
    for img_url in image_urls[:number]:
        async with semaphore:
            tasks.append(download_image(img_url, session, directory))

    currentNumber = number - len(image_urls)
    if currentNumber < 0:
        currentNumber = 0

    await asyncio.gather(*tasks)
    return currentNumber


async def crawler(start_url, directory, session, visited_urls, count, number):
    currentNumber = number

    if start_url not in visited_urls:
        try:
            currentNumber = await process_page(start_url, session, number, directory)
            visited_urls.add(start_url)
            with open('visited_urls.txt', "a") as f:
                f.write(start_url + "\n")
        except Exception as e:
            logging.warning(f"Error processing page {start_url}: {e}")
    else:
        logging.info(f"This page {start_url} has been visited")

    if currentNumber > 0:
        count += 1
        html = await fetch(start_url)
        soup = BeautifulSoup(html, 'html.parser')

        nextPage = soup.find("a", class_="pager__link", string=str(count))
        if nextPage:
            nextPageUrl = "https://wallpaperscraft.com" + nextPage.get("href")
            await crawler(nextPageUrl, directory, session, visited_urls, count, number)
        else:
            logging.warning("Page not found")
    else:
        logging.info("The required number of images has been downloaded")


async def main(number: int, directory):
    start_url = "https://wallpaperscraft.com/"
    visited_urls = set()
    i = 1

    if not os.path.exists(directory):
        os.makedirs(directory)

    if os.path.exists('visited_urls.txt'):
        with open('visited_urls.txt', "r") as f:
            visited_urls = set(f.read().splitlines())

    await crawler(start_url, directory, session, visited_urls, i, number)
    session.commit()
    session.close()


if __name__ == "__main__":
    asyncio.run(main(number=10, directory="images"))
