import bisect
import math
import random
import time
import uuid

from virtual_player.card import Card
from virtual_player.channel import MessageTimeout
from virtual_player.game import GamePlayers, GameScores
from virtual_player.player import Player
from virtual_player.score_detector import HoldemPokerScoreDetector, HandEvaluator


class CardsFormatter:
    def __init__(self, compact=True):
        self.compact = compact

    def format(self, cards):
        return self.compact_format(cards) if self.compact else self.visual_format(cards)

    def compact_format(self, cards):
        return u" ".join(
            u"[{} of {}]".format(Card.RANKS[card.rank], Card.SUITS[card.suit])
            for card in cards
        )

    def visual_format(self, cards):
        lines = [""] * 7
        for card in cards:
            lines[0] += u"+-------+"
            lines[1] += u"| {:<2}    |".format(Card.RANKS[card.rank])
            lines[2] += u"|       |"
            lines[3] += u"|   {}   |".format(Card.SUITS[card.suit])
            lines[4] += u"|       |"
            lines[5] += u"|    {:>2} |".format(Card.RANKS[card.rank])
            lines[6] += u"+-------+"
        return u"\n".join(lines)


class HoldemGameState:
    STATE_PREFLOP = 0
    STATE_FLOP = 1
    STATE_TURN = 2
    STATE_RIVER = 3

    def __init__(self, players, scores, pot, big_blind, small_blind):
        self.players = players
        self.scores = scores
        self.pot = pot
        self.big_blind = big_blind
        self.small_blind = small_blind
        self.bets = {}

    @property
    def state(self):
        num_shared_cards = len(self.scores.shared_cards)
        if num_shared_cards == 0:
            return HoldemGameState.STATE_PREFLOP
        elif num_shared_cards == 3:
            return HoldemGameState.STATE_FLOP
        elif num_shared_cards == 4:
            return HoldemGameState.STATE_TURN
        else:
            return HoldemGameState.STATE_RIVER


class HoldemPlayerClient:
    def __init__(self, player_connector, player, bet_strategy, logger):
        self._player_connector = player_connector
        self._player = player
        self._bet_strategy = bet_strategy
        self._logger = logger

    def play(self):
        # Connecting the player
        server_channel = self._player_connector.connect(player=self._player, session_id=str(uuid.uuid4()))

        cards_formatter = CardsFormatter(compact=True)

        game_state = None

        while True:
            try:
                message = server_channel.recv_message(time.time() + 120)  # Wait for max 2 minutes
            except MessageTimeout:
                server_channel.send_message({"message_type": "disconnect"})
                self._logger.warning("Server did not send anything in 2 minutes: disconnecting")
                break
            else:
                if message["message_type"] == "disconnect":
                    self._logger.warning("Disconnected from the server")
                    break

                elif message["message_type"] == "ping":
                    server_channel.send_message({"message_type": "pong"})

                elif message["message_type"] == "room-update":
                    pass

                elif message["message_type"] == "game-update":
                    if message["event"] == "new-game":
                        game_state = HoldemGameState(
                            players=GamePlayers([
                                Player(id=player["id"], name=player["name"], money=player["money"])
                                for player in message["players"]
                            ]),
                            scores=GameScores(HoldemPokerScoreDetector()),
                            pot=0.0,
                            big_blind=message["big_blind"],
                            small_blind=message["small_blind"]
                        )
                        self._logger.info("New game: {}".format(message["game_id"]))

                    elif message["event"] == "game-over":
                        game_state = None
                        self._logger.info("Game over")

                    elif message["event"] == "cards-assignment":
                        cards = [Card(card[0], card[1]) for card in message["cards"]]
                        game_state.scores.assign_cards(self._player.id, cards)
                        self._logger.info("Cards received: {}".format(cards_formatter.format(cards)))

                    elif message["event"] == "showdown":
                        for player_id in message["players"]:
                            cards = [Card(card[0], card[1]) for card in message["players"][player_id]["cards"]]
                            game_state.scores.assign_cards(player_id, cards)
                            self._logger.info("Player {} cards: {}".format(
                                game_state.players.get(player_id),
                                cards_formatter.format(cards))
                            )

                    elif message["event"] == "fold":
                        game_state.players.fold(message["player"]["id"])
                        self._logger.info("Player {} fold".format(game_state.players.get(message["player"]["id"])))

                    elif message["event"] == "dead-player":
                        game_state.players.remove(message["player"]["id"])
                        self._logger.info("Player {} left".format(game_state.players.get(message["player"]["id"])))

                    elif message["event"] == "pots-update":
                        game_state.pot = sum([pot["money"] for pot in message["pots"]])
                        self._logger.info(u"Jackpot: ${:.2f}".format(game_state.pot))

                    elif message["event"] == "player-action" and message["action"] == "bet":
                        if message["player"]["id"] == self._player.id:
                            self._logger.info("My turn to bet".format(self._player))
                            bet = self._bet_strategy.bet(
                                me=self._player,
                                game_state=game_state,
                                min_bet=message["min_bet"],
                                max_bet=message["max_bet"],
                                bets=message["bets"]
                            )

                            choice = "Fold" if bet == -1 \
                                else ("Call ({:.2f})" if bet == message["min_bet"] else "Raise (${:.2f})").format(bet)

                            self._logger.info("Decision: {}".format(choice))

                            server_channel.send_message({
                                "message_type": "bet",
                                "bet": bet
                            })

                        else:
                            self._logger.info("Waiting for {} to bet...".format(
                                game_state.players.get(message["player"]["id"])
                            ))

                    elif message["event"] == "bet":
                        player = game_state.players.get(message["player"]["id"])
                        player.take_money(message["bet"])
                        self._logger.info("Player {} bet ${:.2f} ({})".format(
                            player,
                            message["bet"],
                            message["bet_type"]
                        ))

                    elif message["event"] == "shared-cards":
                        new_cards = [Card(card[0], card[1]) for card in message["cards"]]
                        game_state.scores.add_shared_cards(new_cards)
                        self._logger.info("Shared cards: {}".format(
                            cards_formatter.format(game_state.scores.shared_cards)
                        ))

                    elif message["event"] == "winner-designation":
                        self._logger.info("${:.2f} pot winners designation".format(message["pot"]["money"]))
                        for player_id in message["pot"]["winner_ids"]:
                            player = game_state.players.get(player_id)
                            player.add_money(message["pot"]["money_split"])
                            self._logger.info("Player {} won ${:.2f}".format(
                                player,
                                message["pot"]["money_split"]
                            ))

                    else:
                        self._logger.error("Event {} not recognised".format(message["event"]))

                else:
                    self._logger.error("Message type {} not recognised".format(message["message_type"]))


class RandomBetStrategy:
    def __init__(self, fold_cases=2, call_cases=5, raise_cases=3):
        self.bet_cases = (["fold"] * fold_cases) + (["call"] * call_cases) + (["raise"] * raise_cases)

    def bet(self, me, game_state, bets, min_bet, max_bet):
        decision = random.choice(self.bet_cases)

        if decision == "call" or (decision == "fold" and not min_bet):
            return min_bet

        elif decision == "fold":
            return -1

        else:
            return min(max_bet, game_state.pot)


class SmartBetStrategy:
    def __init__(self, hand_evaluator, logger):
        self.hand_evaluator = hand_evaluator
        self.logger = logger

    @staticmethod
    def choice(population, weights):
        def cdf(weights):
            total = sum(weights)
            result = []
            cumsum = 0
            for w in weights:
                cumsum += w
                result.append(cumsum / total)
            return result

        assert len(population) == len(weights)
        cdf_vals = cdf(weights)
        x = random.random()
        idx = bisect.bisect(cdf_vals, x)
        return population[idx]

    def bet(self, me, game_state, bets, min_bet, max_bet):
        game_pot = game_state.pot + sum(bets.values())

        cards_formatter = CardsFormatter(compact=False)

        # Logging game status
        self.logger.info("My cards:\n{}".format(cards_formatter.format(game_state.scores.player_cards(me.id))))

        if game_state.scores.shared_cards:
            self.logger.info("Board cards:\n{}".format(cards_formatter.format(game_state.scores.shared_cards)))

        self.logger.info("Min bet: ${:.2f} - Max bet: ${:.2f}".format(min_bet, max_bet))
        self.logger.info("Pots: ${:.2f}".format(game_pot))

        hand_strength = self.hand_evaluator.hand_strength(
            my_cards=game_state.scores.player_cards(me.id),
            board=game_state.scores.shared_cards
        )

        self.logger.info("HAND STRENGTH: {}".format(hand_strength))

        choices = ["fold", "call", "raise"]

        if hand_strength < 0.20:
            # Very bad hand
            weights = [0.85, 0.10, 0.05]    # Bluff
        elif hand_strength < 0.40:
            # Bad hand
            weights = [0.60, 0.35, 0.05]    # Bluff
        elif hand_strength < 0.60:
            # Ok hand
            weights = [0.15, 0.65, 0.20]
        elif hand_strength < 0.80:
            # Good hand
            weights = [0.00, 0.45, 0.55]
        else:
            # Very good hand
            weights = [0.00, 0.20, 0.85]

        self.logger.info("Fold: {}%, Call: {}%, Raise: {}%".format(weights[0], weights[1], weights[2]))

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        #  DECISION
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        choice = self.choice(choices, weights)

        if choice == "fold" and min_bet == 0.0:
            # Do not fold if it's free to call
            choice = "call"
        if choice == "raise" and min_bet == max_bet:
            # Just call if you cannot raise
            choice = "call"

        if choice == "fold":
            bet = -1
        elif choice == "call":
            bet = min_bet
        else:
            bet = min(max_bet, game_pot)

        return bet


BET_STRATEGIES = {
    "smart": lambda logger: SmartBetStrategy(hand_evaluator=HandEvaluator(HoldemPokerScoreDetector()), logger=logger),
    "random": lambda logger: RandomBetStrategy(call_cases=7, fold_cases=2, raise_cases=1)
}


def stategy_factory(strategy, logger):
    return BET_STRATEGIES[strategy](logger)
