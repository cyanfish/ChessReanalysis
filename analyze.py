from models import *
import chess, chess.pgn
import json
from collections import defaultdict

book_depth = 10
forced_move_thresh = 50
unclear_pos_thresh = 100
undecided_pos_thresh = 100
losing_pos_thresh = 500
exclude_forced = True
include_only_unclear = True

class PgnSpyResult():

    def __init__(self):
        self.sample_size = 0
        self.sample_total_cpl = 0
        self.gt0 = 0
        self.gt10 = 0
        self.t1_total = 0
        self.t1_count = 0
        self.t2_total = 0
        self.t2_count = 0
        self.t3_total = 0
        self.t3_count = 0
    
    @property
    def acpl(self):
        return self.sample_total_cpl / float(self.sample_size) if self.sample_size else None

def a1(working_set):
    results = defaultdict(PgnSpyResult)
    for gid, game in working_set.items():
        game_obj, _ = Game.get_or_create(id=gid)

        a1_game(results, game_obj, 'w', GamePlayer.get(game=game_obj, color='w').player)
        a1_game(results, game_obj, 'b', GamePlayer.get(game=game_obj, color='b').player)
    
    with open('reports/testrep.txt', 'w') as fout:
        for player, result in sorted(results.items(), key=lambda i:i[1].acpl or 1000):
            fout.write(f'{player.username}\n')
            if result.t1_total:
                fout.write(f'T1: {result.t1_count}/{result.t1_total} {result.t1_count / result.t1_total:.1%}\n')
            if result.acpl:
                fout.write(f'ACPL: {result.acpl:.1f} ({result.sample_size})\n')


def a1_game(results, game_obj, color, player):
    moves = list(Move.select().where(Move.game == game_obj, Move.color == color).order_by(Move.number))

    r = results[player]

    for m in moves:
        if m.number <= book_depth:
            continue
        if m.pv1_eval <= -undecided_pos_thresh or m.pv1_eval >= undecided_pos_thresh:
            continue
        if m.pv2_eval and m.pv1_eval <= m.pv2_eval + forced_move_thresh and m.pv1_eval <= m.pv2_eval + unclear_pos_thresh:
            r.t1_total += 1
            if m.played_rank and m.played_rank <= 1:
                r.t1_count += 1
        if m.pv3_eval and m.pv2_eval <= m.pv3_eval + forced_move_thresh and m.pv1_eval <= m.pv3_eval + unclear_pos_thresh:
            r.t2_total += 1
            if m.played_rank and m.played_rank <= 2:
                r.t2_count += 1
        if m.pv4_eval and m.pv3_eval <= m.pv4_eval + forced_move_thresh and m.pv1_eval <= m.pv4_eval + unclear_pos_thresh:
            r.t3_total += 1
            if m.played_rank and m.played_rank <= 3:
                r.t3_count += 1
        cpl = max(m.pv1_eval - m.played_eval, 0)
        r.sample_size += 1
        r.sample_total_cpl += cpl
        if cpl > 0:
            r.gt0 += 1
        if cpl > 10:
            r.gt10 += 1
