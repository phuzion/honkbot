from typing import Optional, Dict, List
import requests
import time
from discord.ext import commands

DEBUG_MODE = False

REMY_URL = "https://remywiki.com"
REMY_API = f"{REMY_URL}/api.php"
REMY_HEADERS = {"User-Agent": "OhioDDR-honkbot"}

# Overview: This code is used primarily for taking a song name and returning an image of the jacket or banner for that song from RemyWiki.
# This now uses the MediaWiki API to query pages directly instead of scraping HTML with BeautifulSoup.


class DebugTracker:
    """Tracks HTTP requests and timing for debug output."""
    
    def __init__(self):
        self.requests = []
        self.start_time = time.time()
    
    def track_request(self, method: str, url: str, params: Optional[Dict] = None, 
                     response_status: int = 0, response_size: int = 0, elapsed_ms: float = 0):
        """
        Record a single HTTP request with timing information.
        
        :param method: HTTP method (GET, POST, etc.)
        :param url: Request URL
        :param params: Request parameters
        :param response_status: HTTP status code
        :param response_size: Size of response in bytes
        :param elapsed_ms: Time taken in milliseconds
        """
        self.requests.append({
            "method": method,
            "url": url,
            "params": params,
            "status": response_status,
            "size": response_size,
            "elapsed_ms": elapsed_ms
        })
    
    def get_total_time_ms(self) -> float:
        """Calculate total elapsed time in milliseconds."""
        return (time.time() - self.start_time) * 1000
    
    def format_debug_output(self) -> str:
        """Format all tracked requests into a readable debug message."""
        lines = ["**DEBUG LOG**"]
        lines.append("")
        
        for i, req in enumerate(self.requests, 1):
            lines.append(f"Request {i}: {req['method']} {req['url']}")
            if req['params']:
                # Format params nicely
                param_str = ", ".join(f"{k}={v}" for k, v in req['params'].items())
                lines.append(f"  Params: {param_str}")
            lines.append(f"  Status: {req['status']} | Response: {req['size']} bytes | Time: {req['elapsed_ms']:.2f}ms")
            lines.append("")
        
        total_ms = self.get_total_time_ms()
        lines.append(f"**Total Time: {total_ms:.2f}ms**")
        
        return "\n".join(lines)


def page_is_song(title: str, tracker: Optional[DebugTracker] = None) -> bool:
    """
    Checks if a page belongs to the Songs category using the MediaWiki API.
    
    Uses the MediaWiki API to resolve song category membership.
    
    :param title: The title of the page to check
    :param tracker: Optional DebugTracker to record request timing
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
        start_time = time.time()
        response = requests.get(REMY_API, params=params, headers=REMY_HEADERS)
        elapsed_ms = (time.time() - start_time) * 1000
        
        if tracker:
            tracker.track_request("GET", REMY_API, params, response.status_code, len(response.content), elapsed_ms)
        
        data = response.json()
        pages = data.get("query", {}).get("pages", [])
        if pages and pages[0].get("categories"):
            categories = pages[0]["categories"]
            return any(cat.get("title") == "Category:Songs" for cat in categories)
    except Exception:
        pass
    
    return False


def search_song(query: str, tracker: Optional[DebugTracker] = None) -> Optional[str]:
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
    :param tracker: Optional DebugTracker to record request timing
    :return: the title of a RemyWiki page for a song, or None, representing a lack of results
    """
    # First try to get the page directly
    if page_is_song(query, tracker):
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
        start_time = time.time()
        response = requests.get(REMY_API, params=params, headers=REMY_HEADERS)
        elapsed_ms = (time.time() - start_time) * 1000
        
        if tracker:
            tracker.track_request("GET", REMY_API, params, response.status_code, len(response.content), elapsed_ms)
        
        data = response.json()
        search_results = data.get("query", {}).get("search", [])
        for result in search_results:
            if page_is_song(result["title"], tracker):
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
        start_time = time.time()
        response = requests.get(REMY_API, params=params, headers=REMY_HEADERS)
        elapsed_ms = (time.time() - start_time) * 1000
        
        if tracker:
            tracker.track_request("GET", REMY_API, params, response.status_code, len(response.content), elapsed_ms)
        
        data = response.json()
        search_results = data.get("query", {}).get("search", [])
        if search_results:
            return search_results[0]["title"]
    except Exception:
        pass
    
    return None


def get_images_from_page(title: str, tracker: Optional[DebugTracker] = None) -> Dict[str, str]:
    """
    Gets all images from a page using the MediaWiki API.
    
    Uses the MediaWiki API to get images for a page.
    
    Fetches image URLs by querying imageinfo for each image found.
    
    :param title: The title of the page to get images from
    :param tracker: Optional DebugTracker to record request timing
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
        start_time = time.time()
        response = requests.get(REMY_API, params=params, headers=REMY_HEADERS)
        elapsed_ms = (time.time() - start_time) * 1000
        
        if tracker:
            tracker.track_request("GET", REMY_API, params, response.status_code, len(response.content), elapsed_ms)
        
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
                    start_time = time.time()
                    image_response = requests.get(REMY_API, params=image_params, headers=REMY_HEADERS)
                    elapsed_ms = (time.time() - start_time) * 1000
                    
                    if tracker:
                        tracker.track_request("GET", REMY_API, image_params, image_response.status_code, len(image_response.content), elapsed_ms)
                    
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


def get_images_from_gallery(title: str, tracker: Optional[DebugTracker] = None) -> Dict[str, str]:
    """
    Gets all images from a gallery page using the MediaWiki API.

    Gallery pages are separate from song pages and may include banner/jacket images
    that are not directly attached to the song page.

    :param title: The song title (or Gallery:… title)
    :param tracker: Optional DebugTracker to record request timing
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
        start_time = time.time()
        response = requests.get(REMY_API, params=params, headers=REMY_HEADERS)
        elapsed_ms = (time.time() - start_time) * 1000
        
        if tracker:
            tracker.track_request("GET", REMY_API, params, response.status_code, len(response.content), elapsed_ms)
        
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
                    start_time = time.time()
                    image_response = requests.get(REMY_API, params=image_params, headers=REMY_HEADERS)
                    elapsed_ms = (time.time() - start_time) * 1000
                    
                    if tracker:
                        tracker.track_request("GET", REMY_API, image_params, image_response.status_code, len(image_response.content), elapsed_ms)
                    
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


def check_page_has_gallery(title: str, tracker: Optional[DebugTracker] = None) -> bool:
    """
    Checks if a page has the Gallery template using the MediaWiki API.
    
    Uses the MediaWiki API to detect gallery template usage.
    
    :param title: The title of the page to check
    :param tracker: Optional DebugTracker to record request timing
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
        start_time = time.time()
        response = requests.get(REMY_API, params=params, headers=REMY_HEADERS)
        elapsed_ms = (time.time() - start_time) * 1000
        
        if tracker:
            tracker.track_request("GET", REMY_API, params, response.status_code, len(response.content), elapsed_ms)
        
        data = response.json()
        pages = data.get("query", {}).get("pages", [])
        if pages and pages[0].get("templates"):
            templates = pages[0]["templates"]
            return any("Gallery" in t["title"] for t in templates)
    except Exception:
        pass
    
    return False


def get_image(query: str, image_type: str = "jacket", tracker: Optional[DebugTracker] = None) -> tuple[str, Optional[DebugTracker]]:
    """
    Gets an image (or a message about no image) from a RemyWiki song page.

    This is intended to be used for jackets or banners. This searches the
    song page for images and returns the appropriate one.

    :param query: a string representing something that's supposed to be a
        song name to find
    :param image_type: Either "jacket" or "banner", default "jacket"
    :param tracker: Optional DebugTracker to record request timing
    :return: tuple of (response message, tracker object)
    """
    if tracker is None and DEBUG_MODE:
        tracker = DebugTracker()
    
    song_title = search_song(query, tracker)
    found_images = {}
    
    if song_title:
        # 1) Prefer images directly on the song page
        images = get_images_from_page(song_title, tracker)
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
            return found_images[image_type], tracker

        if page_fallback:
            # Page has images, so prioritise these before gallery fallback
            return page_fallback, tracker

        # 2) fallback to gallery images when there are no direct page images
        if check_page_has_gallery(song_title, tracker):
            gallery_images = get_images_from_gallery(song_title, tracker)
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
                return found_images[image_type], tracker
            if gallery_fallback:
                return gallery_fallback, tracker

        # Otherwise report no available images
        if song_title.lower() == query.lower():
            return f"{song_title} does not have any images", tracker
        else:
            return f"{query} seems to be the song {song_title} but it does not have any images", tracker
    else:  # No song page
        return f"Could not find a song that looks like: {query}", tracker


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
        response, tracker = get_image(title, "jacket")
        await self.respond(ctx, response)
        
        if DEBUG_MODE and tracker and tracker.requests:
            debug_output = f"```\n{tracker.format_debug_output()}\n```"
            await self.respond(ctx, debug_output)

    @commands.hybrid_command()
    async def banner(self, ctx, *, title: str):
        """
        Returns a banner for a bemani song from remywiki.

        User Arguments:
            title: the name of a song to search for
        """
        response, tracker = get_image(title, "banner")
        await self.respond(ctx, response)
        
        if DEBUG_MODE and tracker and tracker.requests:
            debug_output = f"```\n{tracker.format_debug_output()}\n```"
            await self.respond(ctx, debug_output)
