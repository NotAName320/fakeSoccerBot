"""
Bot to simulate a soccer game using the principles of number guessing

Copyright (c) 2021 NotAName

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import asyncio
import json
import logging
import sys
import traceback

import asyncpg
import discord
from discord.ext import commands

from discord_db_client import Bot


async def login():
    """Logs into Discord and PostgreSQL and runs the bot."""
    # Sets up logging
    logger = logging.getLogger('discord')
    logger.setLevel(logging.WARNING)
    handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    # Opens credentials.json and extracts bot token
    with open('credentials.json', 'r') as credentials_file:
        credentials = json.load(credentials_file)
    token = credentials['discord_token']

    # Initializes some configuration objects
    activity = discord.Activity(type=discord.ActivityType.watching, name='your soccer games!')
    intents = discord.Intents.default()
    intents.members = True
    db = await asyncpg.create_pool(**credentials['postgresql_creds'])

    # Initializes bot object
    client = Bot(command_prefix='!', activity=activity, help_command=commands.MinimalHelpCommand(), intents=intents, db=db)

    @client.event
    async def on_ready():
        # Prints login success and bot info to console
        print('Logged in as')
        print(client.user)
        print(client.user.id)

    @client.event
    async def on_error(event, *args):
        """Prints out on_message listener errors to a logging channel."""
        print(f'Ignoring exception in {event}:', file=sys.stderr)
        exception = traceback.format_exc()
        print(exception, file=sys.stderr)
        if event == 'on_message':
            message: discord.Message = args[0]
            log_channel = discord.utils.get(message.guild.channels, name='logs')
            errordesc = f'```py\n' \
                        f'{exception}\n' \
                        f'```'
            embed = discord.Embed(title='Error', description=errordesc, color=discord.Color(0x000000))
            await log_channel.send(content=f"Game error in channel {message.channel.mention}", embed=embed)

    @client.event
    async def on_command_error(ctx, error):
        # Basic error handling, including generic messages to send for common errors
        error: Exception = getattr(error, 'original', error)

        if isinstance(error, commands.CommandNotFound):
            notFoundMessage = f"Your command was not recognized. Please refer to {client.command_prefix}help for more info."
            await ctx.send(notFoundMessage)

        elif isinstance(error, commands.MissingRequiredArgument):
            missingMessage = "Error: you did not provide the required argument(s). Make sure you typed the command correctly."
            await ctx.send(missingMessage)

        elif isinstance(error, commands.CheckFailure):
            checkFailedMessage = "Error: you do not have permissions to use this command."
            await ctx.send(checkFailedMessage)

        else:
            logger.error(traceback.format_exception(type(error), error, tb=error.__traceback__))
            print(f'Exception in command {ctx.command}:', file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            errordesc = f'```py\n' \
                        f'{"".join(traceback.format_exception(type(error), error, tb=error.__traceback__))}\n' \
                        f'```'
            embed = discord.Embed(title='Error', description=errordesc, color=discord.Color(0x000000))
            embed.set_footer(text='Please contact NotAName#0591 for help.')
            await ctx.send(embed=embed)

    # Adds cogs and runs bot
    client.load_extension('cogs')
    client.load_extension('listener')
    try:
        await client.start(token)
    except KeyboardInterrupt:
        await db.close()
        await client.logout()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(login())
