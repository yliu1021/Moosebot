import logging
import os

import dotenv

import bot

logger = logging.getLogger(__name__)


def main():
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.INFO)
    moose_bot = bot.MooseBot()
    moose_bot.run(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()
