import os
import asyncio
import uuid
from io import BytesIO

import httpx
from PIL import Image
from bs4 import BeautifulSoup

VISITED_URLS_FILE = 'visited_urls.txt'


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


async def download_image(url, directory, image_name, max_size=1024 * 1024):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

        if response.status_code == 200:
            image_path = os.path.join(directory, image_name)

            if len(response.content) > max_size:
                with Image.open(BytesIO(response.content)) as img:
                    img.save(image_path, optimize=True, quality=70)

            with open(image_path, 'wb') as f:
                f.write(response.content)


async def process_page(url, directory, number):
    currentNumber = number
    html = await fetch(url)
    image_urls = await extract_images(html)

    if len(image_urls) < currentNumber:
        currentNumber -= len(image_urls)
    else:
        image_urls = image_urls[:number]
        currentNumber = 0

    for index, img_url in enumerate(image_urls):
        image_name = f"{index}_{uuid.uuid4()}.jpg"
        await download_image(img_url, directory, image_name, number)

    return currentNumber


async def crawler(start_url, directory, visited_urls, count, number):
    currentNumber = number

    if start_url not in visited_urls:
        visited_urls.add(start_url)
        with open(VISITED_URLS_FILE, "a") as f:
            f.write(start_url + "\n")

        currentNumber = await process_page(start_url, directory, number)

    if currentNumber > 0:
        html = await fetch(start_url)
        soup = BeautifulSoup(html, 'html.parser')

        count += 1
        nextPage = soup.find("a", class_="pager__link", string=str(count))
        if nextPage:
            nextPageUrl = "https://wallpaperscraft.com" + nextPage.get("href")
            await crawler(nextPageUrl, directory, visited_urls, count, number)
        else:
            print("Страница не найдена")
    else:
        print("Нужное количество изображений скачено")


async def main(number: int):
    start_url = "https://wallpaperscraft.com/"

    directory = 'images'
    if not os.path.exists(directory):
        os.makedirs(directory)

    visited_urls = set()
    i = 1

    if os.path.exists(VISITED_URLS_FILE):
        with open(VISITED_URLS_FILE, "r") as f:
            visited_urls = set(f.read().splitlines())

    await crawler(start_url, directory, visited_urls, i, number)


if __name__ == "__main__":
    asyncio.run(main(number=10))
