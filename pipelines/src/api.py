"""
API client for Brawl Stars API.
Handles all HTTP requests and caching.
"""

import os
import time
import requests
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

# Determine API configuration from environment
PROXY_URL = os.getenv("BRAWL_STARS_PROXY_URL")
if PROXY_URL:
    BASE_URL = PROXY_URL
    API_TOKEN = None
else:
    BASE_URL = "https://api.brawlstars.com/v1"
    API_TOKEN = os.getenv("BRAWL_STARS_API_TOKEN")
    if not API_TOKEN:
        raise ValueError(
            "BRAWL_STARS_API_TOKEN not found. "
            "Either set BRAWL_STARS_API_TOKEN or BRAWL_STARS_PROXY_URL in .env"
        )


class ApiMaintenanceError(Exception):
    """Raised when the Brawl Stars API returns inMaintenance. Assume all endpoints affected."""
    pass


class NotFoundError(Exception):
    """Raised when the API returns 404. Never retried."""
    pass


# Cache for brawlers data to avoid repeated API calls
_BRAWLERS_CACHE = None

_RETRY_COUNT = 3
_RETRY_BACKOFF = 2  # sleeps: 2s, 4s, 8s (backoff_factor * 2^attempt)
_RETRY_STATUS = {429, 500, 502, 503, 504}


def api_call(endpoint, monitor=None):
    """Make an API call to Brawl Stars API (or proxy), with retry on transient errors."""
    headers = {"Accept": "application/json"}

    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"

    url = f"{BASE_URL}/{endpoint}"
    last_exc = None

    for attempt in range(1, _RETRY_COUNT + 1):
        # Only network errors and _RETRY_STATUS codes are retried; everything else raises immediately
        try:
            response = requests.get(url, headers=headers)
        except requests.RequestException as e:
            last_exc = e
        else:
            if response.ok:
                return response

            try:
                in_maintenance = response.json().get("reason") == "inMaintenance"
            except (ValueError, AttributeError):
                in_maintenance = False
            if in_maintenance:
                raise ApiMaintenanceError(f"Brawl API in maintenance (endpoint: {endpoint})")

            error_msg = f"API call failed for endpoint {endpoint}: {response.status_code} - {response.text}"
            if response.status_code == 404:
                raise NotFoundError(error_msg)
            if response.status_code not in _RETRY_STATUS:
                raise Exception(error_msg)

            last_exc = Exception(error_msg)

        if attempt < _RETRY_COUNT:
            delay = _RETRY_BACKOFF * (2 ** (attempt - 1))
            msg = f"API call attempt {attempt}/{_RETRY_COUNT} failed for {endpoint}: {last_exc}. Retrying in {delay}s..."
            print(msg)
            if monitor:
                monitor.log_warning(msg)
            time.sleep(delay)

    raise Exception(f"API call failed after {_RETRY_COUNT} attempts for {endpoint}: {last_exc}")


def get_all_brawlers_data():
    """Fetch complete brawler data including all available items (cached)"""
    global _BRAWLERS_CACHE
    if _BRAWLERS_CACHE is None:
        response = api_call("brawlers")
        data = response.json()
        _BRAWLERS_CACHE = {brawler['name']: brawler for brawler in data.get('items', [])}
    return _BRAWLERS_CACHE


def fetch_brawlers_reference():
    """Fetch complete brawlers reference data (for brawlers.json)"""
    response = api_call("brawlers")
    return response.json()


def fetch_club_data(tag, monitor=None):
    """Fetch club data from API"""
    encoded_tag = quote(tag)
    response = api_call(f"clubs/{encoded_tag}", monitor=monitor)
    return response.json()


def fetch_player_data(tag, monitor=None):
    """Fetch player data from API"""
    encoded_tag = quote(tag)
    response = api_call(f"players/{encoded_tag}", monitor=monitor)
    return response.json()


def fetch_battlelog(tag, monitor=None):
    """Fetch player battlelog from API"""
    encoded_tag = quote(tag)
    try:
        response = api_call(f"players/{encoded_tag}/battlelog", monitor=monitor)
    except NotFoundError:
        # Battlelog 404s for existing players with no battles since the last reset (e.g. after a game update)
        msg = f"Battlelog not found for {tag} (no battles since reset), treating as empty"
        print(msg)
        if monitor:
            monitor.log_warning(msg)
        return {"items": []}
    return response.json()


def get_club_members_tags(club_data):
    """Extract member tags from club data"""
    members = club_data.get('members', [])
    return [member.get('tag') for member in members if 'tag' in member]
