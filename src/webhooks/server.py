from typing import Any, Dict, Union

import sentry_sdk
from fastapi import FastAPI, Header, HTTPException
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from uvicorn import Config, Server

from src.bot import bot
from src.core import settings
from src.webhooks import handlers
from src.webhooks.types import WebhookBody

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[
        StarletteIntegration(transaction_style="url"),
        FastApiIntegration(transaction_style="url"),
    ],
)

app = FastAPI()


@app.post("/webhook")
async def webhook_handler(body: WebhookBody, authorization: Union[str, None] = Header(default=None)) -> Dict[str, Any]:
    """
    Handles incoming webhook requests and forwards them to the appropriate handler.

    This function first checks the provided authorization token in the request header.
    If the token is valid, it checks if the platform can be handled and then forwards
    the request to the corresponding handler.

    Args:
        body (WebhookBody): The data received from the webhook.
        authorization (Union[str, None]): The authorization header containing the Bearer token.

    Returns:
        Dict[str, Any]: The response from the corresponding handler. The dictionary contains
                       a "success" key indicating whether the operation was successful.

    Raises:
        HTTPException: If an error occurs while processing the webhook event or if unauthorized.
    """
    if authorization is None or not authorization.strip().startswith("Bearer"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = authorization[6:].strip()
    if not token == settings.WEBHOOK_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not handlers.can_handle(body.platform):
        raise HTTPException(status_code=501, detail="Platform not implemented")

    return await handlers.handle(body, bot)


config = Config(app, host="0.0.0.0", port=1337)
server = Server(config)
