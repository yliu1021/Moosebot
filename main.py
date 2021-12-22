import logging
import os

import dotenv

import bot.analytics
import bot

logger = logging.getLogger(__name__)


def main():
    try:
        dotenv.load_dotenv()
        logging.basicConfig(level=logging.INFO)
        moose_bot = bot.MooseBot()
        moose_bot.run(os.getenv("DISCORD_TOKEN"))
    except KeyboardInterrupt:
        logger.exception("bot quitting")
        bot.analytics.save_all()


if __name__ == "__main__":
    main()
