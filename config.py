from dotenv import load_dotenv
import os

load_dotenv()

DOCTOR_USERNAME = os.getenv("doctor_username")
DOCTOR_PASSWORD = os.getenv("doctor_password")

MYSQL_USER = os.getenv("mysql_user")
MYSQL_PASSWORD = os.getenv("mysql_password")
MYSQL_HOST = os.getenv("mysql_host")
try:
    MYSQL_PORT = int(os.getenv("mysql_port"))
except ValueError:
    print("Specified port is not a valid int")
    SystemExit(1)

SECRET_KEY = os.getenv("secret_key")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30