import re
from asyncio import sleep, wait, TimeoutError as AsyncioTimeoutError
from math import inf

from discord import Member, Guild, Interaction, Reaction, InteractionMessage, Role
from discord.app_commands import command, MissingRole
from discord.app_commands.checks import has_role
from discord.ext.commands import Cog, Bot
from sat_datetime import SatDatetime

from util import get_const, eul_reul, check_reaction

DECORATED_NICK_RE = re.compile(r'^\d{7} .+$')
ROLE_ID_TABLE = (
    get_const('role.harnavin'), get_const('role.erasheniluin'), get_const('role.quocerin'), get_const('role.lofanin'),
    get_const('role.hjulienin'))
OX_EMOJIS = [get_const('emoji.x'), get_const('emoji.o')]


def get_proper_id(member: Member, role: int, guild: Guild) -> str:
    year = SatDatetime.get_from_datetime(member.joined_at.replace(tzinfo=None)).year
    index = 1
    names = tuple(map(lambda x: x.display_name[:7], guild.members))

    while (candidate := f'{role}{year * 10 + index:06d}') in names:
        index += 1

    return candidate


async def assign_role(member: Member, role_number: str, guild: Guild):
    role_index = int(role_number) - 1
    for i in range(role_index):
        await sleep(0)
        role = guild.get_role(ROLE_ID_TABLE[i])
        if role in member.roles:
            await member.remove_roles(role)
    for i in range(role_index, 5):
        await sleep(0)
        role = guild.get_role(ROLE_ID_TABLE[i])
        if role not in member.roles:
            await member.add_roles(role)


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


def parse_role_name(name: str) -> tuple[bool, int, int, str]:
    """
    출력 값으로는 tuple[bool, int, int, str] 형태의 값을 출력합니다.

    첫 번째 요소가 True이면 role이 강의라는 의미이고, False이면 스터디라는 의미입니다.
    두 번째 요소는 기수, 세 번째 요소는 인덱스 번호입니다.
    마지막 요소는 강의/스터디의 이름입니다.
    """

    if name.startswith('스터디:'):
        name = name[4:]
    elif name.startswith('강의:'):
        name = name[3:]
    else:
        raise ValueError

    is_lecture = name[0] == '1'
    term = int(name[1:3])
    index = int(name[3:4])
    title = name[5:]

    return is_lecture, term, index, title


class AdminCog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        print('Ürpatin is running.')

    @Cog.listener()
    async def on_member_join(self, member: Member):
        if member.guild.id != get_const('guild.lofanfashasch'):
            return

        candidate = get_proper_id(member, 5, member.guild)
        name = member.display_name if DECORATED_NICK_RE.match(member.display_name) is None else member.display_name[8:]
        nick = f'{candidate} {name}'
        await member.edit(nick=nick)
        await assign_role(member, nick[0], member.guild)

    @command(name='id', description='규칙에 따라 로판파샤스 아이디를 부여합니다.')
    async def id_(self, ctx: Interaction, member: Member, role: int = 5):
        if not (1 <= role <= 6):
            await ctx.response.send_message(':x: 잘못된 역할 형식입니다.')
            return

        candidate = get_proper_id(member, role, ctx.guild)

        name = member.display_name if DECORATED_NICK_RE.match(member.display_name) is None else member.display_name[8:]
        post_name = f'{candidate} {name}'

        await ctx.response.send_message(
            f'현재 이름은 `{member.display_name}`이고, 이름을 변경하면 `{post_name}`으로 변경됩니다.\n이름을 변경하시겠습니까?')
        message: InteractionMessage = await ctx.original_response()
        await wait((message.add_reaction(get_const('emoji.x')), message.add_reaction(get_const('emoji.o'))))

        try:
            res: tuple[Reaction, Member] = await self.bot.wait_for(
                'reaction_add',
                timeout=60.0,
                check=check_reaction(OX_EMOJIS, ctx, message.id))
            await message.clear_reactions()
        except AsyncioTimeoutError:
            await message.edit(content=f':x: 시간이 초과되어 작업이 취소되었습니다.')
            return

        if res[0].emoji == get_const('emoji.x'):
            await message.edit(content=f':x: 사용자가 작업을 취소하였습니다.')
            return

        await member.edit(nick=post_name)
        await message.edit(content=f'이름을 변경했습니다.\n> `{member.display_name}` > `{post_name}`')

    @command(name='role', description='닉네임에 따라 로판파샤스 역할을 부여합니다.')
    async def role_(self, ctx: Interaction, member: Member):
        if (role_number := member.display_name[0]) not in '12345':
            await ctx.response.send_message(f'닉네임이 학번으로 시작하지 않거나 역할 지급 대상이 아닙니다.')
            return

        await assign_role(member, role_number, ctx.guild)
        await ctx.response.send_message(f'역할을 부여했습니다.')

    @command(description='역할에 어떤 멤버가 있는지 확인합니다.')
    async def check_role(self, ctx: Interaction, role: Role, ephemeral: bool = True):
        members = list()
        last_member_number = ''
        last_index = 0
        for member in sorted(role.members, key=lambda x: x.display_name):
            if last_member_number != (last_member_number := member.display_name[:7]):
                last_index += 1
            members.append(f'{last_index}. `{member.display_name}` ({member})')

        list_string = '> ' + '\n> '.join(members)

        await ctx.response.send_message(
            f'{role.name} 역할에 있는 멤버 목록은 다음과 같습니다. (총 {last_index}명, 계정 {len(members)}개)'
            f'\n{list_string}', ephemeral=ephemeral)

    @command(description='강의를 개설합니다.')
    @has_role(get_const('role.harnavin'))
    async def new_lecture(self, ctx: Interaction, name: str, term: int, erasheniluin: Member):
        # noinspection DuplicatedCode
        await ctx.response.send_message(
            f'이름이 `{name}`인 {term}기 강의를 개설합니다. 이 작업을 취소하는 기능은 지원되지 않습니다. 동의하십니까?')
        message = await ctx.original_response()
        await wait((message.add_reaction(get_const('emoji.x')), message.add_reaction(get_const('emoji.o'))))

        try:
            res: tuple[Reaction, Member] = await self.bot.wait_for(
                'reaction_add', check=check_reaction(OX_EMOJIS, ctx, message.id))
            await message.clear_reactions()
        except AsyncioTimeoutError:
            await message.edit(content=':x: 시간이 초과되어 작업이 취소되었습니다.')
            return

        if res[0].emoji == get_const('emoji.x'):
            await message.edit(content=':x: 사용자가 작업을 취소하였습니다.')
            return

        index, position = await get_position(ctx, term)

        role = await ctx.guild.create_role(
            name=f'강의:1{term:02d}{index + 1} ' + name, colour=get_const('color.lecture'),
            mentionable=True)
        await role.edit(position=position)
        await erasheniluin.add_roles(role)

        await message.edit(content=f'{role.mention} 강의를 개설했습니다.')

    @new_lecture.error
    async def new_lecture_error(self, ctx: Interaction, error: Exception):
        if isinstance(error, MissingRole):
            await ctx.response.send_message(':x: 명령어를 사용하기 위한 권한이 부족합니다!')
            return

    @command(description='스터디를 개설합니다.')
    @has_role(get_const('role.harnavin'))
    async def new_study(self, ctx: Interaction, name: str, term: int):
        # noinspection DuplicatedCode
        await ctx.response.send_message(
            f'이름이 `{name}`인 {term}기 스터디를 개설합니다. 이 작업을 취소하는 기능은 지원되지 않습니다. 동의하십니까?')
        message = await ctx.original_response()
        await wait((message.add_reaction(get_const('emoji.x')), message.add_reaction(get_const('emoji.o'))))

        try:
            res: tuple[Reaction, Member] = await self.bot.wait_for(
                'reaction_add', check=check_reaction(OX_EMOJIS, ctx, message.id))
            await message.clear_reactions()
        except AsyncioTimeoutError:
            await message.edit(content=':x: 시간이 초과되어 작업이 취소되었습니다.')
            return

        if res[0].emoji == get_const('emoji.x'):
            await message.edit(content=':x: 사용자가 작업을 취소하였습니다.')
            return

        index, position = await get_position(ctx, term, False)

        role = await ctx.guild.create_role(
            name=f'스터디:2{term:02d}{index + 1} ' + name, colour=get_const('color.study'),
            mentionable=True)
        await role.edit(position=position)

        await message.edit(content=f'{role.mention} 스터디를 개설했습니다.')

    @new_study.error
    async def new_study_error(self, ctx: Interaction, error: Exception):
        if isinstance(error, MissingRole):
            await ctx.response.send_message(':x: 명령어를 사용하기 위한 권한이 부족합니다!')
            return

    @command(description='강의 목록을 확인합니다.')
    async def lectures(self, ctx: Interaction, term: int):
        if term <= 0:
            await ctx.response.send_message(f':x: 기수는 1 이상으로 입력해야 합니다.', ephemeral=True)
            return

        lines = list()
        for role in ctx.guild.roles:
            try:
                is_lecture, role_term, index, title = parse_role_name(role.name)
            except ValueError:
                continue

            if not is_lecture:
                continue
            if role_term != term:
                continue

            lines.append(role.name)

        list_string = '> ' + '\n> '.join(lines[::-1])

        if not lines:
            await ctx.response.send_message(f'{term}기에는 (아직) 강의가 없습니다!', ephemeral=True)
            return

        await ctx.response.send_message(f'{term}기의 강의 목록은 다음과 같습니다.\n{list_string}', ephemeral=True)

    @command(description='스터디 목록을 확인합니다.')
    async def studies(self, ctx: Interaction, term: int):
        if term <= 0:
            await ctx.response.send_message(f':x: 기수는 1 이상으로 입력해야 합니다.', ephemeral=True)
            return

        lines = list()
        for role in ctx.guild.roles:
            try:
                is_lecture, role_term, index, title = parse_role_name(role.name)
            except ValueError:
                continue

            if is_lecture:
                continue
            if role_term != term:
                continue

            lines.append(role.name)

        list_string = '> ' + '\n> '.join(lines[::-1])

        if not lines:
            await ctx.response.send_message(f'{term}기에는 (아직) 스터디가 없습니다!', ephemeral=True)
            return

        await ctx.response.send_message(f'{term}기의 스터디 목록은 다음과 같습니다.\n{list_string}', ephemeral=True)

    @command(description='역할을 부여합니다.')
    async def give_role(self, ctx: Interaction, role: Role):
        await ctx.user.add_roles(role)
        await ctx.response.send_message(f'{ctx.user.mention}에게 {role}{eul_reul(role.name)} 부여했습니다.', ephemeral=True)

    @command(description='역할을 제거합니다.')
    async def remove_role(self, ctx: Interaction, role: Role):
        await ctx.user.remove_roles(role)
        await ctx.response.send_message(f'{ctx.user.mention}에게서 {role}{eul_reul(role.name)} 제거했습니다.', ephemeral=True)


async def setup(bot: Bot):
    await bot.add_cog(AdminCog(bot))
