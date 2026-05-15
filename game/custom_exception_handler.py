from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from .exceptions import InvalidMoveError
from ai_engine.exceptions import AIHallucinationError, AITimeoutError

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, InvalidMoveError):
        return Response(
            {
                'error': 'invalid_move',
                'detail': str(exc)
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    if isinstance(exc, AITimeoutError):
        return Response(
            {
                'error': 'ai_timeout',
                'detail': str(exc)
            },
            status=status.HTTP_504_GATEWAY_TIMEOUT
        )
    if isinstance(exc, AIHallucinationError):
        return Response(
            {
                'error': 'ai_hallucination',
                'detail': str(exc)
            },
            status=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    return response
