from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Game
from .serializers import GameStateSerializer, MovePayloadSerializer
from .services import orchestrator


@api_view(['POST'])
def initialize_game(request):
    """POST /api/games/"""
    game = orchestrator.create_new_game()
    serializer = GameStateSerializer(game)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def fetch_game(request, game_id):
    """GET /api/games/{id}/"""
    game = orchestrator.get_game(game_id)
    serializer = GameStateSerializer(game)
    return Response(serializer.data)


@api_view(['POST'])
def attempt_move(request, game_id):
    """POST /api/games/{id}/move/"""
    payload = MovePayloadSerializer(data=request.data)
    payload.is_valid(raise_exception=True)

    clean_data = payload.validated_data
    updated_game = orchestrator.process_move_request(
        game_id,
        from_dict=clean_data['from_pos'],
        to_dict=clean_data['to_pos']
    )

    serializer = GameStateSerializer(updated_game)
    return Response(serializer.data)


@api_view(['POST'])
def undo_move(request, game_id):
    """POST /api/games/{id}/undo/"""
    get_object_or_404(Game, id=game_id)

    updated_game = orchestrator.revert_last_move(game_id)

    serializer = GameStateSerializer(updated_game)
    return Response(serializer.data, status=status.HTTP_200_OK)

