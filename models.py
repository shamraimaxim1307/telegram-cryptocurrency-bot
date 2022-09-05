from peewee import Model, CharField, IntegerField, SqliteDatabase, ForeignKeyField, DecimalField

db = SqliteDatabase("database/botTelegram.sqlite3")


class User(Model):
    chat_id = CharField()
    remain_money = DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        database = db


class Crypto(Model):
    name_crypto = CharField()
    price_per_crypto = DecimalField(max_digits=10, decimal_places=3)
    count_crypto = IntegerField()
    price_crypto = DecimalField(max_digits=10, decimal_places=3)
    foreign_key = ForeignKeyField(User)

    class Meta:
        database = db


if __name__ == '__main__':
    db.create_tables([User, Crypto])
