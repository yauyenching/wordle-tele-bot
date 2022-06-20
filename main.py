import telebot
from telebot import types
import env
import re
from tabulate import tabulate
import pandas as pd

API_KEY = env.API_KEY
# print(API_KEY) # ensure that API_KEY is correctly stored
bot = telebot.TeleBot(API_KEY)

# Dictionary with Telegram user id as key and class as value
score_dict = dict()

USER_STATS = ("*Name*: {} \n"
              "*\# of Games*: {} \n"
              "*Current Streak*: {} \n"
              "*Average Score*: {}/6")

ADDED_TEXT = ("New Wordle champion *{}* added to the leaderboard with the stats:"
              "\n\n"
              + USER_STATS.format({}, 1, 1, {}) +
              "\n\n"
              "To manually update any of these values, use /name, /games, /streak, and /average\.")

class WordleScore:
  def __init__(self, user_name, edition, tries):
    """Class storing a Wordle Score.
    
    Parameters
    ----------
    user_name: str
      Telegram user first name
    score_avg: int
      Total average score
    scores: dict
      Pandas dataframe with Wordle edition as key and # of tries as value
    num_games: int
      Total number of games played
    last_game: int
      Last Wordle edition played
    current_streak: int
      Current running Wordle streak
    """
    self.user_name      = user_name
    self.score_avg      = tries    # updated with score message
    self.num_games      = 1        # updated with score message
    self.last_game      = edition  # updated with score message
    self.current_streak = 1        # updated with score message
    
    # Define dictionary containing Wordle data
    data = {'Edition': [edition],
            'Tries': [tries]}
    self.scores = pd.DataFrame(data)
    
  def setCurrentStreak(self, last_game, current_streak):
    self.last_game = self.last_game
    self.current_streak = current_streak
    
  def setScoreAvg(self, score_avg, num_games):
    self.score_avg = score_avg
    self.num_games = num_games
    
  def setNumGames(self, num_games):
    self.num_games = num_games
    
  def setUserName(self, user_name):
    self.user_name = user_name
    
  def getUserName(self):
    return self.user_name
  
  def getAvgScore(self):
    return self.score_avg
  
  def getNumGames(self):
    return self.getNumGames
  
  def getCurrentStreak(self):
    return self.current_streak
  
  def updateScore(self, edition, tries):
    self.num_games += 1
    self.score_avg = (self.score_avg + tries)/self.num_games
    if self.last_game == edition + 1:
      self.current_streak += 1
    else:
      self.current_streak = 0
    self.last_game = edition
    self.scores = self.scores.append({'Edition': edition, 'Tries': tries})
    
  def printStats(self):
    USER_STATS.format(self.user_name)

@bot.message_handler(commands=['greet'])
def greet(message):
  bot.send_message(message.chat.id, "Hey! How's it going?")
  
@bot.message_handler(regexp='Wordle\s(?P<edition>\d+)\s(?P<tries>[0-6X])/6\n{2}(?:(?:[🟨🟩⬛️]+)(?:\r?\n)){1,6}')
def add_score(message):
  m = re.match(r"Wordle\s(?P<edition>\d+)\s(?P<tries>[0-6X])/6\n{2}(?:(?:[🟨🟩⬛️]+)(?:\r?\n)){1,6}", message.text)
  user_id = message.from_user.id
  user_name = message.from_user.first_name
  user_score = score_dict.get(user_id)
  edition = int(m.group('edition'))
  tries = int(m.group('tries'))
  if user_score == None:
    score_dict[user_id] = WordleScore(user_name, edition, tries)
    bot.send_message(message.chat.id, ADDED_TEXT.format(user_name, user_name, tries), parse_mode="MarkdownV2")
  else:
    user_score.updateScore(edition, tries)
  
@bot.message_handler(commands=['clear'])
def clear(message):
  warning_text = "Are you sure you want to clear the leaderboard database?\n\n⚠ *WARNING:*\n pressing 'Yes' will cause you to *permanently* lose your data\!"
  markup = types.InlineKeyboardMarkup(row_width=2)
  markup.add(types.InlineKeyboardButton(text='Yes', callback_data='yes'), types.InlineKeyboardButton(text='No', callback_data='no'))
  bot.send_message(message.chat.id, 
                   warning_text,
                   reply_markup=markup,
                   parse_mode="MarkdownV2")
  
@bot.callback_query_handler(func=lambda call: True)
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