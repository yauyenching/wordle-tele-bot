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
    last_active_game: int
      Last active chat
    """

    def __init__(self, db):
        self.db = db

    UserData = namedtuple(
        'UserData', ['username', 'num_games', 'streak', 'score_avg', 'last_game', 'last_active_chat'])

    # #--------------------------------------------------METHOD GETTERS
    # @property
    # def username(self):
    #   return self.user_data

    # @property
    # def num_games(self):
    #   return self.num_games

    # @property
    # def streak(self):
    #   return self.streak

    # @property
    # def score_avg(self):
    #   return self.score_avg

    # @property
    # def last_game(self):
    #   return self.last_game

    # #--------------------------------------------------METHOD SETTERS
    # @username.setter
    # def username(self, username):
    #   username = str(username)
    #   self._username = username

    # @num_games.setter
    # def num_games(self, num_games):
    #   num_games = int(num_games)
    #   self._num_games = num_games

    # @streak.setter
    # def streak(self, streak):
    #   streak = int(streak)
    #   self._streak = streak

    # @score_avg.setter
    # def score_avg(self, score_avg):
    #   score_avg = float(score_avg)
    #   if score_avg <= 7.0:
    #       self._score_avg = score_avg

    # @last_game.setter
    # def last_game(self, last_game):
    #   if last_game > self.last_game:
    #     self._last_game = last_game

    class InvalidAvg(ValueError):
        """Raised when the score avg inputted is higher than 7.0"""
        pass

    class UserNotFound(LookupError):
        """Raised when the user is not found in user base"""
        pass

    # --------------------------------------------------USER METHODS
    def get_user_data(self, user_id: int) -> UserData:
        user_data = self.db.find_one({"_id": user_id}, {"_id": 0})
        if user_data == None:
            raise self.UserNotFound
        else:
            self.UserData(
                user_data['username'],
                user_data['num_games'],
                user_data['streak'],
                user_data['score_avg'],
                user_data['last_game'],
                user_data['last_active_chat']
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
            "member_of_chats": [chat_id]
        }
        self.user_data.insert_one(user_data)

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
            _, num_games, _, score_avg, last_game, last_active_chat = self.get_user_data(
                user_id)

            if edition == last_game:
                self.db.update_one({"_id": self.user_id,
                                    "last_active_chat": {"$ne": chat_id}},
                                   {"last_active_chat": chat_id})
                return (False, last_active_chat == chat_id)
            elif edition >= last_game:
                if edition == last_game + 1:
                    # consecutive day
                    streak_op, streak_val = "$inc", 1
                else:
                    # missed a day
                    streak_op, streak_val = "$set", 0

            new_avg = (score_avg * (num_games - 1) +
                       tries)/num_games
            update = {
                streak_op: {"streak": streak_val},
                "$inc": {"num_games": 1},
                "$set": {"last_game": edition,
                         "score_avg": new_avg}
            } | member_of_chat(chat_id)
            self.db.update_one({"_id": self.user_id}, update)
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

    def manual_update(self, user_id: int, chat_id: int, cmd: str, input: Any, input_avg: Any = 0) -> None:
        attr_dict = {
            'name': (str, "username"),
            'games': (int, "num_games"),
            'streak': (int, "streak"),
            'score_avg': (float, "score_avg"),
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
                {"_id": user_id}, {"$set": {"score_avg": float(new_avg)}} | member_of_chat(chat_id))

        if res.matched_count == 0:
            raise self.UserNotFound

    def print_stats(self, user_id: int, chat_id: int, chat_latest_game: int) -> str:
        self.insert_chat_member(user_id, chat_id)

        user_data = self.get_user_data(user_id)
        self.db.update_one({"_id": user_id} | streak_check(chat_latest_game),
                           {"$set": {"streak": 0}})
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

    # --------------------------------------------------CHAT METHODS
    def get_chat_data(self, chat_id: int) -> list[dict]:
        res = list(self.db.find({"member_of_chats": chat_id},
                                {"_id": 0,
                                 "username": 1,
                                 "num_games": 1,
                                 "streak": 1,
                                 "score_avg": 1,
                                 "last_game": 0,
                                 "last_active_chat": 0,
                                 "member_of_chats": 0}))
        if res == []:
            raise self.UserNotFound
        else:
            return res

    def insert_chat_member(self, user_id: int, chat_id: int) -> None:
        self.db.update_one({"_id": user_id}, member_of_chat(chat_id))

    def print_leaderboard(self, user_id: int, chat_id: int, chat_latest_game: int) -> str:
        self.insert_chat_member(user_id, chat_id)

        chat_data = self.get_chat_data(chat_id)

        self.db.update_one({"member_of_chats": chat_id} | streak_check(chat_latest_game),
                           {"$set": {"streak": 0}})

        leaderboard_df = pd.DataFrame.from_records(chat_data)
        leaderboard_df.columns = ['Name', 'Gms', '🔥', 'Avg.']
        leaderboard_df['Avg.'] = leaderboard_df['Avg.'].apply(
            lambda x: f"{x:.3f}".replace(".", "\."))

        leaderboard_df = leaderboard_df.sort_values(
            by=['Avg.']).reset_index(drop=True)
        leaderboard_df.index += 1
        return f"`{tabulate(leaderboard_df, headers='keys')}`"
