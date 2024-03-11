import os


class Context:
    visitedPages = set()
    startUrl = "https://wallpaperscraft.com"
    directory = 'images'

    def init_visited_pages(self):
        if os.path.exists("visited_urls.txt"):
            with open("visited_urls.txt", "r") as f:
                self.visitedPages = set(f.read().splitlines())

    def make_directory(self):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)


ctx = Context()