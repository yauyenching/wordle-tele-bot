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
        "To manually update any of these values, use /µname, /games, /streak, and /average\."
    )
