from .unavailable import UnavailableSource


class MozgoboynyaSource(UnavailableSource):
    def __init__(self):
        super().__init__(
            name="mozgoboynya",
            reason=(
                "Could not find a live schedule source for Mozgoboynya in Penza. Their current "
                "platform (rudagames.com, a Nuxt SPA backed by api.rudagames.com) never "
                "mentions Penza anywhere - no SSR data, no city option found. mzgb.pro, "
                "despite also being branded 'Мозгобойня', is a separate Chelyabinsk-only site. "
                "The aggregator findquiz.ru lists a Penza 'Мозгобойня' organizer but with 0 "
                "games. Likely they aren't currently running games in Penza via any scrapable "
                "site - check their VK group, or add games by hand with /add_game if that "
                "changes."
            ),
        )
