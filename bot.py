import telebot
import os
from telebot import types
from decouple import config
from flask import Flask, request
from bot.global_db_handler import GlobalDB
from utils.messages import START_TEXT, HELP_TEXT

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
    telebot.types.BotCommand("/help", "show help message"),
])

server = Flask(__name__)

score_db = GlobalDB.load()

# --------------------------------------------------------------USER FUNCTIONS


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
    try:
        command, input, *_ = message.text.split(None, 1)
        msg = score_db.update_data(
            message.chat.id, message.from_user.id, input, command[1:])
        bot.reply_to(message, msg, parse_mode="MarkdownV2")
    except ValueError:
        command, *_ = message.text.split()
        bot.reply_to(message, f"Expected a value after {command}!")


@ bot.message_handler(commands=['adjust'])
def cumulative_set(message):
    """ Allow user to cumulatively adjust data """
    try:
        command, old_avg, old_num_games, *_ = message.text.split(None, 2)
        msg = score_db.update_data(
            message.chat.id, message.from_user.id, old_num_games, command[1:], old_avg)
        bot.reply_to(message, msg, parse_mode="MarkdownV2")
    except ValueError:
        bot.reply_to(
            message, f"Expected two values after /adjust! e.g. /adjust 4.5 20. See /help for example explanation.")

# --------------------------------------------------------------DEBUG FUNCTIONS


@ bot.message_handler(commands=['adduser'])
def manual_score(message):
    """ Allow admin to add test user so as to test bot in Telegram """
    id = message.from_user.id
    _, user_id, user_name, message_text = message.text.split(None, 3)
    if id == ADMIN_ID and user_id != 0:
        score_db.add_score(message, bot, True, int(
            user_id), user_name, message_text)


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


@server.route(f'/{API_KEY}', methods=['POST'])
def get_updates():
    # retrieve the message in JSON and then transform it to Telegram object
    bot.process_new_updates(
        [telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200

@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f'https://wordle-scoreboard-bot-yyc.herokuapp.com/{API_KEY}')
    return "!", 200
    
if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 8455)))