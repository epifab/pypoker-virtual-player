#!/env/python
import logging.handlers
import os
import uuid

import redis

from virtual_player.player_client import PlayerClientConnector
from virtual_player.bet_strategy import HoldemPlayerClient, get_random_name, stategy_factory
from virtual_player.player import Player


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)

    redis_url = os.environ["REDIS_URL"]
    redis = redis.from_url(redis_url)

    bet_strategy = os.getenv("BET_STRATEGY", "smart")

    while True:
        player_id = str(uuid.uuid4())

        logger = logging.getLogger("player-{}".format(player_id))
        logger.setLevel(logging.INFO)

        player_connector = PlayerClientConnector(redis, "texas-holdem-poker:lobby", logger)

        player = Player(
            id="hal-{}".format(str(uuid.uuid4())),
            name=get_random_name(),
            money=1000.0
        )

        virtual_player = HoldemPlayerClient(
            player_connector=player_connector,
            player=player,
            bet_strategy=stategy_factory(strategy=bet_strategy, logger=logger),
            logger=logger
        )

        virtual_player.play()
