from models import *
import chess, chess.pgn
import json
from collections import defaultdict
from datetime import datetime
from operator import eq, lt
from functools import partial
import math

# TODO: Make this configurable via the config file.
_cp_loss_intervals = [0, 10, 25, 50, 100, 200, 500]
_cp_loss_names = ["=0"] + [f">{cp_incr}" for cp_incr in _cp_loss_intervals]
_cp_loss_ops = [partial(eq,0)] + [partial(lt, cp_incr) for cp_incr in _cp_loss_intervals]

def generate_stats_string(sample, total):
    percentage = sample / total
    stderr = std_error(percentage, total)
    ci = confidence_interval(percentage, stderr)
    return f'{sample}/{total}; {percentage:.01%} (CI: {ci[0]*100:.01f} - {ci[1]*100:.01f})'

def std_error(p, n):
    return math.sqrt(p*(1-p)/n)

def confidence_interval(p, e):
    return [
        p - (2.0*e),
        p + (2.0*e)
    ]

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
        self.cp_loss_count = defaultdict(int)
        self.cp_loss_total = 0

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
        for k in _cp_loss_names:
            self.cp_loss_count[k] += other.cp_loss_count[k]
        self.cp_loss_total += other.cp_loss_total

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

def t_output(fout, result):
    if result.t1_total:
        fout.write('T1: {}\n'.format(generate_stats_string(result.t1_count, result.t1_total)))
    if result.t2_total:
        fout.write('T2: {}\n'.format(generate_stats_string(result.t2_count, result.t2_total)))
    if result.t3_total:
        fout.write('T3: {}\n'.format(generate_stats_string(result.t3_count, result.t3_total)))
    if result.acpl:
        fout.write(f'ACPL: {result.acpl:.1f} ({result.sample_size})\n')
    total = result.cp_loss_total
    if total > 0:
        for cp_loss_name in _cp_loss_names:
            loss_count = result.cp_loss_count[cp_loss_name]
            stats_str = generate_stats_string(loss_count, total)
            fout.write(f'  {cp_loss_name} CP loss: {stats_str}\n')

def t_output_csv(fout, result):
    if result.t1_total:
        fout.write(f'{result.t1_count}/{result.t1_total},{result.t1_count / result.t1_total:.1%},')
    else:
        fout.write('x,x,')
    if result.t2_total:
        fout.write(f'{result.t2_count}/{result.t2_total},{result.t2_count / result.t2_total:.1%},')
    else:
        fout.write('x,x,')
    if result.t3_total:
        fout.write(f'{result.t3_count}/{result.t3_total},{result.t3_count / result.t3_total:.1%},')
    else:
        fout.write('x,x,')
    if result.acpl:
        fout.write(f'{result.acpl:.1f},{result.sample_size},')
    else:
        fout.write('x,x,')

def a1(working_set, report_name):
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
    if excluded:
        print(f'Skipping {excluded} games that haven\'t been pre-processed')

    out_path = f'reports/report-a1--{datetime.now():%Y-%m-%d--%H-%M-%S}--{report_name}.txt'
    with open(out_path, 'w') as fout:
        fout.write('------ BY PLAYER ------\n\n')
        for player, result in sorted(by_player.items(), key=lambda i: i[1].t3_sort):
            fout.write(f'{player.username} ({result.min_rating} - {result.max_rating})\n')
            t_output(fout, result)
            fout.write(' '.join(result.game_list) + '\n')
            fout.write('\n')

        fout.write('\n------ BY GAME ------\n\n')
        for (player, gameid), result in sorted(by_game.items(), key=lambda i: i[1].t3_sort):
            fout.write(f'{player.username} ({result.min_rating})\n')
            t_output(fout, result)
            fout.write(' '.join(result.game_list) + '\n')
            fout.write('\n')
    print(f'Wrote report on {included} games to "{out_path}"')

def a1csv(working_set, report_name):
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
    if excluded:
        print(f'Skipping {excluded} games that haven\'t been pre-processed')

    out_path = f'reports/report-a1--{datetime.now():%Y-%m-%d--%H-%M-%S}--{report_name}.csv'
    with open(out_path, 'w') as fout:
        fout.write('Name,Rating range,T1:,T1%:,T2:,T2%:,T3:,T3%:,ACPL:,Positions,Games\n')
        for player, result in sorted(by_player.items(), key=lambda i: i[1].t3_sort):
            fout.write(f'{player.username},{result.min_rating} - {result.max_rating},')
            t_output_csv(fout, result)
            fout.write(' '.join(result.game_list) + '\n')

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

        if m.pv2_eval is not None and m.pv1_eval <= m.pv2_eval + p['forced_move_thresh'] and m.pv1_eval <= m.pv2_eval + p['unclear_pos_thresh']:
            if m.pv2_eval < m.pv1_eval:
                r.t1_total += 1
                if m.played_rank and m.played_rank <= 1:
                    r.t1_count += 1

            if m.pv3_eval is not None and m.pv2_eval <= m.pv3_eval + p['forced_move_thresh'] and m.pv1_eval <= m.pv3_eval + p['unclear_pos_thresh']:
                if m.pv3_eval < m.pv2_eval:
                    r.t2_total += 1
                    if m.played_rank and m.played_rank <= 2:
                        r.t2_count += 1

                if m.pv4_eval is not None and m.pv3_eval <= m.pv4_eval + p['forced_move_thresh'] and m.pv1_eval <= m.pv4_eval + p['unclear_pos_thresh']:
                    if m.pv4_eval < m.pv3_eval:
                        r.t3_total += 1
                        if m.played_rank and m.played_rank <= 3:
                            r.t3_count += 1

        cpl = min(max(m.pv1_eval - m.played_eval, 0), p['max_cpl'])
        r.cp_loss_total += 1
        for cp_name, cp_op in zip(_cp_loss_names, _cp_loss_ops):
            if cp_op(cpl):
                r.cp_loss_count[cp_name] += 1

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
