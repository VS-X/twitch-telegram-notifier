import asyncio
import configparser
import twitchAPI
from typing import Dict, List, Final
import telegram
from collections import namedtuple, defaultdict
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

StreamData: Final = namedtuple(
    "StreamData", ["status", "game", "streamer_name", "stream_title"]
)


async def get_stream_data(
    user_ids: Dict[str, str], twitch: twitchAPI.Twitch
) -> Dict[str, StreamData]:
    live_streams = {}
    async for stream in twitch.get_streams(user_id=list(user_ids.values())):
        if stream:
            live_streams[stream.user_login] = StreamData(
                status="live",
                game=stream.game_name,
                streamer_name=stream.user_name,
                stream_title=stream.title,
            )

    for username in user_ids:
        if username not in live_streams:
            live_streams[username] = StreamData(
                status="offline", game=None, streamer_name=None, stream_title=None
            )
    return live_streams


async def get_user_ids(usernames: List[str], twitch: twitchAPI.Twitch):
    return {user.login: user.id async for user in twitch.get_users(logins=usernames)}


async def detect_changes_and_generate_messages(
    prev_stream_data: Dict[str, StreamData],
    current_stream_data: Dict[str, StreamData],
):
    messages: List[str] = []
    for username in current_stream_data:
        prev_status = prev_stream_data[username].status
        prev_game = prev_stream_data[username].game
        current_status = current_stream_data[username].status
        current_game = current_stream_data[username].game
        streamer_name = current_stream_data[username].streamer_name
        stream_title = current_stream_data[username].stream_title
        if prev_status is None:
            continue  # do not generate messages on startup (prev_status is initialized with None)
        elif current_status != prev_status and current_status == "live":
            messages.append(
                f"{streamer_name} went live with {current_game}\n{stream_title}"
            )
        elif current_game != prev_game and current_status == "live":
            messages.append(
                f"{streamer_name} switched to {current_game}\n{stream_title}"
            )

    return messages


async def main():
    try:
        config = configparser.ConfigParser()
        try:
            config.read("config.ini")
            app_id = config.get("twitch", "app_id")
            app_secret = config.get("twitch", "app_secret")
            usernames = config.get("twitch", "usernames").lower().split(",")
            telegram_token = config.get("telegram", "bot_token")
            telegram_chat_id = config.getint("telegram", "chat_id")
        except (FileNotFoundError, KeyError, configparser.Error) as e:
            logger.exception(f"Error reading config file: {e}")
            exit(1)

        logger.info(f"Loaded {len(usernames)} usernames: {', '.join(usernames)}")

        bot = telegram.Bot(token=telegram_token)
        twitch = await twitchAPI.Twitch(app_id, app_secret)

        # Get user IDs for all usernames
        user_ids = await get_user_ids(usernames, twitch)

        # Initialize previous stream data
        prev_stream_data = defaultdict(
            lambda: StreamData(status=None, game=None, streamer_name=None)
        )

        logger.info("Starting monitoring")
        while True:
            try:
                # Check current stream data
                current_stream_data = await get_stream_data(user_ids, twitch)

                messages = await detect_changes_and_generate_messages(
                    prev_stream_data, current_stream_data
                )
                if messages:
                    for message in messages:
                        logger.info(message)
                        try:
                            await bot.send_message(
                                chat_id=telegram_chat_id, text=message
                            )
                        except telegram.error.TelegramError as e:
                            logger.exception(f"Error when sending message: {e}")

                # Update previous stream data:
                prev_stream_data = current_stream_data
            except twitchAPI.types.TwitchAPIException as e:
                logger.exception(f"Twitch API error: {e}")
            except Exception as e:
                logger.exception(f"Unexpected error occurred: {e}")

            finally:
                await asyncio.sleep(60)
    except Exception as e:
        logger.exception(f"Unexpected error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
