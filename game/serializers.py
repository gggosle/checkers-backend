from rest_framework import serializers
from .models import Game

class GameStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = ['id', 'board', 'current_player', 'players', 'must_jump_piece', 'winner']

class PositionSerializer(serializers.Serializer):
    r = serializers.IntegerField(min_value=0, max_value=7)
    c = serializers.IntegerField(min_value=0, max_value=7)

class MovePayloadSerializer(serializers.Serializer):
    from_pos = PositionSerializer()
    to_pos = PositionSerializer()

    def to_internal_value(self, data):

        internal_data = data.copy()
        if 'from' in data:
            internal_data['from_pos'] = data['from']
        if 'to' in data:
            internal_data['to_pos'] = data['to']
        
        ret = super().to_internal_value(internal_data)
        return {
            'from': ret['from_pos'],
            'to': ret['to_pos']
        }