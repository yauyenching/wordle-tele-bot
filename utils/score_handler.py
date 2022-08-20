from pickletools import int4
import re
from telebot import TeleBot
from bot.messages import user_stats

class WordleStats:
  def __init__(self, username, edition, tries):
    """Class storing Wordle score data aggregates.

    Parameters
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
    """
    self._username = username # updated manually ONLY
    self._num_games = 1       # updated with score message or manually
    self._streak = 1          # updated with score message or manually
    self._score_avg = tries   # updated with score message or manually
    self._last_game = edition  # updated with score message ONLY
  
  #--------------------------------------------------GETTERS
  @property
  def username(self):
    return self._username
  
  @property
  def num_games(self):
    return self._num_games
  
  @property
  def streak(self):
    return self._streak

  @property
  def score_avg(self):
    return self._score_avg
  
  @property
  def last_game(self):
    return self._last_game

  #--------------------------------------------------SETTERS
  @username.setter
  def username(self, username):
    username = str(username)
    self._username = username
    
  @num_games.setter
  def num_games(self, num_games):
    num_games = int(num_games)
    self._num_games = num_games

  @streak.setter
  def streak(self, streak):
    streak = int(streak)
    self._streak = streak

  @score_avg.setter
  def score_avg(self, score_avg):
    score_avg = float(score_avg)
    self._score_avg = score_avg
    
  @last_game.setter
  def last_game(self, last_game):
    if last_game > self.last_game:
      self._last_game = last_game

  #--------------------------------------------------METHODS
  def update_stats(self, edition: int, tries: int) -> str | None:
    if edition == self.last_game:
      return f"Today's Wordle has already been computed into your average, {self.username}\!"
    elif edition >= self.last_game:
      if edition == self.last_game + 1:
        # consecutive day
        self.streak += 1
      else:
        # missed a day
        self.streak = 1
      self.last_game = edition
    self.num_games += 1
    self.score_avg = (self.score_avg * (self.num_games - 1) +
                      tries)/self.num_games
    # save(score_dict)
    
  def update_streak(self, chat_latest_game: int) -> bool:
    if self.last_game < chat_latest_game:
      self.streak = 0
      return True
    else:
      return False

  def print_stats(self, chat_latest_game: int) -> tuple[str, bool]:
    streak_updated = self.update_streak(chat_latest_game)
    if self.streak > 1:
      streak_status = " 🔥"
    else:
      streak_status = ""
    streak = str(self.streak) + streak_status
    stats_msg = (
      f"Stats for *{self.username}*:\n\n"
      + user_stats(self.username, self.num_games, streak, self.score_avg)
    )
    return (stats_msg, streak_updated)
    # "Stats for *{}*:\n\n".format(self.username) + USER_STATS.format(self.username, self.num_games, streak, score_avg)
    
  # def from_json(json_dict: dict) -> dict:
  #   db = {}
  #   for chat_id, chat_data in json_dict.items():
  #     db.update({chat_id: {}})
  #     for chat_id, chat in json_dict.items():
