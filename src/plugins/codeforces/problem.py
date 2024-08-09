import random
from http.client import HTTPConnection

import requests
from nonebot import require
from nonebot.log import logger

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

HTTPConnection.debuglevel = 1

cf_base_api = 'https://mirror.codeforces.com/'
problems_api = 'api/problemset.problems'


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Problem(metaclass=SingletonMeta):
    def __init__(self):
        self.__problem: list = []
        self.update()

    def update(self) -> None:
        response = requests.get(
            f'{cf_base_api}/{problems_api}',
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'
            }
        )

        if response.status_code != 200:
            return

        data = response.json()

        if data.get('status') != "OK" or 'result' not in data:
            return

        result = data['result']
        if 'problems' in result:
            self.__problem = result['problems']

        logger.info("cf problems 定时更新完成")

    def get_problems(self) -> list:
        if len(self.__problem) <= 10:
            self.update()

        return self.__problem

    def get_random_problem(self, name: str, rating: int, tags: list):

        temp_problems = self.get_problems()

        if name is not None:
            temp_problems = list(
                filter(lambda x: name.strip().lower() in x.get('name', '').strip().lower(), temp_problems))

        if rating is not None:
            if rating < 800:
                rating = 800

            rating -= rating % 100

            temp_problems = list(filter(lambda x: x.get('rating', 0) == rating, temp_problems))

        if tags is not None and len(tags) > 0:
            temp_problems = list(
                filter(lambda x: all(item in x.get('tags', []) for item in tags), temp_problems))

        if len(temp_problems) == 0:
            return None

        return random.choice(temp_problems)


@scheduler.scheduled_job("cron", hour=3)
def _():
    try:
        Problem().update()
    except Exception as e:
        logger.error(e)
