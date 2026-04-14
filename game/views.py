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
def fetch_game(request, id):
    """GET /api/games/{id}/"""
    game = orchestrator.get_game(id)
    serializer = GameStateSerializer(game)
    return Response(serializer.data)


@api_view(['POST'])
def attempt_move(request, id):
    """POST /api/games/{id}/move/"""
    payload = MovePayloadSerializer(data=request.data)
    if not payload.is_valid():
        return Response(payload.errors, status=status.HTTP_400_BAD_REQUEST)

    clean_data = payload.validated_data
    updated_game = orchestrator.process_move_request(
        game_id=id,
        from_dict=clean_data['from'],
        to_dict=clean_data['to']
    )

    serializer = GameStateSerializer(updated_game)
    return Response(serializer.data)


@api_view(['POST'])
def undo_move(request, id):
    """POST /api/games/{id}/undo/"""
    get_object_or_404(Game, id=id)

    updated_game = orchestrator.revert_last_move(game_id=id)

    serializer = GameStateSerializer(updated_game)
    return Response(serializer.data, status=status.HTTP_200_OK)

