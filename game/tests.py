import os
from types import SimpleNamespace
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Game, MoveEntry
from . import services
from .services.constants import GameRules
from .tasks import run_ai_turn


class GameTests(APITestCase):
    def setUp(self):
        self.prev_provider = os.environ.get('AI_PROVIDER_STR')
        os.environ['AI_PROVIDER_STR'] = 'random'

    def tearDown(self):
        if self.prev_provider is None:
            os.environ.pop('AI_PROVIDER_STR', None)
        else:
            os.environ['AI_PROVIDER_STR'] = self.prev_provider

    def _create_game(self):
        response = self.client.post(reverse('game-list'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response

    def test_initialize_game(self):
        response = self._create_game()
        self.assertIn('id', response.data)
        self.assertEqual(len(response.data['players']), 2)
        self.assertEqual(response.data['ai_player_id'], GameRules.PLAYER_2_ID)
        self.assertIsNone(response.data['winner_id'])

    def test_fetch_game(self):
        game_id = self._create_game().data['id']
        response = self.client.get(reverse('game-detail', args=[game_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data['id']), str(game_id))

    @patch('game.views._enqueue_ai_turn', return_value=SimpleNamespace(id='task-123'))
    def test_attempt_move_queues_ai_turn(self, _enqueue):
        game_id = self._create_game().data['id']
        move_url = reverse('game-move', args=[game_id])
        payload = {
            'fromPos': {'row': 2, 'col': 1},
            'toPos': {'row': 3, 'col': 0},
        }
        response = self.client.post(move_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['task_id'], 'task-123')
        self.assertEqual(response.data['game']['current_player_id'], GameRules.PLAYER_2_ID)
        self.assertEqual(MoveEntry.objects.filter(game_id=game_id).count(), 1)

    def test_ai_worker_is_idempotent_if_not_ai_turn(self):
        game_id = self._create_game().data['id']
        result = run_ai_turn(game_id)
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'not_ai_turn')

    def test_ai_worker_uses_random_provider_and_applies_move(self):
        game_id = self._create_game().data['id']
        services.process_move_request(
            game_id,
            from_dict={'row': 2, 'col': 1},
            to_dict={'row': 3, 'col': 0},
        )
        result = run_ai_turn(game_id)
        self.assertEqual(result['status'], 'completed')

        game = Game.objects.get(id=game_id)
        self.assertEqual(game.current_player_id, GameRules.PLAYER_1_ID)
        self.assertEqual(MoveEntry.objects.filter(game=game).count(), 2)

    def test_undo_reverts_user_and_ai_moves(self):
        create_response = self._create_game()
        game_id = create_response.data['id']
        initial_board = create_response.data['board']

        services.process_move_request(
            game_id,
            from_dict={'row': 2, 'col': 1},
            to_dict={'row': 3, 'col': 0},
        )
        run_ai_turn(game_id)

        response = self.client.post(reverse('game-undo', args=[game_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['board'], initial_board)
        self.assertEqual(response.data['current_player_id'], GameRules.PLAYER_1_ID)
        self.assertEqual(MoveEntry.objects.filter(game_id=game_id).count(), 0)

    def test_invalid_move(self):
        game_id = self._create_game().data['id']
        move_url = reverse('game-move', args=[game_id])
        payload = {
            'fromPos': {'row': 3, 'col': 3},
            'toPos': {'row': 4, 'col': 4},
        }
        response = self.client.post(move_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
