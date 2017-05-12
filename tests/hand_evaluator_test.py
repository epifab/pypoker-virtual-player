from virtual_player.card import Card
from virtual_player.score_detector import HandEvaluator, HoldemPokerScoreDetector


def test_hand_strength_gives_number_between_0_and_1():
    my_card = [Card(4, 1), Card(3, 0)]
    board = [Card(14, 0), Card(9, 3), Card(12, 2)]
    assert 0 <= HandEvaluator(HoldemPokerScoreDetector()).hand_strength(my_card, board) <= 1
