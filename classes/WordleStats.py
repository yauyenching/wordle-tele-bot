from typing import Any
from utils.messages import user_stats
from collections import namedtuple
from tabulate import tabulate
import pandas as pd


def streak_check(chat_latest_game: int) -> dict:
    return {"last_game": {"$lte": chat_latest_game - 2}}


def member_of_chat(chat_id: int) -> dict:
    return {"$addToSet": {"member_of_chats": chat_id}}


class WordleStats:
    """Class storing Wordle score data aggregates.

    Attributes
    ----------
    username: str
        Telegram user first name
    num_games: int
        Total number of games played
    streak: int
        Current running Wordle streak
    score_avg: float
        Total average score
    last_game: int
        Last Wordle edition played
    last_active_chat: int
        Last active chat
    members_of_chat: list[int]
        List of chats that user is apart of
    toggle_retroactive: bool
        State of user-allowed retroactive updates
    toggle_warnings: bool
        State of warning notifications for attempted retroactive updates
    """

    def __init__(self, db):
        self.db = db

    UserData = namedtuple(
        'UserData', ['username', 'num_games', 'streak', 'score_avg', 'last_game', 'last_active_chat', 'toggle_retroactive'])

    class InvalidAvg(Exception):
        """Raised when the score avg inputted is higher than 7.0"""
        pass

    class UserNotFound(Exception):
        """Raised when the user is not found in user base"""
        pass
    
    class RetroactiveOff(Exception):
        """
        Raised when the user tries to update the database with an old Wordle result
        when toggle_retroactive is turned off
        """
        

    # --------------------------------------------------USER METHODS
    def toggle(self, user_id: int, retroactive: bool = True) -> bool:
        setting = 'toggle_retroactive' if retroactive else 'warning'
        old_state = self.db.find_one({"_id": user_id})[setting]
        new_state = not old_state
        self.db.update_one({"_id": user_id},
                           {"$set": {setting: new_state}})
        return new_state

    def get_user_data(self, user_id: int) -> UserData:
        user_data = self.db.find_one({"_id": user_id}, {"_id": 0})
        if user_data == None:
            raise self.UserNotFound
        else:
            return self.UserData(
                user_data['username'],
                user_data['num_games'],
                user_data['streak'],
                user_data['score_avg'],
                user_data['last_game'],
                user_data['last_active_chat'],
                user_data['toggle_retroactive']
            )

    def insert_user_data(self, user_id: int, username: str, edition: int, tries: float, chat_id: int) -> None:
        user_data = {
            "_id": user_id,
            "username": username,
            "num_games": 1,
            "streak": 1,
            "score_avg": tries,
            "last_game": edition,
            "last_active_chat": chat_id,
            "member_of_chats": [chat_id],
            "toggle_retroactive": False,
            "warning": True
        }
        self.db.insert_one(user_data)

    def update_stats(self, user_id: int, chat_id: int, edition: int, tries: int, username: str) -> tuple[bool, bool]:
        """ 
        Update or insert user stats based on Wordle score

        Parameters:
            user_id (int): Telegram user id
            chat_id (int): Telegram chat id
            edition (int): Wordle edition
            tries (int): Wordle tries

        Returns:
            tuple containing

            - update (bool): Whether update has persisted
            - update_msg (bool): Whether to send message (message content dependent on update)
        """
        try:
            _, num_games, _, score_avg, last_game, last_active_chat, retroactive_updates = self.get_user_data(
                user_id)

            last_game_update = {"last_game": edition}
            streak_inc = {"streak": 1}
            streak_reset = {"streak": 1}
            if edition == last_game:
                self.db.update_one({"_id": user_id,
                                    "last_active_chat": {"$ne": chat_id}},
                                   {"$set": {"last_active_chat": chat_id}} | member_of_chat(chat_id))
                return (False, last_active_chat == chat_id)
            elif edition > last_game:
                if edition == last_game + 1:
                    # consecutive day
                    streak_reset = {}
                else:
                    # missed a day
                    streak_inc = {}
            else:
                streak_inc, streak_reset, last_game_update = {}, {}, {}
                if not retroactive_updates:
                    raise self.RetroactiveOff

            new_avg = (score_avg * num_games +
                       tries)/(num_games + 1)
            # print(new_avg)
            # print(streak_inc)
            # print(streak_reset)
            update = {
                "$inc": {"num_games": 1} | streak_inc,
                "$set": {"score_avg": new_avg} | streak_reset | last_game_update
            } | member_of_chat(chat_id)
            self.db.update_one({"_id": user_id}, update)
            return (True, False)
        except self.UserNotFound:
            self.insert_user_data(
                user_id=user_id,
                username=username,
                edition=edition,
                tries=tries,
                chat_id=chat_id
            )
            return (True, True)

    def manual_update(self, user_id: int, chat_id: int, cmd: str, input: Any, input_avg: Any = 0) -> None | tuple[int, float]:
        attr_dict = {
            'name': (str, "username"),
            'games': (int, "num_games"),
            'streak': (int, "streak"),
            'average': (float, "score_avg"),
        }

        if cmd != 'adjust':
            if cmd == 'average' and float(input) > 7.0:
                raise self.InvalidAvg
            change_type, key = attr_dict[cmd]
            res = self.db.update_one(
                {"_id": user_id}, {"$set": {key: change_type(input)}} | member_of_chat(chat_id))
        else:
            user_data = self.get_user_data(user_id)
            score_avg = user_data.score_avg
            num_games = user_data.num_games
            old_games = int(input)
            old_avg = float(input_avg)
            if old_avg > 7.0:
                raise self.InvalidAvg

            new_games = num_games + old_games
            new_avg = ((old_avg * old_games) +
                       (score_avg * num_games)) / new_games
            res = self.db.update_one(
                {"_id": user_id},
                {"$set": {"score_avg": float(
                    new_avg), "num_games": int(new_games)}}
                | member_of_chat(chat_id)
            )
            return (new_games, new_avg)

        if res.matched_count == 0:
            raise self.UserNotFound

    def print_stats(self, user_id: int, chat_id: int, chat_latest_game: int) -> str:
        self.insert_chat_member(user_id, chat_id)
        self.db.update_one({"_id": user_id} | streak_check(chat_latest_game),
                           {"$set": {"streak": 0}})
        user_data = self.get_user_data(user_id)

        if user_data.streak > 1:
            streak_status = " 🔥"
        else:
            streak_status = ""
        streak = str(user_data.streak) + streak_status
        stats_msg = (
            f"Stats for *{user_data.username}*:\n\n"
            + user_stats(user_data.username, user_data.num_games,
                         streak, user_data.score_avg)
        )
        return stats_msg

    def clear(self, user_id: int) -> None:
        res = self.db.delete_one({"_id": user_id})
        if res.deleted_count == 0:
            raise self.UserNotFound

    # --------------------------------------------------CHAT METHODS
    def get_chat_data(self, chat_id: int) -> list[dict]:
        res = list(self.db.find({"member_of_chats": chat_id},
                                {"_id": 0,
                                 "username": 1,
                                 "num_games": 1,
                                 "streak": 1,
                                 "score_avg": 1}))
        if res == []:
            raise self.UserNotFound
        else:
            return res

    def insert_chat_member(self, user_id: int, chat_id: int) -> None:
        self.db.update_one({"_id": user_id}, member_of_chat(chat_id))

    def print_leaderboard(self, user_id: int, chat_id: int, chat_latest_game: int) -> str:
        self.insert_chat_member(user_id, chat_id)
        self.db.update_many({"member_of_chats": chat_id} | streak_check(chat_latest_game),
                            {"$set": {"streak": 0}})
        chat_data = self.get_chat_data(chat_id)

        leaderboard_df = pd.DataFrame.from_records(chat_data)
        leaderboard_df.columns = ['Name', 'Gms', '🔥', 'Avg.']
        leaderboard_df['Avg.'] = leaderboard_df['Avg.'].apply(
            lambda x: f"{x:.3f}".replace(".", "\."))

        leaderboard_df = leaderboard_df.sort_values(
            by=['Avg.']).reset_index(drop=True)
        leaderboard_df.index += 1
        return f"`{tabulate(leaderboard_df, headers='keys')}`"
