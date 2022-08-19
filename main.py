import telebot, os
from telebot import types
from decouple import config
from tabulate import tabulate
import pandas as pd
from types import SimpleNamespace
from flask import Flask, request
from utils.score_handler import add_score
from utils.db_handler import save

API_KEY = config('API_KEY')
ADMIN_ID = int(config('ADMIN_ID'))
bot = telebot.TeleBot(API_KEY)
server = Flask(__name__)

# class GlobalDB:
#   def __init__(self):
#     """Class storing global data for all chats.

#     Parameters
#     ----------
#     username: str
#       Telegram user first name
#     num_games: int
#       Total number of games played
#     streak: int
#       Current running Wordle streak
#     score_avg: float
#       Total average score
#     last_game: int
#       Last Wordle edition played
#     """
#     self._chat_data = {} # Dictionary with Telegram chat id as key with namespace as value
    
#   #--------------------------------------------------GETTERS
#   def latest_game(self, chat_id):
#     score_dict[chat_id]['latest_game']
    
score_dict = {}

@bot.message_handler(commands=['greet'])
def greet(message):
  test, test1, test2, *_ = message.text.split()
  # bot.send_message(message.chat.id, "Hey! How's it going?" + test + test1 + test2)
  if test == "/greet":
    bot.send_message(message.chat.id, "hi")
  else:
    bot.send_message(message.chat.id, "bye")

#--------------------------------------------------------------USER FUNCTIONS
# Update user's data when message matches Wordle Score share regex pattern
@bot.message_handler(regexp='^Wordle\s(?P<edition>\d+)\s(?P<tries>[0-6X])/6\n{2}(?:(?:[🟨🟩⬛️⬜️]+)(?:\r?\n)){1,6}')
def auto_score(message):
  # print("match")
  add_score(message, message.from_user.id, message.from_user.first_name, message.text, score_dict, bot)

# Print user's stats upon command
@bot.message_handler(commands=['stats'])
def stats(message):
  user_id = message.from_user.id
  message_scores = score_dict.get(message.chat.id)
  if message_scores != None:
    user_score = score_dict[message.chat.id].get(user_id)
  else:
    user_score = None
  if user_score == None:
    bot.send_message(message.chat.id, "No data recorded for you yet! Share Wordle results to add yourself to the database.")
  else:
    user_score.print_stats(message.chat.id, score_dict, bot)

# Print user leaderboard upon command
@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
  message_scores = score_dict.get(message.chat.id)
  def no_data():
    bot.send_message(message.chat.id, "No data recorded for anyone yet! Start sharing your Wordle results to this chat to enter yourself into the database.")
  if message_scores == None:
    return no_data()
  leaderboard = []
  for key, user_data in score_dict[message.chat.id].items():
    if key != 'latest_game':
      user_data.update_streak(message.chat.id, score_dict)
      data = [user_data.username, user_data.num_games, user_data.streak, "{:.3f}".format(user_data.score_avg).replace(".", "\.")]
      leaderboard.append(data)
  if not leaderboard:
    return no_data()
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
    _ = score_dict.pop(call.message.chat.id)
    save(score_dict)
    bot.send_message(call.message.chat.id, "Cleared leaderboard database.")
    bot.answer_callback_query(callback_query_id=call.id)
  else:
    bot.send_message(call.message.chat.id, "Clear aborted.")
    bot.answer_callback_query(callback_query_id=call.id)
  bot.edit_message_reply_markup(inline_message_id=call.inline_message_id,
                                message_id=call.message.message_id,
                                chat_id=call.message.chat.id,
                                reply_markup=types.InlineKeyboardMarkup())
  
# Manually update data
@ bot.message_handler(commands=['name', 'games', 'streak', 'average'])
def manual_set(message):
  command, input, *_ = message.text.split()
  user_id = message.from_user.id  
  if command == '/name':
    score_dict[message.chat.id][user_id].username = input
  elif command == '/games':
    score_dict[message.chat.id][user_id].num_games = input
  elif command == '/streak':
    score_dict[message.chat.id][user_id].streak = input
  else:
    score_dict[message.chat.id][user_id].score_avg = input

#--------------------------------------------------------------DEBUG FUNCTIONS
# Add user manually
@ bot.message_handler(commands=['adduser'])
def manual_score(message):
  id = message.from_user.id
  # print(" ".join(map(str, [ADMIN_ID, id, id == ADMIN_ID])))
  if id == ADMIN_ID:
    _, user_id, user_name, message_text = message.text.split(None, 3)
    add_score(message, user_id, user_name, message_text, score_dict, bot)

bot.infinity_polling()
