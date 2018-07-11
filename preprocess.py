from models import *
import chess, chess.pgn, chess.uci
import json
from multiprocessing import Pool, Value

def run(working_set):
    # Exclude already-processed games
    to_process = set(working_set.keys()) - {g.id for g in Game.select(Game.id).where(Game.is_analyzed == True)}
    print(f'Skipping {len(working_set) - len(to_process)} already-processed games')

    engine_config = load_engine_config()
    parallelism = engine_config.get('parallelism', 1)
    p = Pool(parallelism)
    process_args = [
        {
            'total': len(to_process),
            'game_number': i,
            "pgn": working_set[gid],
            "gid": gid
        } for i, gid in enumerate(to_process)
    ]

    print(f"Processing {parallelism} games at a time")
    p.map(process_game, process_args)

def process_game(args):
    game_number = args['game_number']
    gid = args['gid']
    pgn = args['pgn']
    # Get the game DB object and the PGN moves
    game_obj, _ = Game.get_or_create(id=gid)
    moves = list(pgn.main_line())
    print(f'Processing {gid} ({len(moves)} moves) ({game_number})')

    white, _ = Player.get_or_create(username=pgn.headers['White'].lower())
    black, _ = Player.get_or_create(username=pgn.headers['Black'].lower())
    GamePlayer.get_or_create(game=game_obj, color='w', defaults={'player':white})
    GamePlayer.get_or_create(game=game_obj, color='b', defaults={'player':black})

    # Set up the engine
    engine_config = load_engine_config()
    engine = init_engine(engine_config)
    info_handler = chess.uci.InfoHandler()
    engine.info_handlers.append(info_handler)

    # Set up the board
    board = pgn.board()
    for m in moves:
        board.push(m)

    # Process each move in the game in reverse order
    moves_processed = 0
    for played_move in reversed(moves):
        board.pop()
        moves_processed += 1
        color = 'w' if board.turn == chess.WHITE else 'b'
        # Skip already-processed moves
        try:
            move = Move.get(game=game_obj, color=color, number=board.fullmove_number)
            continue
        except DoesNotExist:
            pass
        print(f'{gid} -> {moves_processed}/{len(moves)}')

        while True:
            try:
                # Run the engine for the top 5 moves
                engine.position(board)
                engine.setoption({'multipv': 5})
                engine.go(nodes=engine_config['nodes'])

                # Get the engine results
                pvs = {i: move_list[0] for (i, move_list) in info_handler.info['pv'].items()}
                evals = {i: score_to_cp(s) for (i, s) in info_handler.info['score'].items()}
                played_index = None
                for i, move in pvs.items():
                    if move == played_move:
                        played_index = i
                if not played_index:
                    # The played move was not in the top 5, so we need to analyze it separately
                    board.push(played_move)
                    if board.is_checkmate():
                        played_eval = 29999 if board.turn == chess.BLACK else -29999
                    else:
                        engine.position(board)
                        engine.setoption({'multipv': 1})
                        engine.go(nodes=engine_config['nodes'])
                        played_eval = -score_to_cp(info_handler.info['score'][1])
                    board.pop()
                else:
                    # The played move was in the top 5, so we can copy the corresponding eval to save time
                    played_eval = evals[played_index]

                # Store the evaluations in the DB
                move = Move.create(game=game_obj, color=color, number=board.fullmove_number, \
                                pv1_eval=evals.get(1), pv2_eval=evals.get(2), pv3_eval=evals.get(3), \
                                pv4_eval=evals.get(4), pv5_eval=evals.get(5), \
                                played_rank=played_index, played_eval=played_eval, \
                                nodes=info_handler.info.get('nodes'), masterdb_matches=masterdb_matches(board, move))
                break
            except TypeError:
                # If we get a bad engine output, score_to_cp will throw a TypeError. We can just retry
                continue

    game_obj.is_analyzed = True
    game_obj.save()
    engine.quit()

def masterdb_matches(board, move):
    pass

def score_to_cp(score):
    # Some arbitrary extreme values have been picked to represent mate
    if score.mate:
        return 30000 - score.mate if score.mate > 0 else -30000 - score.mate
    return min(max(score.cp, -29000), 29000)

def load_engine_config():
    with open('./config/engine.json') as config_f:
        return json.load(config_f)

def init_engine(config):
    engine = chess.uci.popen_engine(config['path'])
    engine.uci()
    engine.setoption(config['options'])
    return engine
