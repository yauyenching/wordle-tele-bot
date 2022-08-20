import json, re
from telebot import TeleBot
from bot.messages import ADDED_TEXT
from types import SimpleNamespace
from score_handler import WordleStats

class GlobalDB:
  def __init__(self):
    """Class storing global data for all chats.

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
    self._chat_data: dict[int, ] = {} # Dictionary with Telegram chat id as key with namespace as value
    
  #--------------------------------------------------GETTERS
  @property
  def latest_game(self, chat_id):
    return self._chat_data[chat_id].latest_game
  
  @property
  def user_data(self, chat_id, user_id):
    return self._chat_data[chat_id].user_data.get(user_id)

#--------------------------------------------------------------AUX FUNCTIONS  
# Update data based on Wordle Score result
def add_score(message, user_id, user_name, text, score_dict, bot):
  m = re.match(
      r"Wordle\s(?P<edition>\d+)\s(?P<tries>[0-6X])/6\n{2}(?:(?:[🟨🟩⬛️⬜️]+)(?:\r?\n)){1,6}", text)
  if score_dict.get(message.chat.id) == None:
    score_dict[message.chat.id] = {}
  user_score = score_dict[message.chat.id].get(user_id)
  edition = int(m.group('edition'))
  tries = m.group('tries')
  if tries == "X":
    tries = 7.0
  else:
    tries = float(tries)
  if user_score == None:
    score_dict[message.chat.id][user_id] = WordleStats(user_name, edition, tries)
    score_dict[message.chat.id]['latest_game'] = edition
    save(score_dict)
    bot.send_message(message.chat.id, ADDED_TEXT.format(
        user_name, user_name, "{:.3f}".format(tries).replace(".", "\.")), parse_mode="MarkdownV2")
  else:
    user_score.update_score(message.chat.id, edition, tries, score_dict, bot)
     
# Save score in local .json file for persistence data storage
def save(dict: dict, filename: str = "database.json") -> None:
  # print(os.getcwd())
  f = open(filename, "w+", encoding="utf-8")
  f.write(json.dumps(dict, indent = 4, ensure_ascii=True, default=lambda x: x.__dict__))
  f.close()
  
def load(filename: str = "database.json") -> dict:
  # if os.path.exists(filename):
  f = open(filename)
  db = json.loads(f.read())
# def start(dict: dict, filename: str = "database.json") -> None: