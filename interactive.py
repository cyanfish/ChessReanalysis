"""
ChessReanalysis v0.1
"""

import glob, os, re
import chess.pgn
import preprocess, analyze

working_set = {}

game_link_regex = re.compile(r'^(https?://)?([a-z]+\.)?lichess\.org/([A-Za-z0-9]{8})([A-Za-z0-9]{4})?([/#\?].*)?$')

def gameid(game):
    gamelink = game.headers['Site']
    if gamelink is None or gamelink == '':
        return None
    match = game_link_regex.match(gamelink)
    if match is None:
        return None
    return match.group(3)

def addpgn(filename):
    with open(filename) as fin:
        n = 0
        while True:
            game = chess.pgn.read_game(fin)
            if not game:
                break
            gid = gameid(game)
            if gid:
                working_set[gid] = game
            n += 1
        print(f'Added {n} games to working set from {filename}')

def addpgnloop():
    while True:
        files = glob.glob(f'.{os.sep}pgn{os.sep}*.pgn')
        print('')
        for i, f in enumerate(files, 1):
            print(f'({i}) {f}')
        print('(^) Enter a regex to match multiple files by name')
        print('(0) Cancel')

        i = input()

        if i == '0':
            return
        if i.startswith('^'):
            regex = re.compile(i)
            for f in files:
                if regex.match(f.split(os.sep)[-1]):
                    addpgn(f)
            return
        try:
            f = files[int(i) - 1]
            addpgn(f)
            return
        except (IndexError, ValueError):
            pass

def mainloop():
    while True:
        print('')
        print(f'{len(working_set)} games in working set')
        print('(1) Add PGN to working set')
        print('(2) Clear working set')
        print('(3) Pre-process')
        print('(4) Analysis 1')
        print('(5) Exit')

        i = input()

        if i == '1':
            addpgnloop()
        if i == '2':
            working_set.clear()
        if i == '3':
            try:
                preprocess.run(working_set)
            except KeyboardInterrupt:
                pass
        if i == '4':
            analyze.a1(working_set)
        if i == '5':
            quit()

if __name__ == "__main__":
    mainloop()
