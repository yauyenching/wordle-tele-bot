USER_STATS = (
              "`Name: {}\n"
              "\# of Games : {}\n"
              "Streak: {}\n"
              "Avg. Score: {:.3f}/6`"
              )

ADDED_TEXT = (
              "New Wordle champion *{}* added to the leaderboard with the stats:"
              "\n\n"
              + USER_STATS.format({}, 1, 1, {}) +
              "\n\n"
              "To manually update any of these values, use /name, /games, /streak, and /average\."
              )