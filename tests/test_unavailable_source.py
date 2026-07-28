import pytest

from bot.sources.unavailable import UnavailableSource


@pytest.mark.asyncio
async def test_fetch_raises_with_the_given_reason():
    source = UnavailableSource(name="stub", reason="no scraper yet")
    with pytest.raises(RuntimeError, match="no scraper yet"):
        await source.fetch()
