#!/env/python
import logging.handlers
import os
import random
import string
import uuid

import redis

from virtual_player.player_client import PlayerClientConnector
from virtual_player.bet_strategy import HoldemPlayerClient, stategy_factory
from virtual_player.player import Player


def get_random_string(length=8):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))


def play_game():
    pid = get_random_string()
    player_id = "hal-{}".format(pid)
    player_name = "Hal {}".format(pid)

    logger = logging.getLogger("player.{}".format(player_id))
    logger.setLevel(logging.INFO)

    player_connector = PlayerClientConnector(redis, "texas-holdem-poker:lobby", logger)

    player = Player(
        id=player_id,
        name=player_name,
        money=1000.0
    )
    bot = HoldemPlayerClient(
        player_connector=player_connector,
        player=player,
        bet_strategy=stategy_factory(strategy=bet_strategy, logger=logger),
        logger=logger
    )

    bot.play()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)

    redis_url = os.environ["REDIS_URL"]
    redis = redis.from_url(redis_url)

    bet_strategy = os.getenv("BET_STRATEGY", "smart")

    while True:
        play_game()
