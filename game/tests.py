from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Game, MoveEntry
from .services.constants import GameRules

class GameTests(APITestCase):
    def test_initialize_game(self):
        url = reverse('initialize_game')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(len(response.data['players']), 2)
        self.assertIsNone(response.data['winner'])

    def test_fetch_game(self):
        # First create a game
        game = Game.objects.create(
            board=[[None]*8 for _ in range(8)],
            players=[{'id': 1}, {'id': 2}],
            current_player={'id': 1}
        )
        url = reverse('fetch_game', args=[game.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data['id']), str(game.id))

    def test_attempt_move(self):
        # Initialize a real game to have a valid board
        init_url = reverse('initialize_game')
        init_res = self.client.post(init_url)
        game_id = init_res.data['id']
        
        # Player 1 (WHITE) is at rows 0, 1, 2, move_dir = 1 (UP? wait, MOVE_DIR_UP=1, MOVE_DIR_DOWN=-1)
        # In board_utils: 
        # rows 0,1,2 get WHITE, direction = move_dir_up (1)
        # rows 5,6,7 get BLACK, direction = move_dir_down (-1)
        # Black squares at (2, 1), (2, 3), (2, 5), (2, 7) have white pieces.
        # Valid move for white piece at (2,1) is to (3,0) or (3,2) if they are black squares.
        # is_black_square: (row + col) % 2 != 0
        # (2,1) -> 3 (black), (3,0) -> 3 (black), (3,2) -> 5 (black)
        
        move_url = reverse('attempt_move', args=[game_id])
        payload = {
            'from': {'r': 2, 'c': 1},
            'to': {'r': 3, 'c': 0}
        }
        response = self.client.post(move_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # After move, board[2][1] should be None, board[3][0] should have the piece
        self.assertIsNone(response.data['board'][2][1])
        self.assertIsNotNone(response.data['board'][3][0])
        # Current player should have switched
        self.assertEqual(response.data['current_player']['id'], GameRules.PLAYER_2_ID)

    def test_undo_move(self):
        # Create game and make a move
        init_url = reverse('initialize_game')
        init_res = self.client.post(init_url)
        game_id = init_res.data['id']
        
        move_url = reverse('attempt_move', args=[game_id])
        payload = {
            'from': {'r': 2, 'c': 1},
            'to': {'r': 3, 'c': 0}
        }
        self.client.post(move_url, payload, format='json')
        
        # Now undo
        undo_url = reverse('undo_move', args=[game_id])
        response = self.client.post(undo_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Board should be back to initial
        self.assertIsNotNone(response.data['board'][2][1])
        self.assertIsNone(response.data['board'][3][0])
        self.assertEqual(response.data['current_player']['id'], GameRules.PLAYER_1_ID)
        self.assertEqual(MoveEntry.objects.filter(game_id=game_id).count(), 0)

    def test_invalid_move(self):
        init_url = reverse('initialize_game')
        init_res = self.client.post(init_url)
        game_id = init_res.data['id']
        
        move_url = reverse('attempt_move', args=[game_id])
        # Try to move an empty square
        payload = {
            'from': {'r': 3, 'c': 3},
            'to': {'r': 4, 'c': 4}
        }
        response = self.client.post(move_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK) # Current implementation returns 200 and same state
        self.assertEqual(response.data['current_player']['id'], GameRules.PLAYER_1_ID)
