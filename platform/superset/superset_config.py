"""Local course deployment. Credentials remain outside the project repository."""
import json
import pymysql
# Superset's MySQL type introspection imports MySQLdb constants even for mysql+pymysql.
pymysql.install_as_MySQLdb()
from pathlib import Path
from urllib.parse import quote_plus

_private = json.loads(Path('/opt/taobao/data/reporting/credentials.json').read_text())
SECRET_KEY = _private['superset_secret']
SQLALCHEMY_DATABASE_URI = ('mysql+pymysql://superset_meta:' + quote_plus(_private['superset_meta'])
    + '@127.0.0.1:3307/superset_meta?charset=utf8mb4')
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = False
BABEL_DEFAULT_LOCALE = 'zh'
LANGUAGES = {'zh': {'flag': 'cn', 'name': '中文'}, 'en': {'flag': 'us', 'name': 'English'}}
# This endpoint is bound to loopback and uses local HTTP during development.
TALISMAN_CONFIG = {'force_https': False, 'session_cookie_secure': False, 'content_security_policy': None}
SESSION_COOKIE_SECURE = False
SUPERSET_WEBSERVER_PORT = 8089
ROW_LIMIT = 10000
SQLLAB_TIMEOUT = 120
FEATURE_FLAGS = {'ENABLE_TEMPLATE_PROCESSING': False}
CACHE_CONFIG = {'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300}
DATA_CACHE_CONFIG = {'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300}
