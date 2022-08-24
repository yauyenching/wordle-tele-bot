from ast import Global
import telebot
import os
import json
from telebot import types
from decouple import config
from flask import Flask, request
from bot.global_db_handler import GlobalDB

API_KEY = config('API_KEY')
ADMIN_ID = int(config('ADMIN_ID'))
bot = telebot.TeleBot(API_KEY)
server = Flask(__name__)

score_db = GlobalDB.load()
# score_db.pprint()

# --------------------------------------------------------------USER FUNCTIONS


@bot.message_handler(commands=['greet'])
def test(message):
    bot.send_message(message.chat.id, f"hello @{message.from_user.username}")


@bot.message_handler(regexp='^Wordle\s(?P<edition>\d+)\s(?P<tries>[0-6X])/6\n{2}(?:(?:[🟨🟩⬛️⬜️]+)(?:\r?\n)){1,6}')
def add_score(message):
    """ Update user's data when message matches Wordle Score share regex pattern """
    score_db.add_score(
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        message=message.text,
        username=message.from_user.first_name,
        tele_name=message.from_user.username,
        bot=bot)


@bot.message_handler(commands=['stats', 'leaderboard'])
def print_scores(message):
    """ Print user's stats or chat's leaderboard upon command """
    command = message.text
    if command == '/stats':
        bot.send_message(message.chat.id, score_db.print_scores(
            message.chat.id, message.from_user.id), parse_mode="MarkdownV2")
    else:
        bot.send_message(message.chat.id, score_db.print_scores(
            message.chat.id), parse_mode="MarkdownV2")


@ bot.message_handler(commands=['clear'])
def clear(message):
    """ Clear database upon command """
    warning_text = f"Are you sure you want to delete your data, @{message.from_user.username}?\n\n⚠ *WARNING:*\n This will cause you to *permanently* lose your data\!"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(
        text='Yes', callback_data=message.from_user.id),
        types.InlineKeyboardButton(text='Cancel', callback_data='no'))
    bot.send_message(message.chat.id,
                     warning_text,
                     reply_markup=markup,
                     parse_mode="MarkdownV2")


@ bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == 'no':
        bot.send_message(call.message.chat.id, "Clear aborted.")
    else:
        user_id = int(call.data)
        bot.send_message(call.message.chat.id, score_db.clear_data(user_id))

    bot.answer_callback_query(callback_query_id=call.id)
    bot.edit_message_reply_markup(inline_message_id=call.inline_message_id,
                                  message_id=call.message.message_id,
                                  chat_id=call.message.chat.id,
                                  reply_markup=types.InlineKeyboardMarkup())


@ bot.message_handler(commands=['name', 'games', 'streak', 'average'])
def manual_set(message):
    """ Allow user to manually set data """
    command, input, *_ = message.text.split()
    msg = score_db.update_data(
        message.chat.id, message.from_user.id, message.from_user.username, input, command[1:])
    bot.send_message(message.chat.id, msg, parse_mode="MarkdownV2")


@ bot.message_handler(commands=['adjust'])
def cumulative_set(message):
    """ Allow user to cumulatively adjust data """
    command, old_num_games, old_avg, *_ = message.text.split()
    msg = score_db.update_data(
        message.chat.id, message.from_user.id, message.from_user.username, old_num_games, command[1:], old_avg)
    bot.send_message(message.chat.id, msg, parse_mode="MarkdownV2")

# --------------------------------------------------------------DEBUG FUNCTIONS


@ bot.message_handler(commands=['adduser'])
def manual_score(message):
    """ Allow admin to add test user so as to test bot in Telegram """
    id = message.from_user.id
    _, user_id, user_name, message_text = message.text.split(None, 3)
    if id == ADMIN_ID and user_id != 0:
        score_db.add_score(message.chat.id, int(user_id),
                           message_text, user_name, user_name, bot)


@ bot.message_handler(commands=['restart'])
def restart(message):
    """ Allow admin to restart score_db """
    id = message.from_user.id
    if id == ADMIN_ID:
        score_db.restart()
        
        
@ bot.message_handler(commands=['admingame'])
def restart(message):
    """ Allow admin to manually set latest game """
    id = message.from_user.id
    _, latest_game, *_ = message.text.split()
    if id == ADMIN_ID:
        score_db.set_latest_game(int(latest_game))


bot.infinity_polling()
