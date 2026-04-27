from django.db import transaction
from rest_framework import viewsets, status, mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Game
from .serializers import GameStateSerializer, MovePayloadSerializer, TaskResponseSerializer
from . import services
from drf_spectacular.utils import extend_schema


def _enqueue_ai_turn(game_id: str):
    import django_rq
    queue = django_rq.get_queue('default')
    return queue.enqueue('game.tasks.run_ai_turn', game_id)


class GameViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Game.objects.all()

    def get_serializer_class(self):
        if self.action == 'move':
            return MovePayloadSerializer
        return GameStateSerializer

    @extend_schema(request=None, responses={201: GameStateSerializer})
    def create(self, request):
        game = services.create_new_game()
        return Response(GameStateSerializer(game).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={
            200: GameStateSerializer,
            202: TaskResponseSerializer,
            503: dict,
        }
    )
    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        payload = self.get_serializer(data=request.data)
        payload.is_valid(raise_exception=True)

        clean_data = payload.validated_data
        updated_game = services.process_move_request(
            pk,
            from_dict=clean_data['from_pos'],
            to_dict=clean_data['to_pos']
        )
        if not services.is_ai_turn(updated_game):
            return Response(GameStateSerializer(updated_game).data, status=status.HTTP_200_OK)

        try:
            task = _enqueue_ai_turn(str(updated_game.id))
        except Exception as error:
            return Response(
                {'error': 'ai_queue_unavailable', 'detail': str(error)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                'task_id': task.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(request=None)
    @action(detail=True, methods=['post'])
    def undo(self, request, pk=None):
        with transaction.atomic():
            game = Game.objects.select_for_update().get(id=pk)
            updated_game = services.undo_move(game)

        serializer = self.get_serializer(updated_game)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TaskStatusView(APIView):
    @extend_schema(responses={200: dict, 404: dict})
    def get(self, request, task_id: str):
        try:
            import django_rq
            from rq.exceptions import NoSuchJobError
            from rq.job import Job
        except Exception:
            return Response(
                {'task_id': task_id, 'status': 'unavailable', 'detail': 'django-rq is not configured'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            job = Job.fetch(task_id, connection=django_rq.get_connection('default'))
        except NoSuchJobError:
            return Response({'task_id': task_id, 'status': 'not_found'}, status=status.HTTP_404_NOT_FOUND)

        response = {'task_id': task_id, 'status': job.get_status()}
        if job.is_finished:
            response['result'] = job.result
        if job.is_failed and job.exc_info:
            response['error'] = job.exc_info.splitlines()[-1]

        return Response(response, status=status.HTTP_200_OK)
