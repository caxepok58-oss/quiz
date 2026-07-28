import asyncio
from urllib.parse import urlencode

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class FetchError(Exception):
    pass


async def fetch_text(url: str, params: dict[str, str] | None = None, timeout: int = 20) -> str:
    """Fetch a URL's body by shelling out to the system `curl` binary.

    All three quiz-schedule sites this bot reads from sit behind an
    anti-bot layer that returns a flat 403 to aiohttp/requests regardless
    of the User-Agent header sent (almost certainly TLS/HTTP client
    fingerprinting), while plain curl with a normal browser User-Agent
    gets through reliably - verified against every source. Hence curl
    instead of aiohttp here. Requires the `curl` binary on PATH (present
    on essentially every Linux server).
    """
    if params:
        url = f"{url}?{urlencode(params)}"

    proc = await asyncio.create_subprocess_exec(
        "curl",
        "-sS",
        "-L",
        "-f",
        "--max-time",
        str(timeout),
        "-A",
        _BROWSER_UA,
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise FetchError(f"curl exited {proc.returncode} for {url}: {stderr.decode(errors='replace').strip()[:200]}")
    return stdout.decode("utf-8", errors="replace")
