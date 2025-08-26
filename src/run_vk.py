from os import makedirs

from loguru import logger

from core.loader import vk_bot
from vk import labeler

if __name__ == "__main__":
    error_log_path = "errors"
    makedirs(error_log_path, exist_ok=True)
    logger.add(f"{error_log_path}/vk_log_{{time}}.log", level="WARNING", rotation="20 MB")

    logger.info("Starting VK bot")
    vk_bot.labeler.load(labeler)

    vk_bot.run_forever()