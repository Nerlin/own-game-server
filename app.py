import json
import uuid
from typing import Dict, List

from flask import Flask
from flask_socketio import SocketIO, join_room, leave_room, emit

from game import Game, Question, Player


app = Flask(__name__)
socketio = SocketIO(app)


class SocketIOPlayer(Player):
    key: str

    def __init__(self, name: str, score: int):
        super().__init__(name, score)
        self.key = str(uuid.uuid4())


class SocketIOGame(Game):
    game_id: str
    host_key: str
    players_by_key: Dict[str, SocketIOPlayer]

    def __init__(self):
        super().__init__()
        self.game_id = str(uuid.uuid4())
        self.host_key = str(uuid.uuid4())
        self.players_by_key = {}

    def join(self, player_name) -> SocketIOPlayer:
        player = SocketIOPlayer(name=player_name, score=0)
        self.players.append(player)
        self.players_by_key[player.key] = player
        return player

    def leave(self, player: SocketIOPlayer):
        self.players.remove(player)
        del self.players_by_key[player.key]


games: Dict[str, SocketIOGame] = {}
game_themes = {}


def game_method(func):
    def game_method_decorator(message):
        game_id = message.get("game_id")
        if not game_id:
            return emit("fail", {"error": "Game id is not specified.", "status": -1})

        if game_id not in games:
            return emit("fail", {"error": "No game with such id.", "status": -2})

        return func(game=games[game_id], **message)

    return game_method_decorator


def game_host_only(func):
    @game_method
    def game_host_only_decorator(game: SocketIOGame, **kwargs):
        host_key = kwargs.get("host_key")
        if not host_key:
            return emit("fail", {"error": "Host key is required.", "status": -3})

        if game.host_key != host_key:
            return emit("fail", {"error": "Wrong host key.", "status": -4})

        return func(game, **kwargs)

    return game_host_only_decorator


def joined_player_only(func):
    @game_method
    def joined_player_only_decorator(game: SocketIOGame, **kwargs):
        player_key = kwargs.get("player_key")
        if not player_key:
            return emit("fail", {"error": "Player key is required.", "status": -5})

        if player_key not in game.players_by_key:
            return emit("fail", {"error": "Wrong player key.", "status": -6})

        player = game.players_by_key[player_key]
        return func(game, **kwargs, player=player)

    return joined_player_only_decorator


@socketio.on("start_game")
def start_game():
    new_game = SocketIOGame()
    new_game.themes_questions = load_game_themes()

    games[new_game.game_id] = new_game
    emit("game_started", {
        "game_id": new_game.game_id,
        "host_key": new_game.host_key
    })

    emit("games_list_received", list(games.keys()), broadcast=True)


@socketio.on("get_games_list")
def get_games_list():
    emit("games_list_received", list(games.keys()))


@socketio.on("join_game")
@game_method
def join_game(game: SocketIOGame, **message):
    player_name = message["player_name"]
    player = game.join(player_name)

    join_room(game.game_id)
    emit("joined_game", player.key)
    emit("player_joined", [get_player_dao(game_player) for game_player in game.players], room=game.game_id)


@socketio.on("leave_game")
@joined_player_only
def leave_game(game: SocketIOGame, player: SocketIOPlayer, **message):
    game.leave(player)
    leave_room(game.game_id)
    emit("player_left", [get_player_dao(game_player) for game_player in game.players], room=game.game_id)


@socketio.on("sync")
@game_method
def sync(game: SocketIOGame, **message):
    host_key = message.get("host_key")
    if host_key is not None:
        if game.host_key != host_key:
            return emit("fail", {"error": "Wrong host key.", "status": -4})
        else:
            join_room(game.game_id)
            return emit("synced", get_game_dao(game))

    player_key = message.get("player_key")
    if player_key not in game.players_by_key:
        return emit("fail", {"error": "Wrong player key.", "status": -6})
    else:
        join_room(game.game_id)
        return emit("synced", get_game_dao(game))


@socketio.on("select_question")
@game_host_only
def select_question(game: SocketIOGame, **message):
    theme = message["theme"]
    score = int(message["score"])

    try:
        game.select_question(theme, score)
    except game.QuestionIsAlreadySelected:
        return emit("fail", {"error": "Question is already selected.", "status": 1})
    except game.ThemeNotFound:
        return emit("fail", {"error": "No such theme in this game.", "status": 2})
    except game.QuestionDisabled:
        return emit("fail", {"error": "Question is disabled.", "status": 3})
    except game.QuestionNotFound:
        return emit("fail", {"error": "Question is not found.", "status": 4})

    return emit("question_selected", get_game_question_dao(game.current_question), room=game.game_id)


@socketio.on("select_answering_player")
@joined_player_only
def select_answering_player(game: SocketIOGame, player: SocketIOPlayer, **message):
    try:
        game.select_answering_player(player)
    except game.QuestionIsNotSelected:
        return emit("fail", {"error": "Question is not selected.", "status": 5})
    except game.PlayerIsAlreadySelected:
        return emit("fail", {"error": "Player is already selected.", "status": 7})

    return emit("selected_answering_player", get_player_dao(game.current_question.answering_player), room=game.game_id)


def get_game_dao(game: SocketIOGame):
    current_question_dao = None
    if game.current_question:
        current_question_dao = get_game_question_dao(game.current_question)

    return {
        "players": [get_player_dao(player) for player in game.players],
        "themes_questions": {
            theme: [get_game_question_dao(question) for question in questions]
            for theme, questions in game.themes_questions.items()
        },
        "current_question": current_question_dao,
        "is_over": game.is_over
    }


def get_game_question_dao(question: Question):
    return {
        "text": question.text,
        "score": question.score,
        "disabled": question.disabled,
    }


def get_player_dao(player: Player):
    return {
        "name": player.name,
        "score": player.score
    }


@socketio.on("decline_answer")
@game_host_only
def decline_answer(game: SocketIOGame, **message):
    try:
        game.decline_answer()
    except game.QuestionIsNotSelected:
        return emit("fail", {"error": "Question is not selected.", "status": 5})
    except game.PlayerIsNotSelected:
        return emit("fail", {"error": "Player is not selected.", "status": 6})

    return emit("synced", get_game_dao(game), room=game.game_id)


@socketio.on("accept_answer")
@game_host_only
def accept_answer(game: SocketIOGame, **message):
    try:
        game.accept_answer()
    except game.QuestionIsNotSelected:
        return emit("fail", {"error": "Question is not selected.", "status": 5})
    except game.PlayerIsNotSelected:
        return emit("fail", {"error": "Player is not selected.", "status": 6})

    return emit("synced", get_game_dao(game), room=game.game_id)


@socketio.on("skip_question")
@game_host_only
def skip_question(game: SocketIOGame, **message):
    try:
        game.skip_question()
    except game.QuestionIsNotSelected:
        return emit("fail", {"error": "Question is not selected.", "status": 5})

    return emit("synced", get_game_dao(game), room=game.game_id)


def load_game_themes():
    with open("default_theme.json") as file:
        themes_questions = json.load(file)
        for theme, raw_questions in themes_questions.items():
            themes_questions[theme] = [
                Question(**question) for question in raw_questions
            ]
        return themes_questions


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000)
