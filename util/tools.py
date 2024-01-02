from discord import Interaction, Reaction, User


def check_reaction(emojis: list[str], ctx: Interaction, message_id: int):
    def checker(reaction: Reaction, user: User):
        return user.id == ctx.user.id and str(reaction.emoji) in emojis and reaction.message.id == message_id

    return checker


def custom_emoji(emoji_name: str, emoji_id: int):
    return f'<:{emoji_name}:{emoji_id}>'


def generate_tax_message(amount: int):
    """
    returns autogenerated tax message.
    this contains space character at the end of the string, if any.
    """
    if amount:
        return f'(이 중에서 세금으로 __{amount / 100:,.2f} Ł__를 자동 납부함) '
    else:
        return ''