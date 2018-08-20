import pytest

from game import Game, Question


test_theme = "TestTheme"


def setup_game_with_themes():
    game = Game()
    game.themes_questions = {
        test_theme: [
            Question(text="Test Question", answer="Test Answer", score=100),
            Question(text="Test Other Question", answer="Test Answer", score=200)
        ]
    }
    return game


def setup_game_players(game: Game):
    game.join("Test Player #1")
    game.join("Test Player #2")
    game.join("Test Player #3")


def setup_game_selected_question(game: Game):
    game_question = game.themes_questions[test_theme][0]
    game.select_question(test_theme, game_question.score)


def setup_game_answering_player(game: Game):
    player = game.players[0]
    game.select_answering_player(player)


def test_start_game():
    game = setup_game_with_themes()
    assert not game.is_over


def test_join_game():
    game = Game()
    joined_player = game.join("Test Player")
    assert joined_player.name == "Test Player"
    assert joined_player in game.players
    assert joined_player.score == 0


def test_leave_game():
    game = Game()
    joined_player = game.join("Test Player")
    game.leave(joined_player)
    assert joined_player not in game.players


def test_select_question():
    game = setup_game_with_themes()
    questions = game.themes_questions[test_theme]
    expected_question = questions[0]

    game.select_question(test_theme, expected_question.score)
    assert game.current_question == expected_question
    assert not game.current_question.disabled
    assert game.current_question.answering_player is None


def test_selected_theme_not_found():
    game = setup_game_with_themes()
    with pytest.raises(game.ThemeNotFound):
        game.select_question("InvalidTheme", score=100)


def test_selected_score_not_found():
    game = setup_game_with_themes()
    with pytest.raises(game.QuestionNotFound):
        game.select_question(test_theme, score=-100)


def test_cannot_select_disabled_question():
    game = setup_game_with_themes()
    expected_question = game.themes_questions[test_theme][0]
    expected_question.disabled = True

    with pytest.raises(game.QuestionDisabled):
        game.select_question(test_theme, expected_question.score)


def test_select_answering_player():
    game = setup_game_with_themes()
    setup_game_players(game)
    setup_game_selected_question(game)

    player = game.players[0]
    game.select_answering_player(player)
    assert game.current_question.answering_player == player


def test_cannot_select_answering_player_if_question_is_not_selected():
    game = setup_game_with_themes()
    setup_game_players(game)

    player = game.players[0]
    with pytest.raises(game.QuestionIsNotSelected):
        game.select_answering_player(player)


def test_cannot_select_answering_player_if_player_is_already_selected():
    game = setup_game_with_themes()
    setup_game_players(game)
    setup_game_selected_question(game)
    setup_game_answering_player(game)

    player = game.players[1]
    with pytest.raises(game.PlayerIsAlreadySelected):
        game.select_answering_player(player)


def test_accept_answer():
    game = setup_game_with_themes()
    setup_game_players(game)
    setup_game_selected_question(game)
    setup_game_answering_player(game)

    answering_player = game.current_question.answering_player
    previous_player_score = answering_player.score
    previous_question = game.current_question

    game.accept_answer()
    assert game.current_question is None
    assert previous_question.disabled
    assert answering_player.score == previous_player_score + previous_question.score


def test_cannot_accept_answer_if_question_is_not_selected():
    game = setup_game_with_themes()
    setup_game_players(game)

    with pytest.raises(game.QuestionIsNotSelected):
        game.accept_answer()


def test_cannot_accept_answer_if_player_is_not_selected():
    game = setup_game_with_themes()
    setup_game_players(game)
    setup_game_selected_question(game)

    with pytest.raises(game.PlayerIsNotSelected):
        game.accept_answer()


def test_decline_answer():
    game = setup_game_with_themes()
    setup_game_players(game)
    setup_game_selected_question(game)
    setup_game_answering_player(game)

    answering_player = game.current_question.answering_player
    previous_score = answering_player.score
    previous_question = game.current_question

    game.decline_answer()
    assert game.current_question is None
    assert previous_question.disabled
    assert answering_player.score == previous_score - previous_question.score


def test_cannot_decline_answer_if_question_is_not_selected():
    game = setup_game_with_themes()

    with pytest.raises(game.QuestionIsNotSelected):
        game.decline_answer()


def test_cannot_decline_answer_if_player_is_not_selected():
    game = setup_game_with_themes()
    setup_game_selected_question(game)

    with pytest.raises(game.PlayerIsNotSelected):
        game.decline_answer()


def test_skip_question():
    game = setup_game_with_themes()
    setup_game_players(game)
    setup_game_selected_question(game)
    setup_game_answering_player(game)

    skipped_question = game.current_question

    game.skip_question()
    assert game.current_question is None
    assert skipped_question.disabled


def test_cannot_skip_question_if_question_is_not_selected():
    game = setup_game_with_themes()

    with pytest.raises(game.QuestionIsNotSelected):
        game.skip_question()
