import json
import random
import time
from http.client import HTTPConnection
from pathlib import Path
from typing import Annotated

import nonebot
import requests
from lxml import etree
from nonebot import on_command, on_shell_command
from nonebot import require
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.exception import ParserExit
from nonebot.internal.params import ArgPlainText
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.params import ShellCommandArgs
from nonebot.rule import Namespace, ArgumentParser

from .problem import Problem

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import (  # type: ignore[import-untyped] # noqa: E402
    template_to_pic,
    config
)

# 载入bot名字
Bot_NICKNAME = list(nonebot.get_driver().config.nickname)
Bot_NICKNAME = Bot_NICKNAME[0] if Bot_NICKNAME else "脑积水"

HTTPConnection.debuglevel = 0

cf_base_api = 'https://codeforces.com/'
user_info_api = 'api/user.info'
profile_api = 'profile'
contest_api = "api/contest.list"


def get_color(rating: int):
    rating_levels = {
        "newbie": {
            "range": range(0, 1200),
            "color": [("#1d2129", "#86909c"), ("#3A3F5A", "#BEC7DE"), ("#26255B", "#AAAEC3"), ("#A11069", "#a9aeb8"),
                      ("#8A0993", "#a9aeb8"), ("#3C108F", "#a9aeb8"), ("#072CA6", "#a9aeb8"), ("#114BA3", "#a9aeb8"),
                      ("#07828B", "#a9aeb8"), ("#008026", "#a9aeb8"), ("#5F940A", "#a9aeb8"), ("#FADC19", "#a9aeb8"),
                      ("#F7BA1E", "#a9aeb8"), ("#FF7D00", "#a9aeb8"), ("#F77234", "#a9aeb8"), ("#F53F3F", "#a9aeb8"),
                      ("#CC6C74", "#a9aeb8"), ("#83CCA8", "#a9aeb8")]
        },
        "pupil": {
            "range": range(1200, 1400),
            "color": [("#004D1C", "#00B42A"), ("#2A4D00", "#9FDB1D"), ("#054D00", "#46EE1E"), ("#004D2E", "#39D581"),
                      ("#004D36", "#9DF9D1")]
        },
        "specialist": {
            "range": range(1400, 1600),
            "color": [("#00424D", "#14C9C9"), ("#002E4D", "#0293C7"), ("#000D4D", "#165DFF"), ("#00174D", "#4E8AD8"),
                      ("#001A4D", "#3491FA"), ("#002E4D", "#17B6F2"), ("#000A4D", "#6F8BDA"), ("#0F0FA0", "#9588E4"),
                      ("#00474D", "#16988F")]
        },
        "expert": {
            "range": range(1600, 1900),
            "color": [("#16004D", "#722ED1"), ("#22004D", "#8A1BDB"), ("#0B004D", "#8B6CD9"), ("#6137CC", "#B991FA"),
                      ("#9357AD", "#D7ADE1"), ("#682DA3", "#E0B0FB"), ("#8735A2", "#EEB0F9")]
        },
        "candidate-master": {
            "range": range(1900, 2100),
            "color": [("#42004D", "#D91AD9"), ("#4D0040", "#CB379E"), ("#4D0032", "#A8115E"), ("#4D0028", "#A42A59")]
        },
        "master": {
            "range": range(2100, 2300),
            "color": [("#4D3800", "#FADC19"), ("#4D2D00", "#F7BA1E"), ("#4D3600", "#E7CB3E"), ("#D29237", "#FFDD92"),
                      ("#A19124", "#F6EE6E")]
        },
        "international-master": {
            "range": range(2300, 2400),
            "color": [("#4D1B00", "#FF7D00"), ("#4D0E00", "#F77234"), ("#4D1100", "#E27234"), ("#4D1C00", "#FF8309"),
                      ("#4D0900", "#F4490E")]
        },
        "grandmaster": {
            "range": range(2400, 2600),
            "color": [("#F5319D", "#FDC2DB"), ("#F53F3F", "#FDCDC5"), ("#DF4883", "#F9C5D2"), ("#4D001C", "#FE7191"),
                      ("#4D0022", "#F24077")]
        },
        "international-grandmaster": {
            "range": range(2600, 3000),
            "color": [("#4D0034", "#F5319D"), ("#4D0026", "#C81E5C"), ("#4D0028", "#DF4883"), ("#4D001C", "#FE7191"),
                      ("#4D0024", "#E32564"), ("#BD1B3A", "#F2B7BA"), ("#4D0005", "#EB1504")]
        },
        "legendary-grandmaster": {
            "range": range(3000, 9999),
            "color": [("#4D000A", "#F53F3F"), ("#4D0018", "#BD1B3A"), ("#4D0020", "#980C34"), ("#4D001B", "#D32B4F")]
        }
    }

    for _, rating_range in rating_levels.items():
        if rating in rating_range['range']:
            return random.choice(rating_range['color'])


async def getCodeforcesUserSolvedNumber(handle: str) -> int:
    try:
        url = f"{cf_base_api}/{profile_api}/{handle}"
        response = requests.get(url).text
        tree: etree._Element = etree.HTML(response, None)
        result: list[etree._Element] = tree.xpath(
            "//div[@class='_UserActivityFrame_footer']/div/div/div/text()")
        target: str = str(result[0])
        return int(target.split(" ")[0])
    except Exception:
        return 0


async def qurye_info(cf_userid):
    try:
        response = requests.get(
            f'{cf_base_api}/{user_info_api}',
            params={
                'handles': cf_userid,
                'checkHistoricHandles': False
            },
            timeout=(5, 10)
        )

        data = response.json()

        if data is None:
            await codeforces.finish('查询出错了，接下来跳跃很有用', at_sender=True)

        if data['status'] != "OK":
            await codeforces.finish(data['comment'], at_sender=True)

        if len(data['result']) == 0:
            await codeforces.finish('查询出错了，接下来跳跃很有用', at_sender=True)

        result: dict = data['result'][0]

        template_path = str(Path(__file__).parent / "templates")
        template_name = "card.html"

        color = get_color(result['rating'] if 'rating' in result.keys() else 0)

        pic = await template_to_pic(
            template_path=template_path,
            template_name=template_name,
            templates={
                'handle': result.get('handle', ''),
                'max_rating': result.get('maxRating', 0),
                'rating': result.get('rating', 0),
                'avatar': result.get('avatar', ''),
                'solved': await getCodeforcesUserSolvedNumber(result.get('handle', '')),
                'dark_color': color[0],
                'light_color': color[1],
            },
            pages={
                "viewport": {"width": 400, "height": 248},
            }
        )

        await codeforces.finish(MessageSegment.image(pic))
    except requests.exceptions.Timeout:
        await codeforces.send('查询错误，接下来跳跃很有用', at_sender=True)
    except json.JSONDecodeError:
        await codeforces.send('查询错误，接下来跳跃很有用', at_sender=True)


codeforces = on_command('cf', aliases={'CF', 'Codeforces', 'codeforces'}, priority=3)


@codeforces.handle()
async def _(matcher: Matcher, cf_userid: Message = CommandArg()):
    if cf_userid.extract_plain_text():
        matcher.set_arg('cf_userid', cf_userid)


@codeforces.got('cf_userid', prompt='您想要查询的ID是')
async def _(cf_userid: str = ArgPlainText('cf_userid')):
    await qurye_info(cf_userid)


contest = on_command('比赛', aliases={'contest', '今日比赛'}, priority=3)

phase_name = {
    'BEFORE': '未开始 (BEFORE)',
    'CODING': '比赛中 (CODING)',
    'PENDING_SYSTEM_TEST': '等待代码测试 (PENDING_SYSTEM_TEST)',
    'SYSTEM_TEST': '系统测试 (SYSTEM_TEST)'
}


@contest.handle()
async def _():
    try:
        response = requests.get(
            f'{cf_base_api}/{contest_api}',
            params={'gym': False},
            timeout=(5, 10)
        )

        data = response.json()

        if data is None:
            await codeforces.finish('查询出错了，接下来跳跃很有用', at_sender=True)

        if data['status'] != "OK":
            await codeforces.finish(data['comment'], at_sender=True)

        result: list = data['result']

        message = ''

        out_list = []

        for item in result:
            if item['phase'] == 'FINISHED':
                break
            out_list.append(item)

        for item in out_list[::-1]:
            message += f"{item['name']}\n"
            message += f"计分类型: {item['type']}\n"
            message += f"状态: {phase_name[item['phase']]}\n"
            message += f"时长: {int(item['durationSeconds'] / 60 // 60)} 小时 {int(item['durationSeconds'] / 60 % 60)} 分钟\n"
            message += f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item['startTimeSeconds']))} UTC+8\n"
            message += f"传送门--> https://codeforces.com/contests/{item['id']} \n"
            message += "⚡⚡⚡⚡⚡⚡⚡⚡\n"

        if message == '':
            await codeforces.finish('数据不能从这一侧获取', at_sender=True)
        else:
            await codeforces.finish(f"前有绝景:\n{message}", at_sender=True)
    except requests.exceptions.Timeout:
        await codeforces.send('查询错误，你没有资格啊', at_sender=True)
    except json.JSONDecodeError:
        await codeforces.send('查询错误，你没有资格啊', at_sender=True)


training_parser = ArgumentParser(prog="加训 | contest", description="获得随机加训题目", add_help=True)
training_parser.add_argument('-s', '--show', action='store_true',
                             required=False, help='是否显示题目标签，默认不显示')
training_parser.add_argument('-n', '--name', action='store',
                             required=False, help='题目名')
training_parser.add_argument('-r', '--rating', action='store',
                             required=False, help='题目分数', type=int)
training_parser.add_argument('-t', '--tags', action='store',
                             required=False, nargs='*',
                             help='''题目标签, 可用的标签有(如有空格加引号): '2-sat' ⚡ 'binary search' ⚡ 'bitmasks' ⚡ 'brute force' ⚡ 
                             'bitmasks' ⚡ 'bitmasks' ⚡ 'bitmasks' ⚡ 'chinese remainder theorem' ⚡ 'combinatorics' ⚡ 
                             'constructive algorithms' ⚡ 'data structures' ⚡ 'dfs and similar' ⚡ 'divide and conquer' 
                             ⚡ 'dp' ⚡ 'dsu' ⚡ 'expression parsing' ⚡ 'fft' ⚡ 'flows' ⚡ 'games' ⚡ 'geometry' ⚡ 'graph 
                             matchings' ⚡ 'graphs' ⚡ 'greedy' ⚡ 'hashing' ⚡ 'implementation' ⚡ 'interactive' ⚡ 'math' 
                             ⚡ 'matrices' ⚡ 'meet-in-the-middle' ⚡ 'number theory' ⚡ 'probabilities' ⚡ 'schedules' ⚡ 
                             'shortest paths' ⚡ 'sortings' ⚡ 'string suffix structures' ⚡ 'strings' ⚡ 'ternary 
                             search' ⚡ 'trees' ⚡ 'two pointers' ''')
training = on_shell_command('加训', aliases={'题目', '问题', '加练', "problem", '每日一题'}, parser=training_parser)


# 解析失败
@training.handle()
async def _(foo: Annotated[ParserExit, ShellCommandArgs()]):
    await training.finish(foo.message, at_sender=True)


@training.handle()
async def _(foo: Annotated[Namespace, ShellCommandArgs()]):
    try:

        arg = vars(foo)

        random_problem = Problem().get_random_problem(arg.get('name'), arg.get('rating'), arg.get('tags'))

        if random_problem is None:
            await training.finish("⚡⚡没有满足条件的题目哦⚡⚡", at_sender=True)

        message = f"{Bot_NICKNAME} 请你加训:\n"
        message += f"题目: {random_problem.get('index')}. {random_problem.get('name', '')}\n"
        message += f"难度: {random_problem.get('rating', '未知')}\n"
        if arg.get('show'):
            message += f"标签: {random_problem.get('tags', '无')}\n"
        message += f"传送门--> https://codeforces.com/problemset/problem/{random_problem.get('contestId')}/{random_problem.get('index')}\n"

        await training.finish(message, at_sender=True)

    except json.JSONDecodeError:
        await codeforces.finish('查询错误，你没有资格啊', at_sender=True)
