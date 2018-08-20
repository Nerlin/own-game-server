from typing import List, Dict, Optional


class Player:
    name: str
    score: int

    def __init__(self, name: str, score: int):
        self.name = name
        self.score = score


class Question:
    text: str
    answer: str
    score: int
    disabled: bool
    answering_player: Optional[Player]

    def __init__(self, text: str, answer: str, score: int, disabled: bool = False, answering_player: Player = None):
        self.text = text
        self.answer = answer
        self.score = score
        self.disabled = disabled
        self.answering_player = answering_player

    def accept_answer(self):
        self.answering_player.score += self.score
        self.answering_player = None
        self.disabled = True

    def decline_answer(self):
        self.answering_player.score -= self.score
        self.answering_player = None

    def __copy__(self):
        return Question(
            text=self.text,
            answer=self.answer,
            score=self.score
        )


Theme = str
GameThemes = Dict[Theme, List[Question]]


class GameError(Exception):
    pass


class Game:
    players: List[Player]
    themes_questions: GameThemes
    current_question: Optional[Question]

    class ThemeNotFound(GameError):
        def __init__(self, theme: Theme):
            self.theme = theme

    class QuestionNotFound(GameError):
        def __init__(self, theme: Theme, score: int):
            self.theme = theme
            self.score = score

    class QuestionDisabled(GameError):
        def __init__(self, question: Question):
            self.question = question

    class QuestionIsAlreadySelected(GameError):
        pass

    class QuestionIsNotSelected(GameError):
        pass

    class PlayerIsNotSelected(GameError):
        pass

    class PlayerIsAlreadySelected(GameError):
        def __init__(self, selecting_player):
            self.selecting_player = selecting_player

    def __init__(self):
        self.players = []
        self.themes_questions = {}
        self.current_question = None

    @property
    def players_names(self):
        return (player.name for player in self.players)

    @property
    def is_over(self):
        for theme, questions in self.themes_questions.items():
            for question in questions:
                if not question.disabled:
                    return False
        return True

    def join(self, player_name) -> Player:
        player = Player(name=player_name, score=0)
        self.players.append(player)
        return player

    def leave(self, player):
        self.players.remove(player)

    def select_question(self, theme: Theme, score: int):
        if self.current_question is not None:
            raise Game.QuestionIsAlreadySelected()

        theme_questions = self.themes_questions.get(theme)
        if not theme_questions:
            raise Game.ThemeNotFound(theme)

        for question in theme_questions:
            if question.score == score:
                if question.disabled:
                    raise Game.QuestionDisabled(question)
                self.current_question = question
                break
        else:
            raise Game.QuestionNotFound(theme, score)

    def select_answering_player(self, player: Player):
        if not self.current_question:
            raise Game.QuestionIsNotSelected()

        if self.current_question.answering_player is not None and self.current_question.answering_player != player:
            raise Game.PlayerIsAlreadySelected(player)

        self.current_question.answering_player = player

    def accept_answer(self):
        if not self.current_question:
            raise Game.QuestionIsNotSelected()

        if not self.current_question.answering_player:
            raise Game.PlayerIsNotSelected()

        self.current_question.accept_answer()
        self.current_question = None

    def decline_answer(self):
        if not self.current_question:
            raise Game.QuestionIsNotSelected()

        if not self.current_question.answering_player:
            raise Game.PlayerIsNotSelected()

        self.current_question.decline_answer()

    def skip_question(self):
        if not self.current_question:
            raise Game.QuestionIsNotSelected()

        self.current_question.disabled = True
        self.current_question = None



