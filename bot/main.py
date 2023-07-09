import discord
import os
from classes.MockInterviewBot import MockInterviewBot


if __name__ == '__main__':
    intents = discord.Intents.default()
    intents.message_content = True
    intents.reactions = True

    bot = MockInterviewBot(intents=intents, command_prefix=os.getenv('PREFIX'))

    bot.run(os.getenv('TOKEN'))


