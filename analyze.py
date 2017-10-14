from models import *
import chess, chess.pgn
import json
from collections import defaultdict

book_depth = 10
forced_move_thresh = 50
unclear_pos_thresh = 100
undecided_pos_thresh = 200
losing_pos_thresh = 500
exclude_forced = True
include_only_unclear = True
exclude_flat = True
max_cpl = 500

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
        self.game_list = []
    
    def add(self, other):
        self.sample_size += other.sample_size
        self.sample_total_cpl += other.sample_total_cpl
        self.gt0 += other.gt0
        self.gt10 += other.gt10
        self.t1_total += other.t1_total
        self.t1_count += other.t1_count
        self.t2_total += other.t2_total
        self.t2_count += other.t2_count
        self.t3_total += other.t3_total
        self.t3_count += other.t3_count
        self.game_list += other.game_list
    
    @property
    def acpl(self):
        return self.sample_total_cpl / float(self.sample_size) if self.sample_size else None

def a1(working_set):
    by_player = defaultdict(PgnSpyResult)
    by_game = defaultdict(PgnSpyResult)
    for gid, game in working_set.items():
        game_obj, _ = Game.get_or_create(id=gid)

        a1_game(by_player, by_game, game_obj, 'w', GamePlayer.get(game=game_obj, color='w').player)
        a1_game(by_player, by_game, game_obj, 'b', GamePlayer.get(game=game_obj, color='b').player)
    
    with open('reports/testrep.txt', 'w') as fout:
        fout.write('------ BY PLAYER ------\n\n')
        for player, result in sorted(by_player.items(), key=lambda i:-i[1].t3_count/(i[1].t3_total or 1)):
            fout.write(f'{player.username}\n')
            if result.t1_total:
                fout.write(f'T1: {result.t1_count}/{result.t1_total} {result.t1_count / result.t1_total:.1%}\n')
            if result.t2_total:
                fout.write(f'T2: {result.t2_count}/{result.t2_total} {result.t2_count / result.t2_total:.1%}\n')
            if result.t3_total:
                fout.write(f'T3: {result.t3_count}/{result.t3_total} {result.t3_count / result.t3_total:.1%}\n')
            if result.acpl:
                fout.write(f'ACPL: {result.acpl:.1f} ({result.sample_size})\n')
            fout.write(' '.join(result.game_list) + '\n')
            fout.write('\n')

        fout.write('\n------ BY GAME ------\n\n')
        for (player, gameid), result in sorted(by_game.items(), key=lambda i:-i[1].t3_count/(i[1].t3_total or 1)):
            fout.write(f'{player.username}\n')
            if result.t1_total:
                fout.write(f'T1: {result.t1_count}/{result.t1_total} {result.t1_count / result.t1_total:.1%}\n')
            if result.t2_total:
                fout.write(f'T2: {result.t2_count}/{result.t2_total} {result.t2_count / result.t2_total:.1%}\n')
            if result.t3_total:
                fout.write(f'T3: {result.t3_count}/{result.t3_total} {result.t3_count / result.t3_total:.1%}\n')
            if result.acpl:
                fout.write(f'ACPL: {result.acpl:.1f} ({result.sample_size})\n')
            fout.write(' '.join(result.game_list) + '\n')
            fout.write('\n')

def a1_game(by_player, by_game, game_obj, color, player):
    moves = list(Move.select().where(Move.game == game_obj).order_by(Move.number, -Move.color))

    r = PgnSpyResult()
    r.game_list.append(game_obj.id)

    evals = []
    for m in moves:
        if m.color != color:
            evals.append(-m.pv1_eval)
            continue
        evals.append(m.pv1_eval)

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

        cpl = min(max(m.pv1_eval - m.played_eval, 0), max_cpl)
        if exclude_flat and cpl == 0 and evals[-3:] == [m.pv1_eval] * 3:
            # Exclude flat evals from CPL, e.g. dead drawn endings
            continue

        r.sample_size += 1
        r.sample_total_cpl += cpl
        if cpl > 0:
            r.gt0 += 1
        if cpl > 10:
            r.gt10 += 1
    
    by_player[player].add(r)
    by_game[(player, game_obj.id)].add(r)
