from mysql.connector import MySQLConnection
import mysql.connector
import mysql
from typing import Dict, List, NamedTuple, Optional
from enum import unique, Enum
import aiomysql
import datetime
from config import MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_USER


@unique
class UserRole(Enum):
    Client = 0
    Doctor = 1

    def __str__(self):
        return self.name


class User(NamedTuple):
    """User tuple"""
    name: str
    hashed_password: str
    role: UserRole

    def as_dict(self) -> Dict[str, str]:
        return {
            'name': self.name,
            'hashed_password': self.hashed_password,
            'role': str(self.role)
        }


@unique
class MessageStatus(Enum):
    """Status of message:
        Queue: message added but not reviewed
        Answered: message have been reviewed and answered
    """
    Queue = 0
    Answered = 1


class Message(NamedTuple):
    """Message tuple representation for type checking and easy fields access.
    Basically converts list with indices in named tuple with fields access
    """
    message_id: int
    user: str
    message_text: str
    status: MessageStatus
    sent_date: str
    is_doc: bool


class DBConnection():
    """Async MySQL singleton for medical issues managing. Works with only one DB."""
    _instance = None

    def __new__(cls, db_config: dict = None):
        if cls._instance is None:
            cls._instance = super(DBConnection, cls).__new__(cls)
            if db_config:
                cls.db_config = db_config
            else:
                cls.db_config = {
                    'host': MYSQL_HOST,
                    'port': MYSQL_PORT,
                    'user': MYSQL_USER,
                    'password': MYSQL_PASSWORD,
                }
                cls.db = "med"
            try:
                cls._instance._create_table_if_not_exists()
            except mysql.connector.Error as e:
                print(f"Can't create tables because: {e}")
        return cls._instance
    

    def _create_table_if_not_exists(self) -> None:
        try:
            print("DB CONFIG", self.db_config)
            with MySQLConnection(database=self.db, **self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS users (
                        name VARCHAR(255) PRIMARY KEY NOT NULL,
                        hashed_password VARCHAR(511) NOT NULL,
                        role VARCHAR(255) NOT NULL DEFAULT 'Client',
                        CHECK(role IN ('Client', 'Doctor'))
                        )
                        """
                    )
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS messages (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        author_name VARCHAR(255) NOT NULL,
                        message VARCHAR(1023) NOT NULL,
                        status VARCHAR(255) NOT NULL DEFAULT 'Queue',
                        time VARCHAR(255) NOT NULL DEFAULT '2000-01-01, 00:00',
                        is_doc BOOLEAN NOT NULL DEFAULT 0,
                        CHECK (status IN ('Queue', 'Answered')),
                        CHECK (CHAR_LENGTH(message) <= 1000)
                        )
                        """
                    )
                    conn.commit()
        except mysql.connector.Error as e:
            print(f"MySQL error occurred while creating tables: {e}")

    
    async def insert_message(self, client_name: str, message: str, is_doc: bool = False) -> bool:
        """Inserts new message in database

        Args:
            client_name (str): client's name
            message (str): text of message, must be less or equal 1000 symbols

        Returns:
            bool: Either operation succeeded or not. True for success, False if error occurred
        """
        if len(message) > 1000:
            print("MySQL error: message can't be longer than 1000 symbols")
            return False
        try:
            async with aiomysql.connect(db=self.db, **self.db_config) as conn:
                async with conn.cursor() as cursor:
                    now = datetime.datetime.now().strftime('%Y-%m-%d, %H:%M')
                    await cursor.execute("INSERT INTO messages (author_name, message, status, time, is_doc) VALUES (%s, %s, %s, %s, %s)", (client_name, message, 'Queue', now, is_doc))
                    await conn.commit()
            return True
        except aiomysql.Error as e:
            print(f"MySQL error occurred: {e}")
            return False
        

    async def insert_user_or_exists(self, name: str, hashed_password: str, role: UserRole = None) -> bool:
        """Inserts user, if no user with given username exists.

        Args:
            name (str): client's name
            hashed_password (str): user password hash
            role (UserRole, optional): Specify role if needed. By default is UserRole.Client

        Returns:
            bool: True, if operation ended without errors, otherwise False.
        """
        if role is None:
            role = UserRole.Client
        try:
            async with aiomysql.connect(db=self.db, **self.db_config) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("INSERT IGNORE INTO users (name, hashed_password, role) VALUES (%s, %s, %s)", (name, hashed_password, role.name))
                    await conn.commit()
            return True
        except aiomysql.Error as e:
            print(f"MySQL error occurred: {e}")
            return False
        

    async def get_user(self, name: str) -> Optional[User]:
        """Get client info from db by his name. 

        Args:
            name (str): Client's name.

        Returns:
            Optional[User]: Returns User if found client with given name, None if no client found or error occured.
        """
        try:
            async with aiomysql.connect(db=self.db, **self.db_config) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT name, hashed_password, role FROM users WHERE name = %s", (name,))
                    result = await cursor.fetchone()
            if result:
                return User(result[0], result[1], UserRole[result[2]])
            return None
        except aiomysql.Error as e:
            print(f"MySQL error occurred: {e}")
            return None
        

    async def get_queue(self, last_message_id: int) -> List[Message]:
        """Get list of not answered messages.

        Args:
            last_message_id (int): Last known message index.

        Returns:
            List[Message]: List of messages, if no updates or error occured - [] returned.
        """
        try:
            async with aiomysql.connect(db=self.db, **self.db_config) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT id, author_name, message, status, time, is_doc FROM messages WHERE status = 'Queue'")
                    messages = await cursor.fetchall()
            return [Message(message_id=int(message[0]), user=message[1], message_text=message[2], status=MessageStatus[message[3]], sent_date=message[4], is_doc=message[5]) for message in messages][last_message_id:]
        except aiomysql.Error as e:
            print(f"MySQL error occurred: {e}")
            return []
        

    async def change_message_status(self, message_id: int, new_status: MessageStatus) -> bool:
        """Changes status of message to provided.

        Args:
            message_id (int): Index of message.
            new_status (MessageStatus): New status to set.

        Returns:
            bool: True, if operation ended without errors, otherwise False.
        """
        try:
            async with aiomysql.connect(db=self.db, **self.db_config) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("UPDATE messages SET status = %s WHERE id = %s", (new_status.name, message_id))
                    await conn.commit()
            return True
        except aiomysql.Error as e:
            print(f"MySQL error occurred in 'change_message_status': {e}")
            return False
        

    async def mark_messages_as_answered(self, author_name: str) -> bool:
        """Marks all messages by one client answered.

        Args:
            author_name (str): Client's name.

        Returns:
            bool: True, if operation ended without errors, otherwise False.
        """
        try:
            async with aiomysql.connect(db=self.db, **self.db_config) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("UPDATE messages SET status = %s WHERE author_name = %s", (MessageStatus.Answered.name, author_name))
                    await conn.commit()
            return True
        except aiomysql.Error as e:
            print(f"MySQL error occurred in 'mark_messages_as_answered': {e}")
            return False
        

    async def get_new_messages(self, username: str, last_message_num: int) -> List[Message]:
        """Returns chat updates

        Args:
            username (str): Client's or doctor's name.
            last_message_num (int): Last received message index.

        Returns:
            List[Message]: List of new messages. [] if no updates found, or error occured.
        """
        try:
            async with aiomysql.connect(db=self.db, **self.db_config) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT id, message, status, time, is_doc FROM messages WHERE author_name = %s", (username,))
                    all_messages = await cursor.fetchall()
            return [Message(message_id=int(message[0]), user=username, message_text=message[1], status=MessageStatus[message[2]], sent_date=message[3], is_doc=message[4]) for message in all_messages][last_message_num:]
        except aiomysql.Error as e:
            print(f"MySQL error occurred in 'get_new_messages': {e}", flush=True)
            return []
