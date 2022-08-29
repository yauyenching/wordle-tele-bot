import os
import jsonpickle
from typing import Any
from telebot import TeleBot, types
from utils.messages import added_text
from classes.WordleStats import WordleStats
from utils.message_handler import extract_score
from pymongo import collection


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

    def __init__(self, db: collection.Collection) -> None:
        self._latest_game = db["latest_game"]
        self.global_data = WordleStats(db["user_data"])

    # --------------------------------------------------GETTERS
    @property
    def latest_game(self) -> int:
        return self._latest_game.find_one({"_id": 0})['latest_game']

    # --------------------------------------------------SETTERS
    @latest_game.setter
    def latest_game(self, edition: int) -> None:
        if edition > self.latest_game:
            self._latest_game.replace_one({"_id": 0},
                                          {"latest_game": edition},
                                          upsert=True)

    # --------------------------------------------------METHODS
    def add_score(self, message: types.Message, bot: TeleBot, debug: bool = False, id: int = 1, name: str = "", txt: str = "") -> None:
        """ Add Wordle score to user database """
        chat_id = message.chat.id
        user_id = message.from_user.id if not debug else id
        username = message.from_user.first_name if not debug else name
        text = message.text if not debug else txt

        edition, tries = extract_score(text)
        self.latest_game = edition

        update, update_msg = self.global_data.update_stats(
            user_id=user_id,
            chat_id=chat_id,
            edition=edition,
            tries=tries,
            username=username
        )

        if update_msg and update:
            bot.send_message(chat_id, added_text(
                username=username, init_score=tries), parse_mode="MarkdownV2")
        elif update_msg and not update:
            bot.reply_to(message,
                         f"Today's Wordle has already been computed into your average\!",
                         parse_mode="MarkdownV2")
        elif not update_msg and not update:
            warning_state = self.global_data.db.find_one({"_id": user_id})['warning']
            if warning_state:
                bot.reply_to(message,
                            "/toggleretroactive is OFF so results for older games do not affect your stats! Use /togglewarning to turn off this warning.")

    def print_scores(self, chat_id: int, user_id: int, cmd: str) -> str:
        """ Send pretty printed requested stats """
        # print(cmd)
        print_func = self.global_data.print_stats if cmd == 'stats' else self.global_data.print_leaderboard

        return print_func(user_id=user_id, chat_id=chat_id, chat_latest_game=self.latest_game)

    def update_data(self, chat_id: int, user_id: int, input: Any, command: str, input_avg: Any = 0) -> None | tuple[int, float]:
        return self.global_data.manual_update(
            user_id=user_id,
            chat_id=chat_id,
            cmd=command,
            input=input,
            input_avg=input_avg
        )

    def clear_data(self, user_id: int) -> None:
        self.global_data.clear(user_id)
        
    def toggle_retroactive(self, user_id: int) -> bool:
        return self.global_data.toggle(user_id)
    
    def toggle_warning(self, user_id: int) -> bool:
        return self.global_data.toggle(user_id, False)
        
    # --------------------------------------------------ADMIN METHODS
    
    def get_latest_game(self) -> str:
        return str(self.latest_game)

    def set_latest_game(self, latest_game: int) -> None:
        self._latest_game.replace_one({"_id": 0},
                                      {"latest_game": latest_game})
        
    def clear_debug(self, admin_id: int) -> None:
        self.global_data.db.delete_many({"member_of_chats": admin_id, "_id": {"$ne": admin_id}})
