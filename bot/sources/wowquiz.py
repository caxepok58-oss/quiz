from .unavailable import UnavailableSource


class WowQuizSource(UnavailableSource):
    def __init__(self):
        super().__init__(
            name="wowquiz",
            reason=(
                "wowquiz.ru/schedule is a Nuxt SPA with no SSR data at all (window.__NUXT__ "
                "and the __NUXT_DATA__ payload are both empty) - the schedule is fetched "
                "purely client-side after mount. Found the API host (api.etowow.ru, a Yii2 "
                "backend) via the page's runtime config, but not the actual schedule route: "
                "~15 plausible paths (api/games/schedule, api/v1/schedule, api/public/games, "
                "etc.) all 404'd, and headless-Chrome network capture in this environment "
                "didn't fire the client-side fetch either. Needs a real browser's Network tab "
                "on /schedule to read the true request URL."
            ),
        )
