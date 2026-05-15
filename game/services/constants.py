from typing import Literal


class GameConfig:
    BOARD_SIZE = 8

class GameRules:
    PIECE_ROWS_COUNT = 3
    MOVE_DIR_UP = 1
    MOVE_DIR_DOWN = -1
    PLAYER_1_ID = 1
    PLAYER_2_ID = 2

Color = Literal['white', 'black']

MoveType = Literal['move', 'jump']