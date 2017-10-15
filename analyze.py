from models import *
import chess, chess.pgn
import json
from collections import defaultdict
from datetime import datetime

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
        self.min_rating = None
        self.max_rating = None
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
        self.with_rating(other.min_rating)
        self.with_rating(other.max_rating)
        self.game_list += other.game_list
    
    def with_rating(self, rating):
        if rating is None:
            return
        self.min_rating = min(self.min_rating, rating) if self.min_rating else rating
        self.max_rating = max(self.max_rating, rating) if self.max_rating else rating

    @property
    def acpl(self):
        return self.sample_total_cpl / float(self.sample_size) if self.sample_size else None

    @property
    def t3_sort(self):
        if self.t3_total == 0:
            return 0
        return -wilson_interval(self.t3_count, self.t3_total)[0]

def a1(working_set):
    p = load_a1_params()
    by_player = defaultdict(PgnSpyResult)
    by_game = defaultdict(PgnSpyResult)
    excluded = included = 0
    for gid, pgn in working_set.items():
        game_obj, _ = Game.get_or_create(id=gid)
        if not game_obj.is_analyzed:
            excluded += 1
            continue

        a1_game(p, by_player, by_game, game_obj, pgn, 'w', GamePlayer.get(game=game_obj, color='w').player)
        a1_game(p, by_player, by_game, game_obj, pgn, 'b', GamePlayer.get(game=game_obj, color='b').player)
        included += 1
    print(f'Skipping {excluded} games that haven\'t been pre-processed')

    out_path = f'reports/report-a1--{datetime.now():%Y-%m-%d--%H-%M-%S}.txt'
    with open(out_path, 'w') as fout:
        fout.write('------ BY PLAYER ------\n\n')
        for player, result in sorted(by_player.items(), key=lambda i: i[1].t3_sort):
            fout.write(f'{player.username} ({result.min_rating} - {result.max_rating})\n')
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
        for (player, gameid), result in sorted(by_game.items(), key=lambda i: i[1].t3_sort):
            fout.write(f'{player.username} ({result.min_rating})\n')
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
    print(f'Wrote report on {included} games to "{out_path}"')

def a1_game(p, by_player, by_game, game_obj, pgn, color, player):
    moves = list(Move.select().where(Move.game == game_obj).order_by(Move.number, -Move.color))

    r = PgnSpyResult()
    r.game_list.append(game_obj.id)
    try:
        r.with_rating(int(pgn.headers['WhiteElo' if color == 'w' else 'BlackElo']))
    except ValueError:
        pass

    evals = []
    for m in moves:
        if m.color != color:
            evals.append(-m.pv1_eval)
            continue
        evals.append(m.pv1_eval)

        if m.number <= p['book_depth']:
            continue

        if m.pv1_eval <= -p['undecided_pos_thresh'] or m.pv1_eval >= p['undecided_pos_thresh']:
            continue
        if m.pv2_eval and m.pv1_eval <= m.pv2_eval + p['forced_move_thresh'] and m.pv1_eval <= m.pv2_eval + p['unclear_pos_thresh']:
            r.t1_total += 1
            if m.played_rank and m.played_rank <= 1:
                r.t1_count += 1
        if m.pv3_eval and m.pv2_eval <= m.pv3_eval + p['forced_move_thresh'] and m.pv1_eval <= m.pv3_eval + p['unclear_pos_thresh']:
            r.t2_total += 1
            if m.played_rank and m.played_rank <= 2:
                r.t2_count += 1
        if m.pv4_eval and m.pv3_eval <= m.pv4_eval + p['forced_move_thresh'] and m.pv1_eval <= m.pv4_eval + p['unclear_pos_thresh']:
            r.t3_total += 1
            if m.played_rank and m.played_rank <= 3:
                r.t3_count += 1

        cpl = min(max(m.pv1_eval - m.played_eval, 0), p['max_cpl'])
        if p['exclude_flat'] and cpl == 0 and evals[-3:] == [m.pv1_eval] * 3:
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

def load_a1_params():
    with open('./config/params_for_a1.json') as config_f:
        return json.load(config_f)

def wilson_interval(ns, n):
    z = 1.96 # 0.95 confidence
    a = 1 / (n + z**2)
    b = ns + z**2 / 2
    c = z * (ns * (n - ns) / n + z**2 / 4)**(1/2)
    return (a * (b - c), a * (b + c))
