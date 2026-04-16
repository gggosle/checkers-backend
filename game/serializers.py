from rest_framework import serializers
from .models import Game

class GameStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ['id', 'board', 'current_player', 'players', 'must_jump_piece', 'winner']

class PositionSerializer(serializers.Serializer):
    row = serializers.IntegerField(min_value=0, max_value=7)
    col = serializers.IntegerField(min_value=0, max_value=7)

class MovePayloadSerializer(serializers.Serializer):
    from_pos = PositionSerializer()
    to_pos = PositionSerializer()