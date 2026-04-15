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
        url = reverse('initialize_game')
        init_res = self.client.post(url)
        game_id = init_res.data['id']
        
        url = reverse('fetch_game', args=[game_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data['id']), str(game_id))

    def test_attempt_move(self):
        init_url = reverse('initialize_game')
        init_res = self.client.post(init_url)
        game_id = init_res.data['id']

        move_url = reverse('attempt_move', args=[game_id])
        payload = {
            'from': {'r': 2, 'c': 1},
            'to': {'r': 3, 'c': 0}
        }
        response = self.client.post(move_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['board'][2][1])
        self.assertIsNotNone(response.data['board'][3][0])
        self.assertEqual(response.data['current_player']['id'], GameRules.PLAYER_2_ID)

    def test_undo_move(self):
        init_url = reverse('initialize_game')
        init_res = self.client.post(init_url)
        game_id = init_res.data['id']
        
        move_url = reverse('attempt_move', args=[game_id])
        payload = {
            'from': {'r': 2, 'c': 1},
            'to': {'r': 3, 'c': 0}
        }
        self.client.post(move_url, payload, format='json')
        
        undo_url = reverse('undo_move', args=[game_id])
        response = self.client.post(undo_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['board'][2][1])
        self.assertIsNone(response.data['board'][3][0])
        self.assertEqual(response.data['current_player']['id'], GameRules.PLAYER_1_ID)
        self.assertEqual(MoveEntry.objects.filter(game_id=game_id).count(), 0)

    def test_invalid_move(self):
        init_url = reverse('initialize_game')
        init_res = self.client.post(init_url)
        game_id = init_res.data['id']
        
        move_url = reverse('attempt_move', args=[game_id])
        payload = {
            'from': {'r': 3, 'c': 3},
            'to': {'r': 4, 'c': 4}
        }
        response = self.client.post(move_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['current_player']['id'], GameRules.PLAYER_1_ID)

    def test_undo_multi_jump(self):
        init_url = reverse('initialize_game')
        init_res = self.client.post(init_url)
        game_id = init_res.data['id']
        game = Game.objects.get(id=game_id)
        
        MoveEntry.objects.create(game=game, player_dir=1, from_pos={'row': 2, 'col': 1}, to_pos={'row': 4, 'col': 3}, is_jump=True)
        MoveEntry.objects.create(game=game, player_dir=1, from_pos={'row': 4, 'col': 3}, to_pos={'row': 6, 'col': 5}, is_jump=True)
        
        undo_url = reverse('undo_move', args=[game.id])
        response = self.client.post(undo_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(MoveEntry.objects.filter(game=game).count(), 0)
        self.assertEqual(response.data['current_player']['id'], GameRules.PLAYER_1_ID)
