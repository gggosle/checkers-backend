from .entities import GameState, Player
from .constants import GameConfig, GameRules
from .board_utils import create_initial_board

def generate_players() -> list[Player]:
    player1 = Player(
        id= GameRules.PLAYER_1_ID,
        name='Player 1',
        color='white',
        move_dir=GameRules.MOVE_DIR_UP,
    )

    player2 = Player(
        id=GameRules.PLAYER_2_ID,
        name='Player 2',
        color='black',
        move_dir=GameRules.MOVE_DIR_DOWN,
    )

    return [player1, player2]

def create_initial_game_state() -> GameState:
    players = generate_players()
    board = create_initial_board(GameConfig.BOARD_SIZE, GameRules.PIECE_ROWS_COUNT, GameRules.MOVE_DIR_UP, GameRules.MOVE_DIR_DOWN)
    return GameState(board, players, players[0].id, None)

