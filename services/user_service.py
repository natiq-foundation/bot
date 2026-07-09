from config import Config
from db.repositories import bot_state_repo, channel_repo, group_repo, user_repo
from db.session import get_session
from services.verse_ingestion_service import LAST_INGESTION_STATE_KEY


def register_incoming_message(platform: str, chat: dict) -> None:
    """
    Register every incoming user/group/channel in database.
    """

    chat_type = chat.get("type", "private")
    external_id = chat.get("id")

    if external_id is None:
        return

    external_id = str(external_id)

    with get_session() as session:

        if chat_type == "private":
            user_repo.get_or_create(
                session,
                platform=platform,
                external_id=external_id,
                username=chat.get("username"),
                first_name=chat.get("first_name"),
            )

        elif chat_type in ("group", "supergroup"):
            group_repo.get_or_create(
                session,
                platform=platform,
                external_id=external_id,
                title=chat.get("title"),
            )

        elif chat_type == "channel":
            channel_repo.get_or_create(
                session,
                platform=platform,
                external_id=external_id,
                title=chat.get("title"),
                username=chat.get("username"),
            )


def is_admin(platform: str, external_id: str) -> bool:
    """
    Check if user is admin.
    """

    with get_session() as session:
        return user_repo.is_admin(
            session,
            platform,
            str(external_id),
        )


def bootstrap_admins() -> None:
    """
    Promote ADMIN_USER_IDS from environment.
    """

    admin_ids = Config.get_admin_ids()

    if not admin_ids:
        return

    platform = Config.PLATFORM_NAME

    with get_session() as session:

        for admin_id in admin_ids:

            user = user_repo.get_or_create(
                session,
                platform=platform,
                external_id=str(admin_id),
            )

            user.is_admin = True


def seed_static_recipients() -> None:
    """
    Import initial recipients from env.

    These are only bootstrap values.
    After that, database becomes the source of truth.
    """

    platform = Config.PLATFORM_NAME

    with get_session() as session:

        for channel_id in Config.get_seed_channel_ids():

            channel_repo.get_or_create(
                session,
                platform=platform,
                external_id=str(channel_id),
            )


        for group_id in Config.get_seed_group_ids():

            group_repo.get_or_create(
                session,
                platform=platform,
                external_id=str(group_id),
            )


        for user_id in Config.get_seed_user_ids():

            user_repo.get_or_create(
                session,
                platform=platform,
                external_id=str(user_id),
            )


def get_stats() -> dict:

    with get_session() as session:

        return {
            "users": user_repo.count(session),
            "channels": channel_repo.count(session),
            "groups": group_repo.count(session),
            "last_verse_ingestion": bot_state_repo.get(
                session,
                LAST_INGESTION_STATE_KEY,
            ),
        }
