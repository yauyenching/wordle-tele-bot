import os
import jsonpickle
from typing import Any
from telebot import TeleBot, types
from utils.messages import added_text
from classes.WordleStats import WordleStats
from utils.message_handler import extract_score
import pandas as pd
from tabulate import tabulate

NO_DATA_MSG = "No data recorded yet\! Share Wordle results to add yourself to the database\."


class GlobalDB:
    """
    Class storing global chat data for Wordle stats.

    Attributes
    ----------
    latest_game: int
        Latest game globally for streak purposes
    chat_users: dict[int, list[int]]
        Dictionary with chat id as key and list of user ids as value
    user_data: dict[int, WordleStats]
        Dictionary with user id as key and user data as value
    """

    def __init__(self, init_game=0, init_chat_db={}, init_user_db={}) -> None:
        self._latest_game: int = init_game
        self.chat_users: dict[int, list[int]] = init_chat_db
        self.user_data: dict[int, WordleStats] = init_user_db

    # --------------------------------------------------GETTERS
    @property
    def latest_game(self) -> int:
        return self._latest_game

    # --------------------------------------------------SETTERS
    @latest_game.setter
    def latest_game(self, edition: int) -> None:
        if edition > self.latest_game:
            self._latest_game = edition

    # --------------------------------------------------METHODS
    def get_chat_members(self, chat_id: int) -> list[int] | None:
        return self.chat_users.get(chat_id)

    def get_chat_data(self, chat_id: int) -> list[WordleStats] | None:
        chat_members_ids = self.get_chat_members(chat_id)
        if chat_members_ids == None:
            self.chat_users[chat_id] = []
            return None
        else:
            res = map(lambda user_id: self.get_user_data(
                user_id), chat_members_ids)
            return list(filter(lambda x: x is not None, res))

    def get_user_data(self, user_id: int) -> WordleStats | None:
        return self.user_data.get(user_id)

    def is_in_chat(self, chat_id: int, user_id: int) -> bool:
        chat_users = self.get_chat_members(chat_id)
        if chat_users == None:
            self.chat_users[chat_id] = []
            return False
        else:
            return user_id in chat_users

    def add_score(self, message: types.Message, bot: TeleBot, debug: bool = False, id: int = 1, name: str = "", txt: str = "") -> None:
        """ Add Wordle score to user database """
        chat_id = message.chat.id
        user_id = message.from_user.id if not debug else id
        username = message.from_user.first_name if not debug else name
        text = message.text if not debug else txt

        user_data = self.get_user_data(user_id)

        edition, tries = extract_score(text)
        self.latest_game = edition

        is_in_chat = self.is_in_chat(chat_id, user_id)
        if not is_in_chat:
            self.chat_users[chat_id].append(user_id)

        if user_data == None:  # no data recorded for user yet
            self.user_data[user_id] = WordleStats(
                username, edition, tries, chat_id)
            self.save_json()
            bot.send_message(chat_id, added_text(
                username=username, init_score=tries), parse_mode="MarkdownV2")
        else:  # data for user exists, update user data
            update, same_chat = user_data.update_stats(edition, tries, chat_id)
            if update:
                self.save_json()
            else:
                if not is_in_chat:
                    self.save_json()
                if same_chat:
                    bot.reply_to(message,
                                 f"Today's Wordle has already been computed into your average\!",
                                 parse_mode="MarkdownV2")

    def print_leaderboard(self, chat_data: list[WordleStats]) -> tuple[str, bool]:
        fields = ['username', 'num_games', 'streak', 'score_avg']
        streak_updated = list(
            map(lambda x: x.update_streak(self.latest_game), chat_data))
        leaderboard_df = pd.DataFrame(
            [{fn: getattr(user_data, fn) for fn in fields}
                for user_data in chat_data]
        )
        leaderboard_df.columns = ['Name', 'Gms', '🔥', 'Avg.']
        leaderboard_df['Avg.'] = leaderboard_df['Avg.'].apply(
            lambda x: f"{x:.3f}".replace(".", "\."))

        leaderboard_df = leaderboard_df.sort_values(
            by=['Avg.']).reset_index(drop=True)
        leaderboard_df.index += 1
        return (f"`{tabulate(leaderboard_df, headers='keys')}`", any(streak_updated))

    def print_scores(self, chat_id: int, user_id: int = 0) -> str:
        """ Send pretty printed requested stats """
        if user_id:
            cmd_msg = "your stats"
        else:
            cmd_msg = "the chat's leaderboard"
        no_update_msg = NO_DATA_MSG + \
            f" After being added, you will then be able to print {cmd_msg}\."

        if user_id:
            user_data = self.get_user_data(user_id)
            if user_data == None:
                return no_update_msg
            else:
                print_msg, streak_updated = user_data.print_stats(
                    self.latest_game)
        else:
            chat_data = self.get_chat_data(chat_id)
            if chat_data == None:
                return no_update_msg
            else:
                print_msg, streak_updated = self.print_leaderboard(chat_data)

        if streak_updated:
            self.save_json()
        return print_msg

    def update_data(self, chat_id: int, user_id: int, input: Any, command: str, input_avg: Any = 0) -> str:
        no_update_msg = NO_DATA_MSG + \
            " After being added, you will then be able to update your user data\."

        user_data = self.get_user_data(user_id)

        res = f"Successfully updated your {command} to *{input}*\!".replace(
            ".", "\.")

        if user_data == None:
            return no_update_msg
        elif command == 'name':
            user_data.username = input
        elif command == 'games':
            user_data.num_games = input
        elif command == 'streak':
            user_data.streak = input
        elif command == 'average':
            user_data.score_avg = input
            new_avg = float(input)
            res = f"Successfully updated your {command} to *{new_avg:.3f}*\!".replace(
            ".", "\.")
            if float(input) > 7.0:
                return "Sorry, you can only update your score average to have a max value of *7\.0*\!"
        else:
            old_games = int(input)
            old_avg = float(input_avg)
            score_avg = user_data.score_avg
            num_games = user_data.num_games

            new_games = num_games + old_games
            new_avg = ((old_avg * old_games) +
                       (score_avg * num_games)) / new_games

            user_data.num_games = new_games
            user_data.score_avg = new_avg

            res = f"Successfully updated your games and average to *{new_games}* and *{new_avg:.3f}*\!".replace(
                ".", "\.")

        self.save_json()
        return res

    def clear_data(self, user_id: int) -> str:
        user_data = self.get_user_data(user_id)
        no_data_msg = "No user data to clear!"

        user_data = self.get_user_data(user_id)

        if user_data == None:
            return no_data_msg
        else:
            _ = self.user_data.pop(user_id)
            self.save_json()
            return "Cleared user database."

    def save_json(self, filename: str = "database.json") -> None:
        """ Save score in local .json file for persistence data storage """
        f = open(filename, "w+", encoding="utf-8")
        f.write(jsonpickle.encode(self, indent=4, keys=True))
        f.close()

    def load(filename: str = "database.json"):
        if os.path.exists(filename):
            f = open(filename)
            return jsonpickle.decode(f.read(), keys=True)
        else:
            return GlobalDB()

    def pprint(self) -> None:
        print(jsonpickle.encode(self, indent=4))

    def restart(self) -> None:
        self._latest_game = 0
        self.chat_users = {}
        self.user_data = {}
        self.save_json()

    def set_latest_game(self, latest_game: int) -> None:
        self._latest_game = latest_game
        self.save_json()
