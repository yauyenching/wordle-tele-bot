import telebot
from telebot import types
from decouple import config
import re
from tabulate import tabulate
import pandas as pd

API_KEY = config('API_KEY')
bot = telebot.TeleBot(API_KEY)

# Dictionary with Telegram chat id as key then user id as key and class as value
score_dict = dict()

USER_STATS = (
              "`Name: {}\n"
              "\# of Games : {}\n"
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
    if edition > score_dict[chat_id]['latest_game']:
      score_dict[chat_id]['latest_game'] = edition
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
    self.score_avg = (self.score_avg * (self.num_games - 1) +
                      tries)/self.num_games
    
  def update_streak(self, chat_id):
    if self.last_game < score_dict[chat_id]['latest_game']:
      self.streak = 0

  def print_stats(self, chat_id):
    self.update_streak(chat_id)
    score_avg = "{:.2f}".format(self.score_avg).replace(".", "\.")
    if self.streak > 1:
      streak_status = " 🔥"
    else:
      streak_status = ""
    streak = str(self.streak) + streak_status
    message = "Stats for *{}*:\n\n".format(self.username) + USER_STATS.format(self.username, self.num_games, streak, score_avg)
    bot.send_message(chat_id, message, parse_mode="MarkdownV2")


@bot.message_handler(commands=['greet'])
def greet(message):
  _, test1, test2, *_ = message.text.split()
  bot.send_message(message.chat.id, "Hey! How's it going?" + test1 + test2)

#--------------------------------------------------------------AUX FUNCTIONS
# Update data based on Wordle Score result
def add_score(message, user_id, user_name, text):
  m = re.match(
      r"Wordle\s(?P<edition>\d+)\s(?P<tries>[0-6X])/6\n{2}(?:(?:[🟨🟩⬛️]+)(?:\r?\n)){1,6}", text)
  user_score = score_dict[message.chat.id].get(user_id)
  edition = int(m.group('edition'))
  tries = m.group('tries')
  if tries == "X":
    tries = 7.0
  else:
    tries = float(tries)
  if user_score == None:
    score_dict[message.chat.id][user_id] = WordleScore(user_name, edition, tries)
    bot.send_message(message.chat.id, ADDED_TEXT.format(
        user_name, user_name, "{:.2f}".format(tries).replace(".", "\.")), parse_mode="MarkdownV2")
  else:
    user_score.update_score(message.chat.id, edition, tries)

#--------------------------------------------------------------USER FUNCTIONS
@bot.message_handler(commands=['start'])
def start(message):
  score_dict[message.chat.id] = {}
  score_dict[message.chat.id]['latest_game'] = 0

# Update user's data when message matches Wordle Score share regex pattern
@bot.message_handler(regexp='^Wordle\s(?P<edition>\d+)\s(?P<tries>[0-6X])/6\n{2}(?:(?:[🟨🟩⬛️]+)(?:\r?\n)){1,6}')
def auto_score(message):
  # bot.send_message(message.chat.id, "match")
  add_score(message, message.from_user.id, message.from_user.first_name, message.text)

# Print user's stats upon command
@bot.message_handler(commands=['stats'])
def stats(message):
  user_id = message.from_user.id
  user_score = score_dict[message.chat.id].get(user_id)
  if user_score == None:
    bot.send_message(message.chat.id, "No data recorded for you yet! Share Wordle results to add yourself to the database.")
  else:
    user_score.print_stats(message.chat.id)

# Print user leaderboard upon command
@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
  leaderboard = []
  for key, user_data in score_dict[message.chat.id].items():
    if key != 'latest_game':
      user_data.update_streak(message.chat.id)
      data = [user_data.username, user_data.num_games, user_data.streak, "{:.3f}".format(user_data.score_avg).replace(".", "\.")]
      leaderboard.append(data)
  if not leaderboard:
    bot.send_message(message.chat.id, "No data recorded for anyone yet! Start sharing your Wordle results to this chat to enter yourself into the database.")
  else:
    leaderboard_df = pd.DataFrame(leaderboard, columns=['Name', 'Gms', '🔥', 'Avg.'])
    leaderboard_df = leaderboard_df.sort_values(by=['Avg.']).reset_index(drop=True)
    leaderboard_df.index += 1                                            
    bot.send_message(message.chat.id, "`{}`".format(tabulate(leaderboard_df, headers='keys')), parse_mode="MarkdownV2")

# Clear database upon command
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
    score_dict[message.chat.id].clear()
    bot.send_message(call.message.chat.id, "Cleared leaderboard database.")
    bot.answer_callback_query(callback_query_id=call.id)
  else:
    bot.send_message(call.message.chat.id, "Clear aborted.")
    bot.answer_callback_query(callback_query_id=call.id)
  bot.edit_message_reply_markup(inline_message_id=call.inline_message_id,
                                message_id=call.message.message_id,
                                chat_id=call.message.chat.id,
                                reply_markup=types.InlineKeyboardMarkup())

#--------------------------------------------------------------DEBUG FUNCTIONS
# Add user manually
@ bot.message_handler(commands=['adduser'])
def manual_score(message):
  _, user_id, user_name, message_text = message.text.split(None, 3)
  add_score(message, user_id, user_name, message_text)


bot.infinity_polling()
