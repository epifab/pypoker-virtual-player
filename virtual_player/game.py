class GamePlayers:
    def __init__(self, players):
        # Dictionary of players keyed by their ids
        self._players = {player.id: player for player in players}
        # List of player ids sorted according to the original players list
        self._player_ids = [player.id for player in players]
        # List of folder ids
        self._folder_ids = set()
        # Dead players
        self._dead_player_ids = set()

    def fold(self, player_id):
        if player_id not in self._player_ids:
            raise ValueError("Unknown player id")
        self._folder_ids.add(player_id)

    def remove(self, player_id):
        self.fold(player_id)
        self._dead_player_ids.add(player_id)

    def reset(self):
        self._folder_ids = set(self._dead_player_ids)

    def round(self, start_player_id, reverse=False):
        start_item = self._player_ids.index(start_player_id)
        step_multiplier = -1 if reverse else 1
        for i in range(len(self._player_ids)):
            next_item = (start_item + (i * step_multiplier)) % len(self._player_ids)
            player_id = self._player_ids[next_item]
            if player_id not in self._folder_ids:
                yield self._players[player_id]
        raise StopIteration

    # def rounder(self, start_player_id):
    #     def decorator(action):
    #         def perform():
    #             start_item = self._player_ids.index(start_player_id)
    #             try:
    #                 while True:
    #                     player_id = self._player_ids[start_item]
    #                     if player_id not in self._folder_ids:
    #                         action(self._players[player_id])
    #                     start_item = (start_item + 1) % len(self._player_ids)
    #             except StopIteration:
    #                 pass
    #         return perform
    #     return decorator

    def get(self, player_id):
        try:
            return self._players[player_id]
        except KeyError:
            raise ValueError("Unknown player id")

    def get_next(self, player_id):
        if player_id not in self._player_ids:
            raise ValueError("Unknown player id")
        if player_id in self._folder_ids:
            raise ValueError("Inactive player")
        start_item = self._player_ids.index(player_id)
        for i in range(len(self._player_ids) - 1):
            next_index = (start_item + i + 1) % len(self._player_ids)
            next_id = self._player_ids[next_index]
            if next_id not in self._folder_ids:
                return self._players[next_id]
        return None

    def get_previous(self, player_id):
        if player_id not in self._player_ids:
            raise ValueError("Unknown player id")
        if player_id in self._folder_ids:
            raise ValueError("Inactive player")
        start_index = self._player_ids.index(player_id)
        for i in range(len(self._player_ids) - 1):
            previous_index = (start_index - i - 1) % len(self._player_ids)
            previous_id = self._player_ids[previous_index]
            if previous_id not in self._folder_ids:
                return self._players[previous_id]
        return None

    def is_active(self, player_id):
        if player_id not in self._player_ids:
            raise ValueError("Unknown player id")
        return player_id not in self._folder_ids

    def count_active(self):
        return len(self._player_ids) - len(self._folder_ids)

    def count_active_with_money(self):
        return len([player for player in self.active if player.money > 0])

    @property
    def all(self):
        return [self._players[player_id] for player_id in self._player_ids if player_id not in self._dead_player_ids]

    @property
    def folders(self):
        return [self._players[player_id] for player_id in self._folder_ids]

    @property
    def dead(self):
        return [self._players[player_id] for player_id in self._dead_player_ids]

    @property
    def active(self):
        return [self._players[player_id] for player_id in self._player_ids if player_id not in self._folder_ids]


class GameScores:
    def __init__(self, score_detector):
        self._score_detector = score_detector
        self._players_cards = {}
        self._shared_cards = []

    @property
    def shared_cards(self):
        return self._shared_cards

    def player_cards(self, player_id):
        return self._players_cards[player_id]

    def player_score(self, player_id):
        return self._score_detector.get_score(self._players_cards[player_id] + self._shared_cards)

    def assign_cards(self, player_id, cards):
        self._players_cards[player_id] = self._score_detector.get_score(cards).cards

    def add_shared_cards(self, cards):
        self._shared_cards += cards
