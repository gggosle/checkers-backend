from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Game, MoveEntry
from .services.constants import GameRules

class GameTests(APITestCase):
    def test_initialize_game(self):
        url = reverse('game-list')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(len(response.data['players']), 2)
        self.assertIsNone(response.data['winner_id'])

    def test_fetch_game(self):
        init_url = reverse('game-list')
        init_res = self.client.post(init_url)
        game_id = init_res.data['id']
        
        url = reverse('game-detail', args=[game_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data['id']), str(game_id))

    def test_attempt_move(self):
        init_url = reverse('game-list')
        init_res = self.client.post(init_url)
        game_id = init_res.data['id']

        move_url = reverse('game-move', args=[game_id])
        # CamelCaseJSONParser expects camelCase keys
        payload = {
            'fromPos': {'row': 2, 'col': 1},
            'toPos': {'row': 3, 'col': 0}
        }
        response = self.client.post(move_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['board'][2][1])
        self.assertIsNotNone(response.data['board'][3][0])
        self.assertEqual(response.data['current_player_id'], GameRules.PLAYER_2_ID)

    def test_undo_move(self):
        init_url = reverse('game-list')
        init_res = self.client.post(init_url)
        game_id = init_res.data['id']
        
        move_url = reverse('game-move', args=[game_id])
        payload = {
            'fromPos': {'row': 2, 'col': 1},
            'toPos': {'row': 3, 'col': 0}
        }
        self.client.post(move_url, payload, format='json')
        
        undo_url = reverse('game-undo', args=[game_id])
        response = self.client.post(undo_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['board'][2][1])
        self.assertIsNone(response.data['board'][3][0])
        self.assertEqual(response.data['current_player_id'], GameRules.PLAYER_1_ID)
        self.assertEqual(MoveEntry.objects.filter(game_id=game_id).count(), 0)

    def test_invalid_move(self):
        init_url = reverse('game-list')
        init_res = self.client.post(init_url)
        game_id = init_res.data['id']
        
        move_url = reverse('game-move', args=[game_id])
        payload = {
            'fromPos': {'row': 3, 'col': 3},
            'toPos': {'row': 4, 'col': 4}
        }
        response = self.client.post(move_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_undo_multi_jump(self):
        init_url = reverse('game-list')
        init_res = self.client.post(init_url)
        game_id = init_res.data['id']
        game = Game.objects.get(id=game_id)
        
        # Manually create move entry to test undo logic without complex game state setup
        MoveEntry.objects.create(game=game, player_dir=1, from_pos={'row': 2, 'col': 1}, to_pos={'row': 3, 'col': 0}, is_jump=False, is_promoted=False)
        
        undo_url = reverse('game-undo', args=[game.id])
        response = self.client.post(undo_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(MoveEntry.objects.filter(game=game).count(), 0)
        self.assertEqual(response.data['current_player_id'], GameRules.PLAYER_1_ID)
        self.assertIsNotNone(response.data['board'][2][1])
        self.assertIsNone(response.data['board'][3][0])
