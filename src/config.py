import os
from dotenv import load_dotenv

import sys
sys.path.append('.')

load_dotenv('.env')

class DBSettings:
	
    MYSQL_HOST = os.environ.get("MYSQL_HOST")
    MYSQL_DB_NAME  = os.environ.get("MYSQL_DB_NAME")
    MYSQL_USERNAME = os.environ.get("MYSQL_USERNAME")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
    
    DATABASE_URL = f"mysql+pymysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_HOST}:3306/{MYSQL_DB_NAME}"


settings = DBSettings()