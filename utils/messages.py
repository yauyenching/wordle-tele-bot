START_TEXT = ("Welcome to the Wordle Leaderboard Bot! This bot was made to automatically keep track of your "
              "running score average for Wordle to compare between family and friends.\n"
              "\n"
              "To use me, simply share your Wordle results to start tracking your averages. "
              "Add me to a group chat to compare scores for a group. Don't worry, your stats "
              "are synchronized across different chats!\n"
              "\n"
              "Use /help to see the list of available commands.")

HELP_TEXT = ("I keep track of your Wordle stats by automatically calculating your score average, "
             "your streak, and the total number of games you have played based off your Wordle resuls\.\n"
             "\n"
             "You can control me by using these commands:\n"
             "\n"
             "*Show and compare*\n"
             "/stats \- show your aggregated stats\n"
             "/leaderboard \- show a chat leaderboard sorted by lowest average\n"
             "\n"
             "*Change your data*\n"
             "/clear \- clear your user data\n"
             "/name \- change your display name\n"
             "/games \- change your total number of games played\n"
             "/streak \- change your current running streak\n"
             "/average \- change your score average\n"
             "/adjust \- calculate your score average using your old score average\n"
             "\n"
             "*Settings*\n"
             "/toggleretroactive \- control whether sharing older Wordle results can update your results \(toggled OFF by default\)\n"
             "\n"
             "Examples for changing your data:\n"
             "\- /average 4\.5 \(to change your average to 4\.5\)\n"
             "\- /adjust 4\.5 20 \(to calculate your new score average using your old average of 4\.5 that was calculated over 20 games\)\n"
             "\n"
             "Created with love by @yyenching")

NO_DATA_MSG = "No data recorded yet! Share your Wordle results to add yourself to the database."

INVALID_AVG = "Wordle score average cannot be above a value of 7.0!"

def user_stats(username: str, num_games: int, streak: int, score_avg: float) -> str:
    return (
        f"`Name: {username}\n"
        f"\# of Games : {num_games}\n"
        f"Streak: {streak}\n"
        f"Avg. Score: {score_avg:.3f}/6`"
    ).replace(".", "\.")


def added_text(username: str, init_score: float) -> str:
    return (
        f"New Wordle champion *{username}* added to the leaderboard with the stats:"
        "\n\n"
        + user_stats(username, 1, 1, init_score) +
        "\n\n"
        "To manually update any of these values, use /name, /games, /streak, and /average\."
    )
