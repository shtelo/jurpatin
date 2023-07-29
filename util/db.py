from datetime import datetime, timedelta
from typing import Optional, Any

from pymysql import connect, Connection

from util import get_secret


_get_connection_cache: Optional[Connection] = None
_get_connection_last_used = None
def get_connection():
    global _get_connection_cache, _get_connection_last_used
    now = datetime.now()

    # if old connection
    if _get_connection_last_used is not None \
            and now - _get_connection_last_used > timedelta(hours=1):
        _get_connection_cache.close()
        _get_connection_cache = None

    # if connection does not exist
    if _get_connection_cache is None:
        _get_connection_cache = connect(
            host=get_secret('database.host'),
            user=get_secret('database.user'),
            password=get_secret('database.password'),
            database=get_secret('database.database'),
        )
        _get_connection_last_used = now

    return _get_connection_cache


def get_money(user_id: int) -> Optional[int]:
    database = get_connection()
    with database.cursor() as cursor:
        cursor.execute('SELECT money FROM money WHERE id = %s', (user_id,))
        data = cursor.fetchone()

        if data:
            return data[0]

        create_account(user_id)
        return 0


def create_account(user_id: int) -> None:
    database = get_connection()
    with database.cursor() as cursor:
        cursor.execute('INSERT INTO money (id) VALUES (%s)', (user_id,))
        database.commit()


def set_money(user_id: int, money: int) -> None:
    database = get_connection()
    with database.cursor() as cursor:
        cursor.execute('UPDATE money SET money = %s WHERE id = %s', (money, user_id))
        database.commit()


def add_money(user_id: int, money: int) -> None:
    """
    :param user_id: User ID
    :param money: Amount of money to add in cŁ
    """
    database = get_connection()
    with database.cursor() as cursor:
        cursor.execute('INSERT INTO money (id, money) VALUES (%s, %s) '
                       'ON DUPLICATE KEY UPDATE money = money + %s',
                       (user_id, money, money))
        database.commit()


def get_money_ranking(limit: int = 10) -> tuple[tuple[Any, ...], ...]:
    database = get_connection()
    with database.cursor() as cursor:
        cursor.execute('SELECT id, money, rank() OVER (ORDER BY money DESC) FROM money LIMIT %s', (limit,))
        return cursor.fetchall()


def set_value(key: str, value) -> None:
    database = get_connection()
    with database.cursor() as cursor:
        cursor.execute('INSERT INTO `values` (`key`, value) VALUES (%s, %s) '
                       'ON DUPLICATE KEY UPDATE value = %s', (key, value, value))
        database.commit()


def get_value(key: str) -> Optional[str]:
    database = get_connection()
    with database.cursor() as cursor:
        cursor.execute('SELECT value FROM `values` WHERE `key` = %s', (key,))
        data = cursor.fetchone()

        if data:
            return data[0]

        return None


def remove_value(key: str) -> None:
    database = get_connection()
    with database.cursor() as cursor:
        cursor.execute('DELETE FROM `values` WHERE `key` = %s', (key,))
        database.commit()


def get_inventory(user_id: int) -> dict[str, int]:
    database = get_connection()
    with database.cursor() as cursor:
        cursor.execute('SELECT name, amount FROM inventory WHERE id = %s', (user_id,))
        # noinspection PyTypeChecker
        return dict(cursor.fetchall())


def set_inventory(user_id: int, name: str, amount: int) -> None:
    database = get_connection()
    with database.cursor() as cursor:
        if amount:
            cursor.execute('INSERT INTO inventory (id, name, amount) VALUES (%s, %s, %s) '
                           'ON DUPLICATE KEY UPDATE amount = %s', (user_id, name, amount, amount))
        else:
            cursor.execute('DELETE FROM inventory WHERE id = %s AND name = %s', (user_id, name))
        database.commit()


def add_inventory(user_id: int, name: str, amount: int) -> None:
    database = get_connection()
    with database.cursor() as cursor:
        cursor.execute('INSERT INTO inventory (id, name, amount) VALUES (%s, %s, %s) '
                       'ON DUPLICATE KEY UPDATE amount = amount + %s', (user_id, name, amount, amount))
        database.commit()


# noinspection PyTypeChecker
def get_lotteries() -> tuple[tuple[int, str, int], ...]:
    database = get_connection()
    with database.cursor() as cursor:
        cursor.execute("SELECT id, name, amount FROM inventory WHERE name LIKE '로또: %'")
        return cursor.fetchall()


def clear_lotteries():
    database = get_connection()
    with database.cursor() as cursor:
        cursor.execute("DELETE FROM inventory WHERE name LIKE '로또: %'")
        database.commit()


if __name__ == '__main__':
    from datetime import timedelta
    set_value('test', timedelta(seconds=1239487))
