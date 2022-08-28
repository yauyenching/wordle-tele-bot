import re

def extract_score(message: str) -> tuple[int, float]:
    """ Use regex to extract Wordle edition and tries """
    m = re.match(
         r"Wordle\s(?P<edition>\d+)\s(?P<tries>[0-6X])/6\n{2}(?:(?:[🟨🟩⬛️⬜️]+)(?:\r?\n)){1,6}", message)
    edition = int(m.group('edition'))
    tries = m.group('tries')
    if tries == "X":
        tries = 7.0
    else:
        tries = float(tries)
        
    return (edition, tries)

def extract_command(command:str):
    """ Use regex to extract command """
    cmd = re.search('\/(.*?)@*\w*', command)
    return cmd.group(0)[1:]