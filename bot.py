import telebot
import os
from telebot import types
from decouple import config
from flask import Flask, request
from classes.WordleStats import WordleStats
from utils.load_mongo_db import get_database
from handlers.global_db_handler import GlobalDB
from utils.messages import START_TEXT, HELP_TEXT, NO_DATA_MSG, INVALID_AVG
from utils.message_handler import extract_command

API_KEY = config('API_KEY')
ADMIN_ID = int(config('ADMIN_ID'))
bot = telebot.TeleBot(API_KEY)
bot.set_my_commands([
    telebot.types.BotCommand("/stats", "show your stats"),
    telebot.types.BotCommand("/leaderboard", "show chat leaderboard"),
    telebot.types.BotCommand("/clear", "clear your data"),
    telebot.types.BotCommand("/name", "change display name"),
    telebot.types.BotCommand("/games", "change total games"),
    telebot.types.BotCommand("/streak", "change running streak"),
    telebot.types.BotCommand("/average", "change score average"),
    telebot.types.BotCommand(
        "/adjust", "calculate score average with old data"),
    telebot.types.BotCommand(
        "/toggleretroactive", "toggle retroactive stats updates for older games"),
    telebot.types.BotCommand("/help", "show help message"),
])

server = Flask(__name__)

score_db = GlobalDB(get_database())

# --------------------------------------------------------------USER FUNCTIONS


@bot.message_handler(commands=['greet'])
def greet(message):
    bot.send_message(message.chat.id, "sup hello")


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, START_TEXT)


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(message.chat.id, HELP_TEXT, parse_mode="MarkdownV2")


@bot.message_handler(regexp='^Wordle\s(?P<edition>\d+)\s(?P<tries>[0-6X])/6\n{2}(?:(?:[🟨🟩⬛️⬜️]+)(?:\r?\n)){1,6}')
def add_score(message):
    """ Update user's data when message matches Wordle Score share regex pattern """
    score_db.add_score(message=message, bot=bot)


@bot.message_handler(commands=['stats', 'leaderboard'])
def print_scores(message):
    """ Print user's stats or chat's leaderboard upon command """
    try:
        command = message.text
        command = extract_command(command)
        err_msg = "your stats" if command == 'stats' else "the chat's leaderboard"

        res = score_db.print_scores(
            chat_id=message.chat.id, user_id=message.from_user.id, cmd=command)
        bot.send_message(message.chat.id, res, parse_mode="MarkdownV2")
    except WordleStats.UserNotFound:
        no_update_msg = NO_DATA_MSG + \
            f" After being added, you will then be able to print {err_msg}."
        bot.reply_to(message, no_update_msg)


@ bot.message_handler(commands=['clear'])
def clear(message):
    """ Clear database upon command """
    warning_text = f"Are you sure you want to delete your data?\n\n⚠ *WARNING:*\n This will cause you to *permanently* lose your data\!"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(
        text='Yes', callback_data=message.from_user.id),
        types.InlineKeyboardButton(text='Cancel', callback_data='no'))
    bot.reply_to(message,
                 warning_text,
                 reply_markup=markup,
                 parse_mode="MarkdownV2")


@ bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    remove_markup = bot.edit_message_reply_markup(inline_message_id=call.inline_message_id,
                                                  message_id=call.message.message_id,
                                                  chat_id=call.message.chat.id,
                                                  reply_markup=types.InlineKeyboardMarkup())
    try:
        if call.data == 'no':
            bot.send_message(call.message.chat.id, "Clear aborted.")
            remove_markup
        else:
            # print(call.from_user.id)
            user_id = int(call.data)
            # print(user_id)
            if user_id == call.from_user.id:
                score_db.clear_data(user_id)
                bot.send_message(call.message.chat.id,
                                 "Cleared user database.")
                remove_markup
    except WordleStats.UserNotFound:
        username = call.from_user.username
        name = call.from_user.first_name if username == None else "@" + username
        bot.send_message(
            call.message.chat.id,
            f"You have no data stored to clear, {name}! Share your Wordle results to add yourself to the database.")
        remove_markup
    finally:
        bot.answer_callback_query(callback_query_id=call.id)


@ bot.message_handler(commands=['name', 'games', 'streak', 'average'])
def manual_set(message):
    """ Allow user to manually set data """
    msg = message.text.split(None, 1)
    command = extract_command(msg[0])

    try:
        input = msg[1]
        score_db.update_data(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            input=input,
            command=command
        )
        msg = f"Successfully updated your {command} to *{input}*\!" if command != 'average' else f"Successfully updated your {command} to *{float(input):.3f}*\!"
        msg = msg.replace(".", "\.")
        bot.reply_to(message, msg, parse_mode="MarkdownV2")
    except WordleStats.InvalidAvg:
        bot.reply_to(message, INVALID_AVG)
    except WordleStats.UserNotFound:
        no_update_msg = NO_DATA_MSG + \
            " After being added, you will then be able to update your user data."
        bot.reply_to(message, no_update_msg)
    except (ValueError, IndexError):
        if command == 'streak' or command == 'games':
            value_type = "whole number "
        elif command == 'average':
            value_type = "numerical "
        else:
            value_type = ""
        bot.reply_to(
            message, f"Expected a single {value_type}value after /{command}!")


@ bot.message_handler(commands=['adjust'])
def cumulative_set(message):
    """ Allow user to cumulatively adjust data """
    try:
        command, old_avg, old_num_games, *_ = message.text.split(None, 2)
        command = extract_command(command)
        new_games, new_avg = score_db.update_data(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            input=old_num_games,
            command=command,
            input_avg=old_avg
        )
        msg = f"Successfully updated your games and average to *{new_games}* and *{new_avg:.3f}*\!".replace(
            ".", "\.")
        bot.reply_to(message, msg, parse_mode="MarkdownV2")
    except WordleStats.InvalidAvg:
        bot.reply_to(message, INVALID_AVG)
    except WordleStats.UserNotFound:
        no_update_msg = NO_DATA_MSG + \
            " After being added, you will then be able to update your user data."
        bot.reply_to(message, no_update_msg)
    except ValueError:
        bot.reply_to(
            message, f"Expected two numerical values after /adjust! e.g. /adjust 4.5 20. See /help for explanation of the example.")


@ bot.message_handler(commands=['toggleretroactive'])
def toggle_retroactive(message):
    toggle_state = score_db.toggle_retroactive(message.from_user.id)
    if toggle_state:
        msg = "You are now able to have Wordle results for older games update your stats \(except streak\)\."
    else:
        msg = "Sharing Wordle results for older games will not factor into your stats\."
    bot.reply_to(
        message, f"Retroactive updates for you is now set to *{toggle_state}*\. {msg}", parse_mode="MarkdownV2")
    
@ bot.message_handler(commands=['togglewarning'])
def toggle_retroactive(message):
    toggle_state = score_db.toggle_warning(message.from_user.id)
    if toggle_state:
        msg = "Warnings are turned *on*\. Sharing older games do not affect your stats, and you WILL receive a notification when you do so\."
    else:
        msg = "Warnings are now *muted*\. Sharing older games do not affect your stats, and you will NOT receive a notification when you do so\. Use /togglewarning to turn warnings back on\."
    bot.reply_to(
        message, msg, parse_mode="MarkdownV2")

# --------------------------------------------------------------DEBUG FUNCTIONS


@ bot.message_handler(commands=['adminuser'])
def manual_score(message):
    """ Allow admin to add test user so as to test bot in Telegram """
    id = message.from_user.id
    _, user_id, user_name, message_text = message.text.split(None, 3)
    if id == ADMIN_ID and user_id != 0:
        score_db.add_score(message, bot, True, int(
            user_id), user_name, message_text)


@ bot.message_handler(commands=['admingame'])
def restart(message):
    """ Allow admin to manually set latest game """
    id = message.from_user.id
    _, latest_game, *_ = message.text.split()
    if id == ADMIN_ID:
        score_db.set_latest_game(int(latest_game))
        bot.reply_to(
            message, "Successfuly updated global latest game variable!")


@ bot.message_handler(commands=['adminclear'])
def restart(message):
    """ Allow admin to clear debug users """
    id = message.from_user.id
    if id == ADMIN_ID:
        score_db.clear_debug(ADMIN_ID)
        bot.reply_to(
            message, "Successfuly cleared debug chat database!")


@ bot.message_handler(commands=['admincheck'])
def restart(message):
    """ Allow admin to clear debug users """
    id = message.from_user.id
    if id == ADMIN_ID:
        bot.reply_to(
            message, f"Latest game in the database is *{score_db.get_latest_game()}*\!", parse_mode="MarkdownV2")

@ bot.message_handler(commands=['adminlock'])
def test_lock(message):
    """ Test lock feature """
    id = message.from_user.id
    if id == ADMIN_ID:
        score_db.test_lock(id)
        bot.reply_to(
            message, "Successfuly retrieved user data with write=True!")
        
@ bot.message_handler(commands=['admintoggle'])
def toggle_lock(message):
    """ Test lock feature """
    id = message.from_user.id
    if id == ADMIN_ID:
        new_state = score_db.toggle_lock(id)
        bot.reply_to(
            message, f"Successfuly toggled lock to {new_state}!")
        
@ bot.message_handler(commands=['adminchecklock'])
def check_lock(message):
    """ Test lock feature """
    id = message.from_user.id
    if id == ADMIN_ID:
        state = score_db.check_lock(id)
        bot.reply_to(
            message, f"Lock is currently set to {state}!")

@server.route(f'/{API_KEY}', methods=['POST'])
def get_updates():
    # retrieve the message in JSON and then transform it to Telegram object
    bot.process_new_updates(
        [telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200

@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(
        url=f'https://wordle-scoreboard-bot-yyc.herokuapp.com/{API_KEY}')
    return "!", 200


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 8443)))
