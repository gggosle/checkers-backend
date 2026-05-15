from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Game
from .serializers import GameStateSerializer, MovePayloadSerializer
from .services import orchestrator
from drf_spectacular.utils import extend_schema

class GameViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Game.objects.all()

    def get_serializer_class(self):
        if self.action == 'move':
            return MovePayloadSerializer
        return GameStateSerializer

    @extend_schema(request=None)
    def create(self, request):
        game = orchestrator.create_new_game()
        serializer = self.get_serializer(game)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: GameStateSerializer})
    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)

        clean_data = payload.validated_data
        updated_game = orchestrator.process_move_request(
            pk,
            from_dict=clean_data['from_pos'],
            to_dict=clean_data['to_pos']
        )

        output_serializer = GameStateSerializer(updated_game)
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=None)
    @action(detail=True, methods=['post'])
    def undo(self, request, pk=None):
        game = self.get_object()

        updated_game = orchestrator.revert_last_move(game)

        serializer = self.get_serializer(updated_game)
        return Response(serializer.data, status=status.HTTP_200_OK)