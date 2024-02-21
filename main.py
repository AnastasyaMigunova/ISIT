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


async def download_image(url, directory, max_size=1024 * 1024):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

        if response.status_code == 200:
            image_name = str(uuid.uuid4()) + ".jpg"
            image_path = os.path.join(directory, image_name)

            if len(response.content) > max_size:
                with Image.open(BytesIO(response.content)) as img:
                    img.save(image_path, optimize=True, quality=70)

            with open(image_path, 'wb') as f:
                f.write(response.content)


async def process_page(url, directory):
    html = await fetch(url)
    image_urls = await extract_images(html)
    tasks = [download_image(img_url, directory) for img_url in image_urls]
    await asyncio.gather(*tasks)


async def crawler(start_url, directory, visited_urls, count):
    if start_url not in visited_urls:
        visited_urls.add(start_url)
        with open(VISITED_URLS_FILE, "a") as f:
            f.write(start_url + "\n")

        await process_page(start_url, directory)

    html = await fetch(start_url)
    soup = BeautifulSoup(html, 'html.parser')

    count += 1
    nextPage = soup.find("a", class_="pager__link", text=count).get("href")
    nextPageUrl = "https://wallpaperscraft.com" + nextPage

    task = crawler(nextPageUrl, directory, visited_urls, count)
    await asyncio.gather(task)


async def main():
    start_url = "https://wallpaperscraft.com/"

    directory = 'images'
    if not os.path.exists(directory):
        os.makedirs(directory)

    visited_urls = set()
    i = 1

    if os.path.exists(VISITED_URLS_FILE):
        with open(VISITED_URLS_FILE, "r") as f:
            visited_urls = set(f.read().splitlines())

    await crawler(start_url, directory, visited_urls, i)


if __name__ == "__main__":
    asyncio.run(main())
