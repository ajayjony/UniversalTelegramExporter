"""Utility module to check for new release of telegram-media-downloader"""

import http.client
import json

from rich.console import Console
from rich.markdown import Markdown

from . import __version__


# pylint: disable = C0301
def check_for_updates() -> None:
    """Checks for new releases.

    Using Github API checks for new release and prints information of new release if available.
    Silently fails if update check cannot be performed (network issues, API errors, etc.).
    """
    console = Console()
    try:
        headers: dict = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36",
        }
        conn = http.client.HTTPSConnection("api.github.com")
        conn.request(
            method="GET",
            url="/repos/ajayjony/UniversalTelegramExporter/releases/latest",
            headers=headers,
        )
        res = conn.getresponse()
        
        # Check if the request was successful
        if res.status != 200:
            # Silently fail for non-200 responses (404, 403, etc.)
            return
        
        # Parse the response
        response_data = res.read().decode("utf-8")
        latest_release: dict = json.loads(response_data)
        
        # Validate that the response contains expected fields
        if not isinstance(latest_release, dict):
            return
        
        if "tag_name" not in latest_release:
            # Response doesn't have the expected structure
            return
        
        # Check if a new version is available
        tag_name = latest_release.get("tag_name", "")
        if tag_name and f"v{__version__}" != tag_name:
            update_message: str = (
                f"## New version of Telegram-Media-Downloader is available - {latest_release.get('name', tag_name)}\n"
                f"You are using an outdated version v{__version__} please pull in the changes using `git pull` or download the latest release.\n\n"
                f"Find more details about the latest release here - {latest_release.get('html_url', 'https://github.com/ajayjony/UniversalTelegramExporter/releases')}"
            )
            console.print(Markdown(update_message))
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        # Silently fail for parsing errors - these are not critical
        pass
    except (http.client.HTTPException, OSError, TimeoutError) as e:
        # Silently fail for network errors - these are not critical
        pass
    except Exception as e:
        # Log unexpected errors at debug level only
        # Don't show error to user as update check is non-critical
        pass
