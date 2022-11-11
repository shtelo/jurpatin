import re
from asyncio import sleep
from math import inf
from sys import argv

from discord import Intents, Interaction, Member, Role
from discord.app_commands import MissingRole
from discord.app_commands.checks import has_role
from discord.ext.commands import Bot, when_mentioned
from pymysql.cursors import DictCursor
from sat_datetime import SatDatetime

from util import get_secret, get_const, database

intents = Intents.default()
intents.members = True

bot = Bot(when_mentioned, intents=intents)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print('Ürpatin is running.')


DECORATED_NICK_RE = re.compile(r'^\d{7} .+$')


@bot.tree.command(
    name='id',
    description='규칙에 따라 로판파샤스 아이디를 부여합니다.'
)
async def id_(ctx: Interaction, member: Member, role: int = 5):
    if not (1 <= role <= 6):
        await ctx.response.send_message(':x: 잘못된 역할 형식입니다.')
        return

    year = SatDatetime.get_from_datetime(member.joined_at.replace(tzinfo=None)).year
    index = 1
    names = tuple(map(lambda x: x.display_name[:7], ctx.guild.members))

    while (candidate := f'{role}{year*10 + index:06d}') in names:
        index += 1

    name = member.display_name if DECORATED_NICK_RE.match(member.display_name) is None else member.display_name[8:]

    await member.edit(nick=f'{candidate} {name}')
    await ctx.response.send_message(f'이름을 변경했습니다.\n> `{member.display_name}` > `{candidate} {name}`')


ROLE_ID_TABLE = (
    get_const('role.harnavin'), get_const('role.erasheniluin'),
    get_const('role.quocerin'), get_const('role.lofanin'), get_const('role.hjulienin')
)


@bot.tree.command(
    name='role',
    description='닉네임에 따라 로판파샤스 역할을 부여합니다.'
)
async def role_(ctx: Interaction, member: Member):
    if (role_number := member.display_name[0]) not in '12345':
        await ctx.response.send_message(f'닉네임이 학번으로 시작하지 않거나 역할 지급 대상이 아닙니다.')
        return

    role_index = int(role_number)-1
    for i in range(role_index):
        await sleep(0)
        role = ctx.guild.get_role(ROLE_ID_TABLE[i])
        if role in member.roles:
            await member.remove_roles(role)
    for i in range(role_index, 5):
        await sleep(0)
        role = ctx.guild.get_role(ROLE_ID_TABLE[i])
        if role not in member.roles:
            await member.add_roles(role)

    await ctx.response.send_message(f'역할을 부여했습니다.')


@bot.tree.command(
    description='역할에 어떤 멤버가 있는지 확인합니다.'
)
async def check_role(ctx: Interaction, role: Role):
    members = list()
    for member in role.members:
        members.append(f'- {member.display_name} ({member})')

    list_string = '> ' + '\n> '.join(sorted(members))

    await ctx.response.send_message(f'{role.name} 역할에 있는 멤버 목록은 다음과 같습니다.\n{list_string}')


async def get_position(ctx: Interaction, term: int, is_lecture: bool = True):
    prefix = '강의' if is_lecture else '스터디'
    position = inf
    index = 0
    for guild_role in sorted(ctx.guild.roles, key=lambda x: x.name):
        await sleep(0)
        if not guild_role.name.startswith(f'{prefix}:'):
            continue
        position = min(guild_role.position, position)

        guild_name = guild_role.name[len(prefix):]
        role_term = int(guild_name[2:4])
        role_index = int(guild_name[4:5])
        if role_term != term:
            continue
        index = max(index, role_index)
    return index, position


@bot.tree.command(
    description='강의를 개설합니다.'
)
@has_role(get_const('role.harnavin'))
async def new_lecture(ctx: Interaction, name: str, term: int, erasheniluin: Member, joinable: bool):
    index, position = await get_position(ctx, term)

    role = await ctx.guild.create_role(
        name=f'강의:1{term:02d}{index+1} ' + name, colour=get_const('color.lecture'), mentionable=True)
    await role.edit(position=position)
    await erasheniluin.add_roles(role)

    with database.cursor(DictCursor) as cursor:
        cursor.execute('INSERT INTO lecture VALUES (%s, %s, %s, %s, %s, %s)',
                       (name, role.id, term, erasheniluin.id, index, joinable))
        database.commit()

    await ctx.response.send_message(f'{role.mention} 강의를 개설했습니다.')


@new_lecture.error
async def new_lecture_error(ctx: Interaction, error: Exception):
    if isinstance(error, MissingRole):
        await ctx.response.send_message(':x: 명령어를 사용하기 위한 권한이 부족합니다!')
        return

    print(error.with_traceback(error.__traceback__))


@bot.tree.command(
    description='스터디를 개설합니다.'
)
@has_role(get_const('role.harnavin'))
async def new_study(ctx: Interaction, name: str, term: int):
    index, position = await get_position(ctx, term, False)

    role = await ctx.guild.create_role(
        name=f'스터디:2{term:02d}{index+1} ' + name, colour=get_const('color.study'), mentionable=True)
    await role.edit(position=position)

    with database.cursor() as cursor:
        cursor.execute('INSERT INTO study VALUES (%s, %s, %s, %s)', (name, role.id, term, index))
        database.commit()

    await ctx.response.send_message(f'{role.mention} 스터디를 개설했습니다.')


@new_study.error
async def new_study_error(ctx: Interaction, error: Exception):
    if isinstance(error, MissingRole):
        await ctx.response.send_message(':x: 명령어를 사용하기 위한 권한이 부족합니다!')
        return

    print(error.with_traceback(error.__traceback__))


if __name__ == '__main__':
    bot.run(get_secret('test_bot_token' if '-t' in argv else 'bot_token'))
