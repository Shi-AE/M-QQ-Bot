import random
import time
from http.client import HTTPConnection

import requests
from lxml import etree
from nonebot import require
from nonebot.log import logger

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

interview_base_api = 'https://api.mianshiya.com/'
tag_api = 'api/tagCategory/list'
bank_api = 'api/question_bank/list/page/vo'

HTTPConnection.debuglevel = 1


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Question(metaclass=SingletonMeta):
    def __init__(self):
        Question.TagCategory()
        Question.QuestionBank()

    class TagCategory(metaclass=SingletonMeta):
        def __init__(self):
            self.__tag_category: list[str] = []
            self.update()

        def update(self) -> None:

            response = requests.post(
                f'{interview_base_api}/{tag_api}',
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'
                },
                json={'current': 1}
            )
            response_data = response.json()

            data: list = response_data.get('data', [])

            if len(data) > 0:
                self.__tag_category = list(map(lambda x: x.get('name'), data))

            logger.info("interview TagCategory 定时更新完成")

        def get_tag_category(self) -> list[str]:
            if len(self.__tag_category) < 3:
                self.update()
            return self.__tag_category

        def get_random_tags(self) -> str:
            tags = self.get_tag_category()
            return random.sample(tags, k=random.randint(0, len(tags)))

    class BankItem:
        def __init__(self, title, tagList, questions):
            self.questions = questions
            self.tagList: list[str] = tagList
            self.title = title

    class QuestionBank(metaclass=SingletonMeta):
        def __init__(self):
            self.__question_bank: list[Question.BankItem] = []
            self.update()

        @staticmethod
        def get_questions(item_id) -> list[dict]:
            time.sleep(random.randint(2, 4))
            response = requests.get(
                f'https://www.mianshiya.com/bank/{item_id}/question/',
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'
                }
            )
            text = response.text
            tree: etree._Element = etree.HTML(text)
            li_list: list[etree._Element] = tree.xpath(
                "//*[@id='basicLayout']/div/div[2]/div/main/div[2]/aside/div/ul/li"
            )

            questions = []
            for li in li_list:
                href = li.xpath(".//a/@href")[0]
                question = li.xpath(".//div/text()")[0]
                questions.append({
                    'href': href,
                    'question': question
                })

            return questions

        def update(self) -> None:
            response = requests.post(
                f'{interview_base_api}/{bank_api}',
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'
                },
                json={'current': 1, 'pageSize': 1000}
            )
            response_data = response.json()

            records: list = response_data.get('data', {}).get('records', [])

            if len(records) > 0:
                self.__question_bank: list[Question.BankItem] = list(map(
                    lambda x: Question.BankItem(
                        x.get('title', '暂无'),
                        x.get('tagList', ['其他']),
                        self.get_questions(x.get('id'))
                    ),
                    records))

            logger.info("interview QuestionBank 定时更新完成")

        def get_question_Bank(self) -> list:
            if len(self.__question_bank) < 3:
                self.update()
            return self.__question_bank

        def get_random_question(self, tags: list[str]):
            if tags is None or len(tags) == 0:
                tags = Question.TagCategory().get_random_tags()

            question_bank: list[Question.BankItem] = self.get_question_Bank()
            question_bank = list(
                filter(lambda x: set([item.lower() for item in tags]).issubset([item.lower() for item in x.tagList]),
                       question_bank))

            if len(question_bank) == 0:
                return None

            bank_item = random.choice(question_bank)
            question = random.choice(bank_item.questions)

            return {
                'title': bank_item.title,
                'question': question['question'],
                'tags': bank_item.tagList,
                'href': f"https://www.mianshiya.com/{question['href']}"
            }


@scheduler.scheduled_job("cron", hour=3)
def _():
    try:
        Question().TagCategory().update()
        Question().QuestionBank().update()
    except Exception as e:
        logger.error(e)
