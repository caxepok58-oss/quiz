from .heuristic import HeuristicScheduleSource


class ShakerQuizSource(HeuristicScheduleSource):
    def __init__(self):
        super().__init__(name="shakerquiz", url="https://penza.shakerquiz.ru/")
