from typing import Optional, Dict, List
import requests
from discord.ext import commands

REMY_URL = "https://remywiki.com"
REMY_API = f"{REMY_URL}/api.php"
REMY_HEADERS = {"User-Agent": "OhioDDR-honkbot"}

# Overview: This code is used primarily for taking a song name and returning an image of the jacket or banner for that song from RemyWiki.
# This now uses the MediaWiki API to query pages directly instead of scraping HTML with BeautifulSoup.


def page_is_song(title: str) -> bool:
    """
    Checks if a page belongs to the Songs category using the MediaWiki API.
    
    Uses the MediaWiki API to resolve song category membership.
    
    :param title: The title of the page to check
    :return: True if the page is in the Songs category, False otherwise
    """
    params = {
        "action": "query",
        "format": "json",
        "prop": "categories",
        "titles": title,
        "formatversion": "2"
    }
    try:
        response = requests.get(REMY_API, params=params, headers=REMY_HEADERS)
        data = response.json()
        pages = data.get("query", {}).get("pages", [])
        if pages and pages[0].get("categories"):
            categories = pages[0]["categories"]
            return any(cat.get("title") == "Category:Songs" for cat in categories)
    except Exception:
        pass
    
    return False


def search_song(query: str) -> Optional[str]:
    """
    Tries to find a certain song on RemyWiki using the MediaWiki API.

    MediaWiki will tell you if a title that you've searched is found as a direct
    article title. However, if it doesn't find one, the top page may not be
    a song. The category search to force songs won't allow the direct
    article title. So, we search the raw title, see if we've found it, then
    search in songs only if we haven't. So exact titles should always match,
    and close ones should usually match.

    :param query: a string representing something that's supposed to be a
        song name to find
    :return: the title of a RemyWiki page for a song, or None, representing a lack of results
    """
    # First try to get the page directly
    if page_is_song(query):
        return query
    
    # Search for the query
    # Using MediaWiki search action to find potential matches
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "formatversion": "2"
    }
    try:
        response = requests.get(REMY_API, params=params, headers=REMY_HEADERS)
        data = response.json()
        search_results = data.get("query", {}).get("search", [])
        for result in search_results:
            if page_is_song(result["title"]):
                return result["title"]
    except Exception:
        pass
    
    # Search in Songs category only
    # Restricting search results to only the Songs category
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f'{query} incategory:"Songs"',
        "format": "json",
        "formatversion": "2"
    }
    try:
        response = requests.get(REMY_API, params=params, headers=REMY_HEADERS)
        data = response.json()
        search_results = data.get("query", {}).get("search", [])
        if search_results:
            return search_results[0]["title"]
    except Exception:
        pass
    
    return None


def get_images_from_page(title: str) -> Dict[str, str]:
    """
    Gets all images from a page using the MediaWiki API.
    
    Uses the MediaWiki API to get images for a page.
    
    Fetches image URLs by querying imageinfo for each image found.
    
    :param title: The title of the page to get images from
    :return: A dictionary mapping image titles to their URLs
    """
    params = {
        "action": "query",
        "format": "json",
        "prop": "images",
        "titles": title,
        "formatversion": "2"
    }
    images = {}
    try:
        response = requests.get(REMY_API, params=params, headers=REMY_HEADERS)
        data = response.json()
        pages = data.get("query", {}).get("pages", [])
        if pages and pages[0].get("images"):
            image_list = pages[0]["images"]
            for image in image_list:
                image_title = image["title"]
                # Get the image info to retrieve the URL
                image_params = {
                    "action": "query",
                    "format": "json",
                    "titles": image_title,
                    "prop": "imageinfo",
                    "iiprop": "url",
                    "formatversion": "2"
                }
                try:
                    image_response = requests.get(REMY_API, params=image_params, headers=REMY_HEADERS)
                    image_data = image_response.json()
                    image_pages = image_data.get("query", {}).get("pages", [])
                    if image_pages and image_pages[0].get("imageinfo"):
                        url = image_pages[0]["imageinfo"][0]["url"]
                        images[image_title] = url
                except Exception:
                    pass
    except Exception:
        pass
    
    return images


def get_images_from_gallery(title: str) -> Dict[str, str]:
    """
    Gets all images from a gallery page using the MediaWiki API.

    Gallery pages are separate from song pages and may include banner/jacket images
    that are not directly attached to the song page.

    :param title: The song title (or Gallery:… title)
    :return: A dictionary mapping image titles to their URLs
    """
    gallery_title = title if title.startswith("Gallery:") else f"Gallery:{title}"
    params = {
        "action": "query",
        "format": "json",
        "prop": "images",
        "titles": gallery_title,
        "formatversion": "2"
    }
    images = {}
    try:
        response = requests.get(REMY_API, params=params, headers=REMY_HEADERS)
        data = response.json()
        pages = data.get("query", {}).get("pages", [])
        if pages and pages[0].get("images"):
            image_list = pages[0]["images"]
            for image in image_list:
                image_title = image["title"]
                image_params = {
                    "action": "query",
                    "format": "json",
                    "titles": image_title,
                    "prop": "imageinfo",
                    "iiprop": "url",
                    "formatversion": "2"
                }
                try:
                    image_response = requests.get(REMY_API, params=image_params, headers=REMY_HEADERS)
                    image_data = image_response.json()
                    image_pages = image_data.get("query", {}).get("pages", [])
                    if image_pages and image_pages[0].get("imageinfo"):
                        url = image_pages[0]["imageinfo"][0]["url"]
                        images[image_title] = url
                except Exception:
                    pass
    except Exception:
        pass
    return images


def check_page_has_gallery(title: str) -> bool:
    """
    Checks if a page has the Gallery template using the MediaWiki API.
    
    Uses the MediaWiki API to detect gallery template usage.
    
    :param title: The title of the page to check
    :return: True if the page has a Gallery template, False otherwise
    """
    params = {
        "action": "query",
        "format": "json",
        "prop": "templates",
        "titles": title,
        "formatversion": "2",
        "tllimit": "50"
    }
    try:
        response = requests.get(REMY_API, params=params, headers=REMY_HEADERS)
        data = response.json()
        pages = data.get("query", {}).get("pages", [])
        if pages and pages[0].get("templates"):
            templates = pages[0]["templates"]
            return any("Gallery" in t["title"] for t in templates)
    except Exception:
        pass
    
    return False


def get_image(query: str, image_type: str = "jacket") -> str:
    """
    Gets an image (or a message about no image) from a RemyWiki song page.

    This is intended to be used for jackets or banners. This searches the
    song page for images and returns the appropriate one.

    :param query: a string representing something that's supposed to be a
        song name to find
    :param image_type: Either "jacket" or "banner", default "jacket"
    :return: a response fitting for the bot to return, either the requested
        image or a message describing what it found instead
    """
    song_title = search_song(query)
    found_images = {}
    
    if song_title:
        # 1) Prefer images directly on the song page
        images = get_images_from_page(song_title)
        page_fallback = None
        for image_title, image_url in images.items():
            lower_title = image_title.lower()
            if "banner" in lower_title:
                found_images["banner"] = image_url
            elif "jacket" in lower_title:
                found_images["jacket"] = image_url
            if not page_fallback:
                page_fallback = image_url

        if image_type in found_images:
            return found_images[image_type]

        if page_fallback:
            # Page has images, so prioritise these before gallery fallback
            return page_fallback

        # 2) fallback to gallery images when there are no direct page images
        if check_page_has_gallery(song_title):
            gallery_images = get_images_from_gallery(song_title)
            gallery_fallback = None
            for image_title, image_url in gallery_images.items():
                lower_title = image_title.lower()
                if "banner" in lower_title:
                    found_images["banner"] = image_url
                elif "jacket" in lower_title:
                    found_images["jacket"] = image_url
                if not gallery_fallback:
                    gallery_fallback = image_url
            if image_type in found_images:
                return found_images[image_type]
            if gallery_fallback:
                return gallery_fallback

        # Otherwise report no available images
        if song_title.lower() == query.lower():
            return f"{song_title} does not have any images"
        else:
            return f"{query} seems to be the song {song_title} but it does not have any images"
    else:  # No song page
        return f"Could not find a song that looks like: {query}"


class Remybot(commands.Cog):

    async def respond(self, ctx, message, view=None):
        if ctx.interaction:
            return await ctx.interaction.response.send_message(message, view=view)
        return await ctx.send(message)

    @commands.hybrid_command()
    async def jacket(self, ctx, *, title: str):
        """
        Returns a jacket for a bemani song from remywiki.

        User Arguments:
            title: the name of a song to search for
        """
        response = get_image(title, "jacket")
        await self.respond(ctx, response)

    @commands.hybrid_command()
    async def banner(self, ctx, *, title: str):
        """
        Returns a banner for a bemani song from remywiki.

        User Arguments:
            title: the name of a song to search for
        """
        response = get_image(title, "banner")
        await self.respond(ctx, response)
