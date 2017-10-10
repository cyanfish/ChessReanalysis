from peewee import *

db = SqliteDatabase('./db/data.sqlite3')

class Player(Model):
    username = CharField(unique=True)

    class Meta:
        database = db

class Game(Model):
    id = CharField(primary_key=True)
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
    pv1_eval = SmallIntegerField()
    pv2_eval = SmallIntegerField(null=True)
    pv3_eval = SmallIntegerField(null=True)
    pv4_eval = SmallIntegerField(null=True)
    pv5_eval = SmallIntegerField(null=True)
    played_eval = SmallIntegerField()
    played_rank = SmallIntegerField(null=True)

    class Meta:
        database = db
        indexes = (
            (('game', 'color', 'number'), True),
        )

db.create_tables([Player, Game, GamePlayer, Move], True)
