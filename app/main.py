import logging
import os
import asyncio
import hashlib
from io import BytesIO
from dotenv import load_dotenv
import httpx
from PIL import Image
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from ISIT.app.model.imageData import ImageData
from ISIT.config import config

load_dotenv()


engine = create_async_engine(os.getenv("DATABASE_URL"))
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, future=True)


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


async def download_image(url, directory, semaphore):
    async with semaphore:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)

            if response.status_code == 200:
                compressed_data = await compress_image(response.content)
                checksum = hashlib.md5(compressed_data).hexdigest()

                image_path = os.path.join(directory, f"{checksum}.jpg")
                with open(image_path, "wb") as f:
                    f.write(compressed_data)

                async with async_session.begin() as session:
                    try:
                        image = ImageData(id=checksum, data=image_path)
                        session.add(image)
                        await session.commit()
                    except Exception as e:
                        await session.rollback()
                        logging.error(f"Error adding image to the database: {e}")


async def process_page(url, number, directory):
    html = await fetch(url)
    image_urls = await extract_images_urls(html)

    tasks = []
    semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_TASKS)
    for img_url in image_urls[:number]:
        tasks.append(download_image(img_url, directory, semaphore))

    currentNumber = number - len(image_urls)
    if currentNumber < 0:
        currentNumber = 0

    await asyncio.gather(*tasks)
    return currentNumber


async def crawler(next_url, directory, visited_urls, count, number, start_url):
    currentNumber = number

    if next_url not in visited_urls:
        try:
            currentNumber = await process_page(next_url, number, directory)
            visited_urls.add(next_url)
            with open('visited_urls.txt', "a") as f:
                f.write(next_url + "\n")
        except Exception as e:
            logging.warning(f"Error processing page {next_url}: {e}")
    else:
        logging.info(f"This page {next_url} has been visited")

    if currentNumber > 0:
        count += 1
        html = await fetch(next_url)
        soup = BeautifulSoup(html, 'html.parser')

        nextPage = soup.find("a", class_="pager__link", string=str(count))
        if nextPage:
            next_url = start_url + nextPage.get("href")
            await crawler(next_url, directory, visited_urls, count, currentNumber, start_url)
        else:
            logging.warning("Page not found")
    else:
        logging.info("The required number of images has been downloaded")
        return


async def main(next_url, directory, number: int, visited_urls, start_url):

    if not os.path.exists(directory):
        os.makedirs(directory)

    await crawler(next_url, directory, visited_urls, 1, number, start_url)
