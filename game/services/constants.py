from enum import Enum

class GameConfig:
    BOARD_SIZE = 8
    LOCAL_STORAGE_GAME_STATE_KEY = 'checkers_state'
    LOCAL_STORAGE_TIMER_STATE_KEY = 'timer_state'
    DEFAULT_GAME_TIME = 60
    ANIMATION_DURATION = 400

class GameRules:
    PIECE_ROWS_COUNT = 3
    MOVE_DIR_UP = 1
    MOVE_DIR_DOWN = -1
    PLAYER_1_ID = 1
    PLAYER_2_ID = 2


class Color(Enum):
    WHITE = 'white'
    BLACK = 'black'

class MoveType(Enum):
    MOVE = 'move'
    JUMP = 'jump'