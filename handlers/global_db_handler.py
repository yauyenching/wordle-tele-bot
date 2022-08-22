import re
import os
import pipe
import jsonpickle
from typing import Any
from handlers.chat_db_handler import ChatDB
from telebot import TeleBot
from utils.messages import added_text
from handlers.score_handler import WordleStats

NO_DATA_MSG = "No data recorded for you yet\! Share Wordle results to add yourself to the database\."


class GlobalDB:
    """
    Class storing global chat data for Wordle stats.

    Attributes
    ----------
    chat_data: dict[int, ChatDB]
        Dictionary with chat id as key and chat data as value
    """

    def __init__(self, init_db={}) -> None:
        self.global_data: dict[int, ChatDB] = init_db

    # --------------------------------------------------METHODS
    def get_chat_data(self, chat_id: int) -> ChatDB | None:
        return self.global_data.get(chat_id)

    def update_data(self, chat_id: int, user_id: int, username: str, input: Any, command: str, input_avg: Any = 0) -> str:
        no_update_msg = NO_DATA_MSG + \
            " After being added, you will then be able to update your user data\."
        chat_data = self.get_chat_data(chat_id)
        if chat_data == None:
            return no_update_msg

        user_data = chat_data.get_user_data(user_id)
        
        res = f"Successfully updated {command} for @{username} to *{input}*\!".replace(".", "\.")

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
            if float(input) > 7.0:
                return "Sorry, you can only update your score average to have a max value of *7\.0*\!"
        else:
            old_games = int(input)
            old_avg = float(input_avg)
            score_avg = user_data.score_avg
            num_games = user_data.num_games
            
            new_games = num_games + old_games
            new_avg = ((old_avg * old_games) + (score_avg * num_games)) / new_games
            
            user_data.num_games = new_games
            user_data.score_avg = new_avg
            
            res = f"Successfully updated games and average for @{username} to *{new_games}* and *{new_avg:.3f}*\!".replace(".", "\.")

        self.save_json()
        return res

    def clear_data(self, chat_id: int, user_id: int = 0) -> str:
        request_type = 'user' if user_id else 'chat'
        no_data_msg = f"No {request_type} data to clear!"

        chat_data = self.get_chat_data(chat_id)

        if chat_data == None:
            return no_data_msg
        elif not user_id:
            _ = self.global_data.pop(chat_id)
            self.save_json()
            return "Cleared chat database."
        else:
            user_data = chat_data.get_user_data(user_id)
            if user_data == None:
                return "No user data to clear!"
            else:
                chat_data.clear(user_id)
                self.save_json()
                return "Cleared user database."

    def add_score(self, chat_id: int, user_id: int, message: str, username: str, bot: TeleBot) -> None:
        """ Add Wordle score to chat database for user """
        # Use regex to extract Wordle edition and tries
        m = re.match(
            r"Wordle\s(?P<edition>\d+)\s(?P<tries>[0-6X])/6\n{2}(?:(?:[🟨🟩⬛️⬜️]+)(?:\r?\n)){1,6}", message)
        edition = int(m.group('edition'))
        tries = m.group('tries')
        if tries == "X":
            tries = 7.0
        else:
            tries = float(tries)

        chat_data = self.get_chat_data(chat_id)
        new_user_msg = added_text(username=username, init_score=tries)

        if chat_data == None:  # no data recorded for chat yet
            # initialize db for chat using Wordle results
            self.global_data[chat_id] = ChatDB(latest_game=edition,
                                               init_stats=WordleStats(
                                                   username, edition, tries),
                                               user_id=user_id)
            bot.send_message(chat_id, new_user_msg, parse_mode="MarkdownV2")
            self.save_json()
        else:  # data for chat exists, update user data
            res = chat_data.update_user_data(
                user_id=user_id, username=username, edition=edition, tries=tries)
            if isinstance(res, str):  # data already recorded for today's Wordle
                bot.send_message(chat_id, res)
            else:  # update successful
                self.save_json()
                if res:  # new user added
                    bot.send_message(chat_id, new_user_msg,
                                     parse_mode="MarkdownV2")

    def print_scores(self, chat_id: int, user_id: int = 0) -> str:
        """ Send pretty printed requested stats """
        if user_id:
            cmd_msg = "your stats"
        else:
            cmd_msg = "the chat's leaderboard"
        no_update_msg = NO_DATA_MSG + \
            f" After being added, you will then be able to print {cmd_msg}\."

        chat_data = self.get_chat_data(chat_id)
        if chat_data == None:
            return no_update_msg
        # print(chat_data)
        user_data = chat_data.get_user_data(user_id)
        # print(user_data)

        if user_id and user_data == None:
            return no_update_msg
        elif user_id:
            print_msg, streak_updated = user_data.print_stats(
                chat_data.latest_game)
            # print_msg, streak_updated = chat_data.print_stats_for_user(user_id)
        else:
            print_msg, streak_updated = chat_data.print_leaderboard()
        if streak_updated:
            self.save_json()
        return print_msg

    def save_json(self, filename: str = "database.json") -> None:
        """ Save score in local .json file for persistence data storage """
        # print(os.getcwd())
        f = open(filename, "w+", encoding="utf-8")
        f.write(jsonpickle.encode(self.global_data, indent=4, keys=True))
        f.close()

    def load(filename: str = "database.json") -> dict[int, ChatDB]:
        print(os.path.exists(filename))
        if os.path.exists(filename):
            f = open(filename)
            res = jsonpickle.decode(f.read(), keys=True)
            # print(res)
            print(type(list(res.keys())[0]))
            return res
        else:
            return {}

    def pprint(self) -> None:
        print(jsonpickle.encode(self.global_data))
        # print(type(list(self.global_data.keys())[0]))
