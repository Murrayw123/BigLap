import datetime
from peewee import *
from flask_login import UserMixin
from flask_bcrypt import generate_password_hash

DATABASE = SqliteDatabase('biglap.db')

class User(UserMixin, Model):
    username = CharField(unique=True)
    email = CharField(unique=True)
    password = CharField(max_length=100)
    joined_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = DATABASE

    @classmethod
    def create_user(cls, username, email, password):
        """class method to create a new user instance"""
        try:
            cls.create(
                username = username,
                email = email,
                password = generate_password_hash(password)
            )
        except IntegrityError:
            raise ValueError("User already exists")

class SavedTrips(Model):
    origin = TextField()
    destination = TextField()

    class Meta:
        database = DATABASE

def initialize():
    DATABASE.connect()
    DATABASE.create_tables([User], safe=True)
    DATABASE.create_tables([SavedTrips], safe=True)
    DATABASE.close

