import asyncio
import configparser
import twitchAPI
import telegram
import logging
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def read_config():
    try:
        cp = configparser.ConfigParser()
        cp.read("config.ini")
        config = {}
        config["app_id"] = cp.get("twitch", "app_id")
        config["app_secret"] = cp.get("twitch", "app_secret")
        config["usernames"] = cp.get("twitch", "usernames").lower().split(",")
        config["telegram_token"] = cp.get("telegram", "bot_token")
        config["telegram_chat_id"] = cp.getint("telegram", "chat_id")
        return config
    except (FileNotFoundError, KeyError, configparser.Error) as e:
        logger.exception(f"Error reading config file: {e}")
        exit(1)


async def get_data(usernames: List[int], twitch: twitchAPI.Twitch):
    live_streams = {}
    async for stream in twitch.get_streams(user_login=list(usernames)):
        if stream:
            live_streams[stream.user_login] = {
                "status": "live",
                "game": stream.game_name,
                "title": stream.title,
                "name": stream.user_name,
            }
    return live_streams


async def detect_changes_and_generate_messages(
    current_stream_data: Dict[str, str],
):
    messages: List[str] = []
    for username in current_stream_data:
        prev_status = streams.get(username, {}).get("status", None)
        prev_game = streams.get(username, {}).get("game", None)
        current_status = current_stream_data[username]["status"]
        current_game = current_stream_data[username]["game"]
        current_title = current_stream_data[username]["title"]
        streamer_name = current_stream_data[username]["name"]
        if not prev_status:  # initialization
            streams[username] = {
                "game": current_game,
                "title": current_title,
                "status": current_status,
            }
        elif current_status == "offline":  # streamer went offline
            streams[username]["status"] = current_status
        elif current_status != prev_status:  # streamer went live
            streams[username]["status"] = current_status
            streams[username]["game"] = current_game
            messages.append(
                f"{streamer_name} went live with {current_game}\n{current_title}"
            )
        elif (  # streamer changed game
            current_status == prev_status and current_game != prev_game
        ):
            streams[username]["game"] = current_game
            messages.append(
                f"{streamer_name} switched to {current_game}\n{current_title}"
            )
    return messages


async def send_messages(messages):
    for message in messages:
        logger.info(message)
        try:
            await bot.send_message(chat_id=config["telegram_chat_id"], text=message)
        except telegram.error.TelegramError as e:
            logger.exception(f"Error when sending message: {e}")


config = read_config()
bot = telegram.Bot(token=config["telegram_token"])
streams: Dict[str, Dict[str, str]] = {}


async def main():
    try:
        logger.info(
            f"Loaded {len(config['usernames'])} usernames: {', '.join(config['usernames'])}"
        )

        twitch = await twitchAPI.Twitch(config["app_id"], config["app_secret"])
        logger.info("Starting monitoring")
        while True:
            try:
                # Check current stream data
                current_stream_data = await get_data(config["usernames"], twitch)
                messages = await detect_changes_and_generate_messages(
                    current_stream_data
                )
                if messages:
                    await send_messages(messages)

                # # Update previous stream data:
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
