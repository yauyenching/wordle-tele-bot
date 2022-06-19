import telebot
import env
import re

API_KEY = env.API_KEY
# print(API_KEY) # ensure that API_KEY is correctly stored
bot = telebot.TeleBot(API_KEY)

# Dictionary with Telegram user id as key and class as value
score_dict = dict()

class WordleScore:
  def __init__(self, user_name, score_avg, scores, num_games, last_game, current_streak):
    """Class storing a Wordle Score.
    
    Parameters
    ----------
    user_name: str
      Telegram user first name
    score_avg: int
      Total average score
    scores: dict
      Dictionary with Wordle edition as key and # of tries as value
    num_games: int
      Total number of games tracked with bot
    last_game: int
      Last Wordle edition played
    current_streak: int
      Current running Wordle streak
    """
    self.user_name      = user_name
    self.score_avg      = score_avg      # updated with score message
    self.scores         = scores         # updated with score message
    self.num_games      = num_games      # updated with score message
    self.last_game      = last_game      # updated with score message
    self.current_streak = current_streak # updated with score message
    
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
    if self.last_game == self.edition + 1:
      self.current_streak += 1
    else:
      self.current_streak = 0
    self.last_game = edition
    self.scores[edition] = tries

@bot.message_handler(commands=['greet'])
def greet(message):
  bot.send_message(message.chat.id, "Hey! How's it going?")
  
@bot.message_handler(regexp='Wordle\s(?P<edition>\d+)\s(?P<tries>[0-6X])/6\n{2}(?:(?:[🟨🟩⬛️]+)(?:\r?\n)){1,6}')
def add_score(message):
  m = re.match(r"Wordle\s(?P<edition>\d+)\s(?P<tries>[0-6X])/6\n{2}(?:(?:[🟨🟩⬛️]+)(?:\r?\n)){1,6}", message.text)
  # bot.reply_to(message, "For Wordle {}, {} got a score of {} out of 6.".format(m.group('game_id'), message.from_user.first_name, m.group('tries')))
  user_score = score_dict[message.from_user.id]
  user_score.updateScore(m.group('edition'), m.group('tries'))
  


bot.polling()