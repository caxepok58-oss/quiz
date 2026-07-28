from .heuristic import HeuristicScheduleSource


class Club60SecSource(HeuristicScheduleSource):
    def __init__(self):
        super().__init__(name="club60sec", url="https://club60sec.ru/quizgames/schedule/58/")
