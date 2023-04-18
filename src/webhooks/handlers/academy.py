from discord import Bot
from discord.errors import NotFound
from fastapi import HTTPException

from src.core import settings
from src.webhooks.types import WebhookBody, WebhookEvent


async def handler(body: WebhookBody, bot: Bot) -> dict:
    """
    Handles incoming webhook events and performs actions accordingly.

    This function processes different webhook events related to account linking,
    certificate awarding, and account unlinking. It updates the member's roles
    based on the received event.

    Args:
        body (WebhookBody): The data received from the webhook.
        bot (Bot): The instance of the Discord bot.

    Returns:
        dict: A dictionary with a "success" key indicating whether the operation was successful.

    Raises:
        HTTPException: If an error occurs while processing the webhook event.
    """
    # TODO: Change it here so we pass the guild instead of the bot  # noqa: T000
    guild = await bot.fetch_guild(settings.guild_ids[0])

    try:
        discord_id = int(body.data["discord_id"])
        member = await guild.fetch_member(discord_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Discord ID") from exc
    except NotFound as exc:
        raise HTTPException(status_code=400, detail="User is not in the Discord server") from exc

    if body.event == WebhookEvent.ACCOUNT_LINKED:
        roles_to_add = {settings.roles.ACADEMY_USER}
        roles_to_add.update(settings.get_academy_cert_role(cert["id"]) for cert in body.data["certifications"])

        # Filter out invalid role IDs
        valid_roles_to_add = {role_id for role_id in roles_to_add if role_id is not None}

        await member.add_roles(*valid_roles_to_add, atomic=True)
    elif body.event == WebhookEvent.CERTIFICATE_AWARDED:
        cert_id = body.data["certification"]["id"]

        role = settings.get_academy_cert_role(cert_id)
        if not role:
            raise HTTPException(status_code=400, detail=f"Role for certification: {cert_id} does not exist")

        await member.add_roles(role, atomic=True)
    elif body.event == WebhookEvent.ACCOUNT_UNLINKED:
        current_role_ids = {role.id for role in member.roles}
        cert_role_ids = {settings.get_academy_cert_role(cert_id) for _, cert_id in settings.academy_certificates}

        common_role_ids = current_role_ids.intersection(cert_role_ids)

        roles_to_remove = {settings.roles.ACADEMY_USER}.union(common_role_ids)

        await member.remove_roles(*roles_to_remove, atomic=True)
    else:
        raise HTTPException(status_code=501, detail=f"Event {body.event} not implemented")

    return {"success": True}
