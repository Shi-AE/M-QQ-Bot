import asyncio
import os
import random

import nonebot
import nonebot.adapters.onebot.v11
from nonebot import CommandGroup, get_plugin_config
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me
from nonebot.typing import T_State

from .config import Config
from .get_translate import translate
from .img import wordleOutput

# import nonebot.adapters.console

# 获取配置
config = get_plugin_config(Config).wordle

# 命令注册
__plugin_meta__ = PluginMetadata(
    name="wordle",
    description="英语猜词",
    usage=(
        "  wordle.help 显示帮助列表\n"
        "  wordle.help <command> 显示详细帮助\n"
        "  wordle.rule 显示规则\n"
        "  wordle.start <len> 开始一局长度为 <len> 的 wordle\n"
        "  wordle.guess <word> 尝试匹配 <word> 单词\n"
        "  wordle.giveup 放弃该对局 (需要 @bot 或私聊)\n"
        "  wordle.remain 显示未使用过的字母\n"
        "  wordle.history 显示历史猜测\n"
        "注意 此功能可能会造成刷屏"
    ),
    type="application",
    homepage="https://www.github.com/shiyihang2007/nonebot-plugin-wordle-simple/",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra={
        "unique_name": "nonebot_plugin_wordle_simple",
        "example": "",
        "author": "shiyihang <467557146@qq.com>",
        "version": "0.0.6",
    },
)


async def is_enabled(event: MessageEvent) -> bool:
    if isinstance(event, GroupMessageEvent):
        group_id = str(event.group_id)
        user_id = str(event.get_user_id())
        # 不回复黑名单用户
        if user_id in config.ban_user:
            return False
        # 在允许的群聊中启用
        if group_id in config.groups_enabled:
            return True
        return False
    # 启用私聊
    return True


async def is_admin(bot: Bot, event: MessageEvent, state: T_State) -> bool:
    if not await to_me()(bot, event, state):
        return False
    user_id: str = event.get_user_id()
    if isinstance(event, GroupMessageEvent):
        group_id: str = str(event.group_id)
        user_info: dict = await bot.call_api(
            "get_group_member_info", **{"group_id": group_id, "user_id": user_id}
        )
        user_role: str = user_info["role"]
        # 只允许管理员使用
        if user_role in ["owner", "admin"]:
            return True
        return False
    # 禁用私聊
    return False


wordleGroup: CommandGroup = CommandGroup("wordle", priority=config.command_priority)

debugEnable = wordleGroup.command("debug_enable", permission=SUPERUSER)
debugDisable = wordleGroup.command("debug_disable", permission=SUPERUSER)
changeMinLength = wordleGroup.command("change_min_length", rule=is_admin)
changeMaxLength = wordleGroup.command("change_max_length", rule=is_admin)
change_try_limit = wordleGroup.command("change_try_limit", rule=is_admin)

commandEnable = wordleGroup.command("enable", aliases={"启用"}, rule=is_admin)
commandDisable = wordleGroup.command("disable", aliases={"禁用"}, rule=is_admin)

wordle = wordleGroup.command(tuple(), rule=is_enabled)
wordle_help = wordleGroup.command("help", rule=is_enabled)
rule = wordleGroup.command("rule", rule=is_enabled)
start = wordleGroup.command("start", rule=is_enabled)
guess = wordleGroup.command("guess", rule=is_enabled)
giveup = wordleGroup.command("giveup", rule=is_enabled & to_me())
remain = wordleGroup.command("remain", rule=is_enabled)
history = wordleGroup.command("history", rule=is_enabled)
debug = wordleGroup.command("debug", rule=is_enabled)

# 全局变量初始化
keyWord: str = ""
historyGuess: list[str] = []
historyGuessWord: list[str] = []
trycnt: int = 0
dictionary: list[str] = []
usedChars: dict = {}


# admin
@debugEnable.handle()
async def _():
    global config
    config.debug_enabled = True


@debugDisable.handle()
async def _():
    global config
    config.debug_enabled = False


@change_try_limit.handle()
async def _(args: Message = CommandArg()):
    global config
    change_to_times = config.try_limit
    try:
        change_to_times = int(args.extract_plain_text())
    except TypeError:
        await change_try_limit.finish(f"{args.extract_plain_text()} 不是有效的数字")
    if change_to_times < 1 or change_to_times > 20:
        await change_try_limit.finish(
            f"警告! 猜词次数应在 1 ~ 20 范围内."
        )
    config.try_limit = change_to_times
    await changeMinLength.send(f"限制次数已设置为 {config.try_limit}")


@changeMinLength.handle()
async def _(args: Message = CommandArg()):
    global config
    changeToLength = config.length_min
    try:
        changeToLength = int(args.extract_plain_text())
    except TypeError:
        await changeMinLength.finish(f"{args.extract_plain_text()} 不是有效的数字")
    if changeToLength < 2:
        await changeMinLength.send(
            f"错误! 最小单词长度({changeToLength})过小, 已自动更改为 2."
        )
        changeToLength = 2
    if changeToLength > config.length_max:
        await changeMinLength.finish(
            f"警告! 最小单词长度({changeToLength})大于最大单词长度({changeToLength})."
        )
    config.length_min = changeToLength
    await changeMinLength.send(f"最小单词长度已设置为 {config.length_min}")


@changeMaxLength.handle()
async def _(args: Message = CommandArg()):
    global config
    changeToLength = config.length_max
    try:
        changeToLength = int(args.extract_plain_text())
    except TypeError:
        await changeMaxLength.finish(f"{args.extract_plain_text()} 不是有效的数字")
    if changeToLength > 15:
        await changeMaxLength.send(
            f"错误! 最大单词长度({changeToLength})过大, 已自动更改为 15."
        )
    if changeToLength < config.length_min:
        await changeMaxLength.finish(
            f"警告! 最大单词长度({changeToLength})小于最小单词长度({changeToLength})."
        )
    config.length_max = changeToLength
    await changeMaxLength.send(f"最大单词长度已设置为 {config.length_max}")


@commandEnable.handle()
async def _(event: GroupMessageEvent):
    global config
    group_id = str(event.group_id)
    if group_id in config.groups_enabled:
        await commandEnable.finish(f"群聊 {group_id} 已在白名单中")
    config.groups_enabled.add(group_id)
    await commandEnable.send(f"群聊 {group_id} 加入了白名单")


@commandDisable.handle()
async def _(event: GroupMessageEvent):
    global config
    group_id = str(event.group_id)
    if group_id not in config.groups_enabled:
        await commandDisable.finish(f"群聊 {group_id} 不在白名单中")
    config.groups_enabled.remove(group_id)
    await commandDisable.send(f"群聊 {group_id} 退出了白名单")


# 帮助列表
helpDict = {
    "help": "想想你现在在用什么.",
    "rule": "显示规则, 就像你想的那样.",
    "start": f"开始 wordle, 你需要提供一个 {config.length_min}~{config.length_max}之间的数作为单词的长度, bot 会帮你选择单词.",
    "guess": "猜词, 你需要提供正确长度的单词, bot 会告诉你匹配情况.",
    "giveup": "需要 @bot 或私聊 这将直接放弃该局游戏并获取正确答案,慎用!",
    "remain": "显示未使用过的单词,就像你想的那样.",
    "history": "显示历史猜测,按猜测顺序排列.",
}


@wordle.handle()
async def wordleHandle():
    await wordle.send(
        "[Error] bot: Unknown Command\n" + "Press 'wordle.help' to show command list."
    )


# 帮助
@wordle_help.handle()
async def wordleHelp(args: Message = CommandArg()):
    if len(args) == 0:
        # 简要帮助
        res: str = "bot: \n-- Wordle --\n命令列表\n"
        for i in helpDict.keys():
            res += f"  wordle.{i} {helpDict[i]}\n"
        res = res + "注意 此功能可能会造成刷屏"
        await wordle_help.finish(res)
    else:
        # 详细帮助
        command = args.extract_plain_text()
        if command in helpDict.keys():
            await wordle_help.finish("bot: " + helpDict[command])
        else:
            await wordle_help.finish(
                "[Error] bot: Unknown Command; return '请给出正确的参数!'."
            )


# 规则
@rule.handle()
async def wordleRule():
    # await rule.finish("bot: 此功能未完成. bdfs 谢谢!")
    res: str = """bot: 
  -- Wordle --
规则
  你需要使用 /wordle.start <len> 来开始 wordle, 
  你需要提供一个 3~12之间的数作为单词的长度, bot 会帮你选择单词.
  使用 /wordle.guess <word> 来猜词, 你需要提供正确长度的单词, bot 会告诉你匹配情况.
  使用 /wordle.remain 显示未使用过的字母.
  祝您愉快~"""
    await rule.send(res)


# 调试
@debug.handle()
async def wordleDebug(args: Message = CommandArg()):
    global keyWord
    global dictionary
    global trycnt
    global historyGuess
    if not config.debug_enabled:
        await debug.finish("bot: 你想干什么? [恼]")
    text: str = args.extract_plain_text()
    if text == "dictionary":
        cnt: int = 0
        output: str = ""
        for i in dictionary:
            cnt = cnt + 1
            output = output + "\n" + i
            if cnt > 20:
                await debug.send("[Debug] bot: \n -- dictionary --" + output)
                await debug.finish(
                    "[Debug] bot: have more... [All size " + str(len(dictionary)) + "]"
                )
        await debug.send("[Debug] bot: \n -- dictionary --" + output)
        await debug.finish("[Debug] bot: done. [All size " + str(len(dictionary)) + "]")
    if text == "keyword":
        await debug.finish("[Debug] bot: keyWord is " + str(keyWord) + ".")


# 主处理流程
@start.handle()
async def wordleStart(args: Message = CommandArg()):
    global keyWord
    global dictionary
    global trycnt
    global historyGuess
    global historyGuessWord
    global usedChars
    if keyWord != "":
        await start.finish("bot: 当前已有正在进行的 Wordle!")
    text = args.extract_plain_text()
    wordlen: int = 0
    try:
        wordlen = int(text)
        if wordlen < 3:
            await start.finish(
                "[Error] bot: Unexcepted Input; Return '单词长度不应小于3!'."
            )
        if wordlen > 12:
            await start.finish(
                "[Error] bot: Unexcepted Input; Return '单词长度不应大于12!'."
            )
        # await start.send("[Info] bot: Finding Word...")
    except ValueError:
        await start.finish("[Error] bot: ValueError; Return '请给出正确的单词长度!'.")
    # 读取字典
    fdict = open(os.path.split(__file__)[0] + "/AnswerDictionary.txt", "r")
    dictionary = fdict.readlines()
    fdict.close()
    wordlist: list[str] = []
    for i in range(len(dictionary)):
        dictionary[i] = ((dictionary[i].split())[0]).lower()
        if len(dictionary[i]) == wordlen:
            wordlist.append(dictionary[i])
    trycnt = 0
    historyGuessWord = []
    historyGuess = []
    usedChars = set()
    keyWord = wordlist[random.randint(0, len(wordlist))]
    fdict = open(os.path.split(__file__)[0] + "/GuessDictionary.txt", "r")
    dictionary = fdict.readlines()
    fdict.close()
    for i in range(len(dictionary)):
        dictionary[i] = ((dictionary[i].split())[0]).lower()
    await start.send("bot: Word Found")


@guess.handle()
async def wordleGuessPlus(
        bot: Bot,
        event: GroupMessageEvent,
        args: nonebot.adapters.onebot.v11.Message = CommandArg(),
):
    global keyWord
    global dictionary
    global trycnt
    global historyGuess
    global historyGuessWord
    global usedChars
    if keyWord == "":
        await guess.finish("bot: 当前没有正在进行的 Wordle!")
    # await guess.finish("bot: 此功能未完成, 正在咕咕中! [100/100]")
    guessWord = args.extract_plain_text().split()[0].lower()
    if dictionary.count(guessWord) == 0:
        await guess.finish("bot: " + guessWord + " 不是一个单词!")
    if len(guessWord) != len(keyWord):
        await guess.finish("bot: 请输入长度为 " + str(len(keyWord)) + " 的单词!")
    if guessWord in historyGuessWord:
        await guess.finish("bot: 此单词已经尝试过!")
    historyGuessWord.append(guessWord)
    trycnt = trycnt + 1
    if guessWord == keyWord:
        # await guess.send("bot: Game Over!")
        await asyncio.create_task(
            bot.send_group_msg(
                group_id=int(event.get_session_id().split("_")[1]),
                message=f"bot: 游戏结束! \n[CQ:at,qq={str(int(event.get_user_id()))}] 猜到了答案为 {keyWord}.\n你们总共进行了 {str(trycnt)}次猜测.\n翻译:\n{await translate(keyWord)}",
            )
        )
        # await guess.send("bot: 正在清理缓存.")
        keyWord = ""
        trycnt = 0
        historyGuess.clear()
        dictionary = []
        usedChars = set()
        return
        # await guess.finish("bot: 清理结束.")
    matchState: list = [0] * len(keyWord)
    matchCount: list = [0] * 26
    for i in range(len(keyWord)):
        usedChars.add(guessWord[i])
        if guessWord[i] == keyWord[i]:
            matchState[i] = 1
            matchCount[ord(guessWord[i]) - ord("a")] += 1
    for i in range(len(guessWord)):
        if matchState[i] == 1:
            continue
        if matchCount[ord(guessWord[i]) - ord("a")] < keyWord.count(guessWord[i]):
            matchState[i] = 2
            matchCount[ord(guessWord[i]) - ord("a")] += 1
    res: str = ""
    for i in range(len(guessWord)):
        res = res + guessWord[i]
        res = res + "*+?"[matchState[i]]
    historyGuess.append(res)
    if args.extract_plain_text() in ["-p", "--plain"]:
        sendMessage: str = "bot: \n" + "尝试次数: " + str(trycnt)
        for i in historyGuess:
            sendMessage = sendMessage + "\n" + i
    else:
        sendImg: str = wordleOutput(historyGuess)
        sendMessage: str = "[CQ:image,file=base64://" + sendImg + "]"
    await guess.send(nonebot.adapters.onebot.v11.Message(sendMessage))

    if trycnt == config.try_limit:
        await asyncio.create_task(
            guess.send(
                "bot: 很遗憾，没有人猜出来呢 \n答案为 "
                + keyWord
                + "!\n"
                + "你们总共进行了 "
                + str(trycnt)
                + "次猜测."
            )
        )
        keyWord = ""
        trycnt = 0
        historyGuess.clear()
        dictionary = []
        usedChars = set()


@giveup.handle()
async def wordleGiveUp():
    global keyWord
    global dictionary
    global trycnt
    global historyGuess
    if keyWord == "":
        await giveup.finish("bot: 当前没有正在进行的 Wordle!")
    await asyncio.create_task(
        guess.send(
            "bot: 放弃了这局 wordle! \n答案为 "
            + keyWord
            + "!\n"
            + "你们总共进行了 "
            + str(trycnt)
            + "次猜测."
        )
    )
    keyWord = ""
    trycnt = 0
    historyGuess.clear()
    dictionary = []
    # await giveup.finish("bot: 清理结束.")


@remain.handle()
async def wordleRemain():
    global keyWord
    global usedChars
    if keyWord == "":
        await remain.finish("bot: 当前没有正在进行的 Wordle!")
    output: str = "bot: \n 未使用的字母: "
    for i in [chr(x) for x in range(ord("a"), ord("z") + 1) if chr(x) not in usedChars]:
        output = output + i + " "
    await remain.send(output)


@history.handle()
async def wordleHistoryPlus(args: nonebot.adapters.onebot.v11.Message = CommandArg()):
    global keyWord
    global dictionary
    global trycnt
    global historyGuess
    if keyWord == "":
        await remain.finish("bot: 当前没有正在进行的 Wordle!")
    if args.extract_plain_text() in ["-p", "--plain"]:
        sendMessage: str = "bot: \n" + "尝试次数: " + str(trycnt)
        for i in historyGuess:
            sendMessage = sendMessage + "\n" + i
    else:
        sendImg: str = wordleOutput(historyGuess)
        sendMessage: str = "[CQ:image,file=base64://" + sendImg + "]"
    await guess.send(nonebot.adapters.onebot.v11.Message(sendMessage))
