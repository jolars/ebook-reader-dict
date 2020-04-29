"""Update the description of a release."""
import json
import os
import sys
from contextlib import suppress

import requests

from .lang import release_tr
from . import constants as C


def fetch_release_url() -> str:
    """Retrieve the *url* of the release of the current *LOCALE*."""
    url = ""
    with requests.get(C.RELEASE_URL) as req:
        req.raise_for_status()
        data = req.json()
        try:
            count = data["assets"][0]["download_count"]
            update_download_count(count)
        except (KeyError, IndexError):
            pass
        url = data["url"]
    return url


def format_description() -> str:
    """Generate the release description."""

    tr = release_tr[C.LOCALE]

    # Get the words count
    count_tr = tr["words_count"]
    count = C.SNAPSHOT_COUNT.read_text().strip()

    # Format the words count
    thousands_sep = tr["thousands_separator"]
    count = f"{int(count):,}".replace(",", thousands_sep)

    # Get the snapshot's date
    date_tr = tr["date"]
    date = C.SNAPSHOT_FILE.read_text().strip()

    # Format th snapshot's date
    date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"

    # Get the download link
    download = tr["download"]

    return "\n".join(
        (
            f"{count_tr} {count}",
            f"{date_tr} {date}",
            f"\n {download} [{C.DICTHTML.name}]({C.DOWNLOAD_URL})",
        )
    )


def update_download_count(new_count: int) -> None:
    """Save the total download count. Simple curiosity."""
    old_count = 0
    with suppress(FileNotFoundError):
        old_count = int(C.SNAPSHOT_DOWNLOADS.read_text().strip())
    count = old_count + new_count
    C.SNAPSHOT_DOWNLOADS.write_text(str(count))
    print(f">>> Download count is {count:,}")


def update_release(url: str) -> None:
    """Update the release description of the current *LOCALE*."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {os.environ['GITHUB_TOKEN']}",
    }
    data = json.dumps({"body": format_description()})
    print(f">>> Updating release at {url} ...", flush=True)
    with requests.patch(url, data=data, headers=headers) as req:
        req.raise_for_status()


def main() -> int:
    """Entry point."""

    # Get the release URL
    url = fetch_release_url()
    if not url:
        print(" !! Cannot retrieve the release URL.")
        return 1

    # Update the release description
    update_release(url)

    print(">>> Release updated!")
    return 0


if __name__ == "__main__":  # pragma: nocover
    sys.exit(main())
