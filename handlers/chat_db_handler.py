from handlers.score_handler import WordleStats
import pandas as pd
from tabulate import tabulate


class ChatDB:
    def __init__(self, latest_game: int, init_stats: WordleStats, user_id: int) -> None:
        self._latest_game: int = latest_game
        self.chat_data: dict[int, WordleStats] = {user_id: init_stats}

    # --------------------------------------------------GETTERS
    @property
    def latest_game(self) -> int:
        return self._latest_game

    # --------------------------------------------------SETTERS
    @latest_game.setter
    def latest_game(self, edition: int) -> None:
        if edition > self.latest_game:  # set latest_game var for chat if Wordle edition of submitted data is greater
            self._latest_game = edition

    # --------------------------------------------------METHODS
    def get_user_data(self, user_id: int) -> WordleStats | None:
        return self.chat_data.get(user_id)

    def clear(self, user_id: int) -> None:
        _ = self.chat_data.pop(user_id)
        return None

    def update_user_data(self, user_id: int, username: str, edition: int, tries: float) -> bool | str | None:
        self.latest_game = edition
        user_data = self.get_user_data(user_id)

        if user_data == None:  # no data recorded for user yet
            # initialize player stats data using Wordle results
            self.chat_data[user_id] = WordleStats(username, edition, tries)
            return True
        else:  # user exists, so update data
            return user_data.update_stats(edition, tries)
            # if isinstance(res, str): # today's Wordle already recorded
            # return res

    def print_leaderboard(self) -> tuple[str, bool]:

        fields = ['username', 'num_games', 'streak', 'score_avg']
        streak_updated = list(map(lambda x: x.update_streak(self.latest_game), self.chat_data.values()))
        leaderboard_df = pd.DataFrame(
            [{fn: getattr(user_data, fn) for fn in fields}
             for user_data in self.chat_data.values()]
        )
        leaderboard_df.columns = ['Name', 'Gms', '🔥', 'Avg.']
        print(streak_updated)

        leaderboard_df = leaderboard_df.sort_values(
            by=['Avg.']).reset_index(drop=True)
        leaderboard_df.index += 1
        return (f"`{tabulate(leaderboard_df, headers='keys')}`", any(streak_updated))
