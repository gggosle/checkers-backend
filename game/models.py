import uuid
from django.db import models


class Game(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    board = models.JSONField(help_text="Stores the 8x8 matrix of the board")
    current_player_id = models.IntegerField(help_text="The current Player object's id")
    players = models.JSONField(help_text="Array of 2 Player instances")

    must_jump_piece = models.JSONField(null=True, blank=True, help_text="{row: int, col: int} if multi-jump locked")
    winner_id = models.IntegerField(null=True, blank=True, help_text="ID of the winning player")

    def __str__(self):
        return f"Game {self.id} - Winner: {self.winner_id if self.winner_id else 'Ongoing'}"


class MoveEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='moves')
    player_dir = models.IntegerField()
    from_pos = models.JSONField(help_text="{row: int, col: int}")
    to_pos = models.JSONField(help_text="{row: int, col: int}")
    is_promoted = models.BooleanField(default=False)
    is_jump = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Move in {self.game.id} at {self.created_at}"