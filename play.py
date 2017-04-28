#!/env/python
import logging.handlers
import os
import uuid

import redis

from virtual_player.player_client import PlayerClientConnector
from virtual_player.bet_strategy import SmartBetStrategy, HoldemPlayerClient, get_random_name
from virtual_player.player import Player
from virtual_player.score_detector import HandEvaluator, HoldemPokerScoreDetector


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)

    redis_url = os.environ["REDIS_URL"]
    redis = redis.from_url(redis_url)

    player_connector = PlayerClientConnector(redis, "texas-holdem-poker:lobby", logging)

    while True:
        player_id = str(uuid.uuid4())

        logger = logging.getLogger("player-{}".format(player_id))
        logger.setLevel(logging.INFO)

        player = Player(
            id="hal-{}".format(str(uuid.uuid4())),
            name=get_random_name(),
            money=1000.0
        )

        virtual_player = HoldemPlayerClient(
            player_connector=player_connector,
            player=player,
            # bet_strategy=RandomBetStrategy(call_cases=7, fold_cases=2, raise_cases=1),
            bet_strategy=SmartBetStrategy(HandEvaluator(HoldemPokerScoreDetector()), logger),
            logger=logger
        )

        virtual_player.play()
