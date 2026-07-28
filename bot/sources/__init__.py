from .brainsurf import BrainSurfSource
from .club60sec import Club60SecSource
from .mamaquiz import MamaQuizSource
from .mozgoboynya import MozgoboynyaSource
from .quizplease import QuizPleaseSource
from .shakerquiz import ShakerQuizSource
from .wowquiz import WowQuizSource

ALL_SOURCES = [
    QuizPleaseSource(),
    Club60SecSource(),
    ShakerQuizSource(),
    BrainSurfSource(),
    MamaQuizSource(),
    WowQuizSource(),
    MozgoboynyaSource(),
]

__all__ = [
    "ALL_SOURCES",
    "QuizPleaseSource",
    "Club60SecSource",
    "ShakerQuizSource",
    "BrainSurfSource",
    "MamaQuizSource",
    "WowQuizSource",
    "MozgoboynyaSource",
]
