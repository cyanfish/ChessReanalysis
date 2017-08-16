from models import *
import chess, chess.pgn, chess.uci
import json

def run(working_set):
    for gid, game in working_set.items():
        game_obj, _ = Game.get_or_create(id=gid)
        if game_obj.is_analyzed:
            continue
        moves = game.accept(MoveListVisitor())
        engine_config = load_engine_config()
        engine = init_engine(engine_config)
        for m in reversed(moves):
            engine.setoption({'multipv': 5})
            engine.position(m.board())
            # TODO: Need an info handler for multipv results
            result = engine.go(nodes=engine_config['nodes'])
            print(result)

def load_engine_config():
    with open('./config/engine.json') as config_f:
        return json.load(config_f)

def init_engine(config):
    engine = chess.uci.popen_engine(config['path'])
    engine.uci()
    engine.setoption(config['options'])
    return engine

class MoveListVisitor(chess.pgn.BaseVisitor):
    def begin_game(self):
        self.moves = []

    def visit_move(self, board, move):
        self.moves.append(move)

    def result(self):
        return self.moves

