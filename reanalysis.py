"""
ChessReanalysis v0.1
"""

import glob
import chess.pgn
import os

working_set = []

def addpgn(filename):
    with open(filename) as fin:
        n = 0
        while True:
            game = chess.pgn.read_game(fin)
            if not game:
                break
            working_set.append(game)
            n += 1
        print(f'Added {n} games to the working set')

def addpgnloop():
    while True:
        files = glob.glob(f'.{os.sep}pgn{os.sep}*.pgn')
        print('')
        for i, f in enumerate(files, 1):
            print(f'({i}) {f}')
        print('(0) Cancel')

        i = input()

        if i == '0':
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
            preprocess.run(working_set)
        if i == '4':
            analyze.a1(working_set)
        if i == '5':
            quit()

if __name__ == "__main__":
    mainloop()
