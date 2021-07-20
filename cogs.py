"""
Cogs for the Fake Soccer Bot

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

import inspect

import discord
from discord.ext import commands

from discord_db_client import Bot
from listener import DEFENSIVE_MESSAGE


class Teams(commands.Cog):
    """Gives information about teams from the database, and also allows bot operators to create and delete teams."""
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name='teaminfo')
    async def team_info(self, ctx, team_id: str):
        """Gives info about a certain team."""
        team_id = team_id.lower()
        query = 'SELECT * FROM teams WHERE teamid = $1'
        team = await self.bot.db.fetchrow(query, team_id)
        try:
            c = discord.Color(int(team['color'], 16))
        except TypeError:
            return await ctx.reply(f'Error: Team not found. Run {self.bot.command_prefix}teamlist to find a list of teams.')
        manager = self.bot.get_user(team['manager'])
        embed = discord.Embed(title=f'{team["teamname"]} Team Info', color=c)
        embed.add_field(name='Name', value=team['teamname'])
        embed.add_field(name='Team ID', value=team['teamid'])
        embed.add_field(name='Manager', value=manager.mention)
        await ctx.reply(embed=embed)

    @commands.command(name='teamlist', aliases=['listteams', 'teamids', 'listteamids'])
    async def team_list(self, ctx, page_number: int = 1):
        """Lists all teams and their IDs."""
        # TODO: Add regex search for team_list by teamid
        teams = await self.bot.db.fetch(f'SELECT teamname, teamid FROM teams ORDER BY teamid ASC LIMIT 10 OFFSET {(page_number-1)*10}')
        if len(teams) == 0:
            return await ctx.reply('Error: Page number out of range.')
        desc_string = '```\n'
        for team in teams:
            desc_string += f'{team["teamid"].upper()}: {team["teamname"]}\n'
        desc_string += '```'
        c = discord.Color(0x000000)
        embed = discord.Embed(title='Team IDs', description=desc_string, color=c)
        embed.set_footer(text=f'Page {page_number}')
        await ctx.reply(embed=embed)

    @commands.command(name='createteam')
    @commands.has_role('bot operator')
    async def create_team(self, ctx, member: discord.Member, color: str, team_id: str, *, team_name: str):
        """Creates a new team and adds it to the database."""
        team_id = team_id.lower()
        if len(team_id) > 5:
            return await ctx.send('Error: Team ID too long.')
        query = 'INSERT INTO teams(teamid, teamname, manager, color) VALUES ($1, $2, $3, $4)'
        await self.bot.write(query, team_id, team_name, member.id, color)
        color = discord.Color(int(color, 16))
        new_role = await ctx.guild.create_role(name=team_name)
        await new_role.edit(color=color)
        await member.add_roles(new_role)
        await ctx.reply(f'Success: New team {team_name} with manager {member} has been created.')

    @commands.command(name='deleteteam', aliases=['removeteam'])
    @commands.has_role('bot operator')
    async def remove_team(self, ctx, member: discord.Member):
        """Deletes a team from the database."""
        # TODO: Automatically abandon games when the team is deleted.
        userteam = await self.bot.db.fetch('SELECT teamname FROM teams WHERE manager = $1', member.id)
        await self.bot.write('DELETE FROM teams WHERE manager = $1', member.id)
        for team in userteam:
            role = (discord.utils.get(ctx.guild.roles, name=team['teamname']))
            await role.delete()
        await ctx.reply(f'Success: Team belonging to user {member} has been deleted.')


class GameManagement(commands.Cog, name='Game Management'):
    """Allows bot operators to start and abandon games."""
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name='startgame', aliases=['startmatch'])
    @commands.has_role('bot operator')
    async def start_game(self, ctx, hometeam: str, awayteam: str):
        hometeam, awayteam = hometeam.lower(), awayteam.lower()

        if hometeam == awayteam:
            return await ctx.reply('Error: Cannot start game with same two teams.')

        home_team_exists = await self.bot.db.fetchval('SELECT EXISTS(SELECT 1 FROM teams WHERE teamid = $1)', hometeam)
        away_team_exists = await self.bot.db.fetchval('SELECT EXISTS(SELECT 1 FROM teams WHERE teamid = $1)', awayteam)

        if home_team_exists and away_team_exists:
            games_category = discord.utils.get(ctx.guild.categories, name='Game Threads')
            channel = await ctx.guild.create_text_channel(f'{hometeam}-{awayteam}', category=games_category)

            home_team_name = await self.bot.db.fetchval('SELECT teamname FROM teams WHERE teamid = $1', hometeam)
            away_team = await self.bot.db.fetchrow('SELECT teamname, manager FROM teams WHERE teamid = $1', awayteam)

            home_role = discord.utils.get(ctx.guild.roles, name=home_team_name)
            away_role = discord.utils.get(ctx.guild.roles, name=away_team['teamname'])

            query = "INSERT INTO games(hometeam, awayteam, channelid, homeroleid, awayroleid, deadline) VALUES ($1, $2, $3, $4, $5, 'now'::timestamp + INTERVAL '1 day')"
            await self.bot.write(query, hometeam, awayteam, channel.id, home_role.id, away_role.id)

            gameid = await self.bot.db.fetchval(f"SELECT gameid FROM games WHERE hometeam = '{hometeam}' AND awayteam = '{awayteam}'")
            listener_cog = self.bot.get_cog('Listener')
            listener_cog.defcache[channel.id] = (gameid, hometeam, awayteam, 'AWAY')

            message = await channel.send('https://cdn.discordapp.com/attachments/843971721697427519/856397192573747200/image0.png')
            await message.pin()
            await channel.send(f'Game has started between {home_role.mention} and {away_role.mention}\n\n'
                               f'{home_role.mention} gets the ball first.\n\n'
                               f'{hometeam.upper()} 0-0 {awayteam.upper()} '
                               f'0:00\n\n'
                               f'Waiting on {away_role.mention} for defensive number')
            away_manager = self.bot.get_user(away_team['manager'])
            await away_manager.send(DEFENSIVE_MESSAGE.format(hometeam=hometeam.upper(),
                                                             awayteam=awayteam.upper(),
                                                             homescore='0',
                                                             awayscore='0',
                                                             game_time='0:00'))
            return await ctx.reply(f'Game successfully started in {channel.mention}.')
        else:
            return await ctx.reply(f'Error: One or both of your teams does not exist. Run command {self.bot.command_prefix}teamlist for a list of teams.')

    @commands.command(name='startgameovertime', aliases=['startmatchovertime', 'startot'])
    @commands.has_role('bot operator')
    async def start_game_overtime(self, ctx, hometeam: str, awayteam: str):
        hometeam, awayteam = hometeam.lower(), awayteam.lower()

        if hometeam == awayteam:
            return await ctx.reply('Error: Cannot start game with same two teams.')

        home_team_exists = await self.bot.db.fetchval('SELECT EXISTS(SELECT 1 FROM teams WHERE teamid = $1)', hometeam)
        away_team_exists = await self.bot.db.fetchval('SELECT EXISTS(SELECT 1 FROM teams WHERE teamid = $1)', awayteam)

        if home_team_exists and away_team_exists:
            games_category = discord.utils.get(ctx.guild.categories, name='Game Threads')
            channel = await ctx.guild.create_text_channel(f'{hometeam}-{awayteam}', category=games_category)

            home_team_name = await self.bot.db.fetchval('SELECT teamname FROM teams WHERE teamid = $1', hometeam)
            away_team = await self.bot.db.fetchrow('SELECT teamname, manager FROM teams WHERE teamid = $1', awayteam)

            home_role = discord.utils.get(ctx.guild.roles, name=home_team_name)
            away_role = discord.utils.get(ctx.guild.roles, name=away_team['teamname'])

            query = "INSERT INTO games(hometeam, awayteam, channelid, homeroleid, awayroleid, deadline, overtimegame) VALUES ($1, $2, $3, $4, $5, 'now'::timestamp + INTERVAL '1 day', t)"
            await self.bot.write(query, hometeam, awayteam, channel.id, home_role.id, away_role.id)

            gameid = await self.bot.db.fetchval(
                f"SELECT gameid FROM games WHERE hometeam = '{hometeam}' AND awayteam = '{awayteam}'")
            listener_cog = self.bot.get_cog('Listener')
            listener_cog.defcache[channel.id] = (gameid, hometeam, awayteam, 'AWAY')

            message = await channel.send(
                'https://cdn.discordapp.com/attachments/843971721697427519/856397192573747200/image0.png')
            await message.pin()
            await channel.send(f'Game has started between {home_role.mention} and {away_role.mention}\n\n'
                               f'{home_role.mention} gets the ball first.\n\n'
                               f'{hometeam.upper()} 0-0 {awayteam.upper()} '
                               f'0:00\n\n'
                               f'Waiting on {away_role.mention} for defensive number')
            away_manager = self.bot.get_user(away_team['manager'])
            await away_manager.send(DEFENSIVE_MESSAGE.format(hometeam=hometeam.upper(),
                                                             awayteam=awayteam.upper(),
                                                             homescore='0',
                                                             awayscore='0',
                                                             game_time='0:00'))
            return await ctx.reply(f'Game successfully started in {channel.mention}.')
        else:
            return await ctx.reply(
                f'Error: One or both of your teams does not exist. Run command {self.bot.command_prefix}teamlist for a list of teams.')

    @commands.command(name='abandongame', aliases=['stopgame', 'endgame'])
    @commands.has_role('bot operator')
    async def abandon_game(self, ctx):
        game = await self.bot.db.fetchrow(f'SELECT homeroleid, awayroleid, homescore, awayscore FROM games WHERE channelid = {ctx.channel.id}')
        try:
            home_role = discord.utils.get(ctx.guild.roles, id=game['homeroleid'])
            away_role = discord.utils.get(ctx.guild.roles, id=game['awayroleid'])
        except TypeError:
            return await ctx.send('Error: Channel does not appear to be game channel.')
        await self.bot.write(f"UPDATE games SET gamestate = 'ABANDONED' WHERE channelid = {ctx.channel.id}")
        scores_channel = discord.utils.get(ctx.guild.channels, name='scores')
        await scores_channel.send(f'GAME ABANDONED: {home_role.mention} {game["homescore"]}-{game["awayscore"]} {away_role.mention}')
        await ctx.reply('Game Abandoned. You may delete this channel at any time.')


class Eval(commands.Cog):
    """Eval class"""
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def eval(self, ctx, *, arg: str):
        """Evaluate string"""
        result = eval(arg)
        if inspect.isawaitable(result):
            embed = discord.Embed(title='Eval', description=f'```\n{await result}\n```', color=discord.Color(0x000000))
        else:
            embed = discord.Embed(title='Eval', description=f'```\n{result}\n```', color=discord.Color(0x000000))
        await ctx.reply(embed=embed)


def setup(bot: Bot):
    bot.add_cog(Teams(bot))
    bot.add_cog(GameManagement(bot))
    bot.add_cog(Eval(bot))
