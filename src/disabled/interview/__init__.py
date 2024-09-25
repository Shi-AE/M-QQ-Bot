import json
from typing import Annotated

import nonebot
from nonebot import on_shell_command
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.rule import Namespace, ArgumentParser

from src.disabled.interview.question import Question

# 载入bot名字
Bot_NICKNAME = list(nonebot.get_driver().config.nickname)
Bot_NICKNAME = Bot_NICKNAME[0] if Bot_NICKNAME else "脑积水"

training_parser = ArgumentParser(prog="面试 | interview", description="获得随机面试题目", add_help=True)
training_parser.add_argument('-t', '--tags', action='store',
                             required=False, nargs='*',
                             help="题目标签, 可用的标签有(如有空格加引号)")
training_parser.add_argument('-s', '--showTags', action='store_true',
                             required=False, help="查询题目标签")
interview = on_shell_command('面试', aliases={'interview'}, parser=training_parser)


# 解析失败
@interview.handle()
async def _(foo: Annotated[ParserExit, ShellCommandArgs()]):
    await interview.finish(foo.message, at_sender=True)


@interview.handle()
async def _(foo: Annotated[Namespace, ShellCommandArgs()]):
    try:
        arg = vars(foo)

        if arg.get('showTags'):
            await interview.finish(f'可用的标签有: {str(Question.TagCategory().get_tag_category())}', at_sender=True)

        q = Question.QuestionBank().get_random_question(arg.get('tags'))

        if q is None:
            await interview.finish("⚡⚡没有满足条件的题目哦⚡⚡", at_sender=True)

        message = f"{Bot_NICKNAME} 的面试开始:\n"
        message += f"主题: {q.get('title')}\n\n"
        message += f"问题: {q.get('question')}\n\n"
        message += f"标签: {q.get('tags')}\n"
        message += f"传送门--> {q.get('href')}\n"
        message += "大部分题目不提供答案，需自行在互联网上查阅学习"

        await interview.finish(message, at_sender=True)
    except json.JSONDecodeError:
        await interview.finish('查询错误，你没有资格啊', at_sender=True)
