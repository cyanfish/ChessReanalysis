from peewee import *

db = SqliteDatabase('./db/data.sqlite3')

class Player(Model):
    username = CharField(unique=True)

    class Meta:
        database = db

class Game(Model):
    id = CharField(unique=True)
    is_analyzed = BooleanField(default=False)

    class Meta:
        database = db

colors = (('w', 'White'), ('b', 'Black'))

class GamePlayer(Model):
    game = ForeignKeyField(Game)
    color = FixedCharField(max_length=1, choices=colors)
    player = ForeignKeyField(Player)

    class Meta:
        database = db
        indexes = (
            (('game', 'color'), True),
        )

class Move(Model):
    game = ForeignKeyField(Game)
    color = FixedCharField(max_length=1, choices=colors)
    number = SmallIntegerField()
    pv1eval = SmallIntegerField()
    pv2eval = SmallIntegerField()
    pv3eval = SmallIntegerField()
    pv4eval = SmallIntegerField()
    pv5eval = SmallIntegerField()
    eval = SmallIntegerField()
    pv = SmallIntegerField()

    class Meta:
        database = db

db.create_tables([Player, Game, GamePlayer, Move], True)
