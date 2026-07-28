from .heuristic import HeuristicScheduleSource


class QuizPleaseSource(HeuristicScheduleSource):
    def __init__(self):
        super().__init__(name="quizplease", url="https://penza.quizplease.ru/schedule")
