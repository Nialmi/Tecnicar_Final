import os
import redis

class Config:
    SECRET_KEY = 'una_clave_secreta_muy_segura'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_REDIS = redis.StrictRedis(host='localhost', port=6379, db=0)
