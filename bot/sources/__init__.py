from .club60sec import Club60SecSource
from .quizplease import QuizPleaseSource
from .shakerquiz import ShakerQuizSource

ALL_SOURCES = [QuizPleaseSource(), Club60SecSource(), ShakerQuizSource()]

__all__ = ["ALL_SOURCES", "QuizPleaseSource", "Club60SecSource", "ShakerQuizSource"]
