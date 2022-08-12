import telebot
from telebot import types
import env
import re
from tabulate import tabulate
import pandas as pd

API_KEY = env.API_KEY
# print(API_KEY) # ensure that API_KEY is correctly stored

bot = telebot.TeleBot(API_KEY)

"""Dictionary with Telegram user id as key and class as value"""
score_dict = dict()

USER_STATS = (
              "`Name: {} \n"
              "\# of Games : {} \n"
              "Streak: {}\n"
              "Avg. Score: {}/6`"
              )

ADDED_TEXT = ("New Wordle champion *{}* added to the leaderboard with the stats:"
              "\n\n"
              + USER_STATS.format({}, 1, 1, {}) +
              "\n\n"
              "To manually update any of these values, use /name, /games, /streak, and /average\.")


class WordleScore:
  def __init__(self, username, edition, tries):
    """Class storing a Wordle Score.

    Parameters
    ----------
    user_name: str
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
    self.last_game = edition  # updated with score message ONLY
  
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
  def update_score(self, chat_id, edition, tries):
    if edition == self.last_game:
      return bot.send_message(chat_id, "Today's Wordle has already been computed into your average, {}!".format(self.username))
    elif edition >= self.last_game:
      if edition == self.last_game + 1:
        # consecutive day
        self.streak += 1
      else:
        # missed a day
        self.streak = 1
      self.last_game = edition
    self.num_games += 1
    bot.send_message(chat_id, self.score_avg)
    self.score_avg = (self.score_avg * (self.num_games - 1) +
                      tries)/self.num_games
    bot.send_message(chat_id, self.score_avg)
    # self.print_stats(chat_id)

  def print_stats(self, chat_id):
    score_avg = str(round(self.score_avg, 2)).replace(".", "\.")
    if self.streak > 1:
      streak_status = " 🔥"
    else:
      streak_status = ""
    streak = str(self.streak) + streak_status
    message = "Stats for *{}*:\n\n".format(self.username) + USER_STATS.format(self.username, self.num_games, streak, score_avg)
    bot.send_message(chat_id, message, parse_mode="MarkdownV2")


@bot.message_handler(commands=['greet'])
def greet(message):
  bot.send_message(message.chat.id, "Hey! How's it going?")


@bot.message_handler(regexp='Wordle\s(?P<edition>\d+)\s(?P<tries>[0-6X])/6\n{2}(?:(?:[🟨🟩⬛️]+)(?:\r?\n)){1,6}')
def add_score(message):
  m = re.match(
      r"Wordle\s(?P<edition>\d+)\s(?P<tries>[0-6X])/6\n{2}(?:(?:[🟨🟩⬛️]+)(?:\r?\n)){1,6}", message.text)
  user_id = message.from_user.id
  user_name = message.from_user.first_name
  user_score = score_dict.get(user_id)
  edition = int(m.group('edition'))
  tries = m.group('tries')
  if tries == "X":
    tries = 7.0
  else:
    tries = float(tries)
  if user_score == None:
    score_dict[user_id] = WordleScore(user_name, edition, tries)
    bot.send_message(message.chat.id, ADDED_TEXT.format(
        user_name, user_name, tries), parse_mode="MarkdownV2")
  else:
    user_score.update_score(message.chat.id, edition, tries)


@bot.message_handler(commands=['stats'])
def stats(message):
  user_id = message.from_user.id
  user_score = score_dict.get(user_id)
  if user_score == None:
    bot.send_message(message.chat.id, "No data recorded for you yet! Share Wordle results to add yourself to the database.")
  else:
    user_score.print_stats(message.chat.id)


# @bot.message_handler(commands=['leaderboard'])
# def leaderboard(message):
  # data = []
  # for user, score in score_dict.items():
  #   user_data = [score.getUserName, score.getAvg
  #   data.append()


@ bot.message_handler(commands=['clear'])
def clear(message):
  warning_text = "Are you sure you want to clear the leaderboard database?\n\n⚠ *WARNING:*\n pressing 'Yes' will cause you to *permanently* lose your data\!"
  markup = types.InlineKeyboardMarkup(row_width=2)
  markup.add(types.InlineKeyboardButton(text='Yes', callback_data='yes'),
             types.InlineKeyboardButton(text='No', callback_data='no'))
  bot.send_message(message.chat.id,
                   warning_text,
                   reply_markup=markup,
                   parse_mode="MarkdownV2")

@ bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
  if call.data == 'yes':
    score_dict.clear()
    bot.send_message(call.message.chat.id, "Cleared leaderboard database.")
    bot.answer_callback_query(callback_query_id=call.id)
  else:
    bot.send_message(call.message.chat.id, "Clear aborted.")
    bot.answer_callback_query(callback_query_id=call.id)
  bot.edit_message_reply_markup(inline_message_id=call.inline_message_id,
                                message_id=call.message.message_id,
                                chat_id=call.message.chat.id,
                                reply_markup=types.InlineKeyboardMarkup())





bot.polling()
