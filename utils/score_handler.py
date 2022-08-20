import re
from telebot import TeleBot
from bot.messages import USER_STATS, ADDED_TEXT
from utils.global_db_handler import save

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
    self._username = str(username) # updated manually ONLY
    self._num_games = 1            # updated with score message or manually
    self._streak = 1               # updated with score message or manually
    self._score_avg = float(tries)   # updated with score message or manually
    self.last_game = int(edition)  # updated with score message ONLY
  
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

  #--------------------------------------------------FUNCTIONS
  def update_score(self, edition: int, tries: int, chat_latest_game: int) -> int | str | None:
    if edition > chat_latest_game:
      return edition
    if edition == self.last_game:
      return "Today's Wordle has already been computed into your average, {}!".format(self.username)
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
    
  def update_streak(self, chat_id: int, score_dict: dict) -> None:
    if self.last_game < score_dict[chat_id]['latest_game']:
      self.streak = 0
      save(score_dict)

  def print_stats(self, chat_id: int, score_dict: dict, bot: TeleBot) -> None:
    self.update_streak(chat_id, score_dict)
    score_avg = "{:.3f}".format(self.score_avg).replace(".", "\.")
    if self.streak > 1:
      streak_status = " 🔥"
    else:
      streak_status = ""
    streak = str(self.streak) + streak_status
    message = "Stats for *{}*:\n\n".format(self.username) + USER_STATS.format(self.username, self.num_games, streak, score_avg)
    bot.send_message(chat_id, message, parse_mode="MarkdownV2")
    
  # def from_json(json_dict: dict) -> dict:
  #   db = {}
  #   for chat_id, chat_data in json_dict.items():
  #     db.update({chat_id: {}})
  #     for chat_id, chat in json_dict.items():
