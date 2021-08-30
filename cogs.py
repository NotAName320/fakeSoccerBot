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

import utils
from discord_db_client import Bot
from listener import DEFENSIVE_MESSAGE

RANGES_IMAGE_URL = 'https://media.discordapp.net/attachments/867112465673355285/876654939873636372/unknown.png'


class Teams(commands.Cog):
    """Gives information about teams from the database, and also allows bot operators to create and delete teams."""
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name='teaminfo')
    async def team_info(self, ctx, team_id: str):
        """Gives info about a certain team."""
        team_id = team_id.lower()
        team = await self.bot.db.fetchrow('SELECT * FROM teams WHERE teamid = $1', team_id)
        try:
            c = discord.Color(int(team['color'], 16))
        except TypeError:
            return await ctx.reply(f'Error: Team not found. Run {self.bot.command_prefix}teamlist to find a list of teams.')
        manager = self.bot.get_user(team['manager'])
        embed = discord.Embed(title=f'{team["teamname"]} Team Info', color=c)
        embed.add_field(name='Name', value=team['teamname'])
        embed.add_field(name='Team ID', value=team['teamid'])
        embed.add_field(name='Manager', value=manager.mention)
        embed.add_field(name='Substitute', value='*None*' if team['substitute'] is None else self.bot.get_user(team['substitute']).mention)
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

    @commands.command(name='createteam', aliases=['addteam'])
    @commands.has_role('bot operator')
    async def create_team(self, ctx, member: discord.Member, color: str, team_id: str, *, team_name: str):
        """Creates a new team and adds it to the database."""
        team_id = team_id.lower()
        if len(team_id) > 5:
            return await ctx.reply('Error: Team ID too long.')
        query = 'INSERT INTO teams(teamid, teamname, manager, color) VALUES ($1, $2, $3, $4)'
        await self.bot.write(query, team_id, team_name, member.id, color)
        color = discord.Color(int(color, 16))
        new_role = await ctx.guild.create_role(name=team_name)
        await new_role.edit(color=color)
        await member.add_roles(new_role)
        await ctx.reply(f'Success: New team {team_name} with manager {member} has been created.')

    @commands.command(name='removeteam', aliases=['deleteteam', 'delteam'])
    @commands.has_role('bot operator')
    async def remove_team(self, ctx, teamid: str):
        """Deletes a team from the database."""
        # TODO: Automatically abandon games when the team is deleted.
        userteam = await self.bot.db.fetchval('SELECT teamname FROM teams WHERE teamid = $1', teamid)
        await self.bot.write('DELETE FROM teams WHERE teamid = $1', teamid)
        role = (discord.utils.get(ctx.guild.roles, name=userteam))
        await role.delete()
        await ctx.reply(f'Success: Team {userteam} has been deleted.')

    @commands.command(name='addsubstitute', aliases=['addsub'])
    @commands.has_role('bot operator')
    async def add_substitute(self, ctx, team_id: str, user: discord.Member):
        """Adds a substitute for a team."""
        team_id = team_id.lower()
        team = await self.bot.db.fetchrow('SELECT teamname, manager, substitute FROM teams WHERE teamid = $1', team_id)
        if team is not None:
            await self.bot.write(f"UPDATE teams SET substitute = {user.id} WHERE teamid = '{team_id}'")
            team_role = discord.utils.get(ctx.guild.roles, name=team['teamname'])
            existing_coach = discord.utils.get(ctx.guild.members, id=team['manager'])
            await existing_coach.remove_roles(team_role)
            if team['substitute'] is not None:
                existing_sub = discord.utils.get(ctx.guild.members, id=team['substitute'])
                await existing_sub.remove_roles(team_role)
            await user.add_roles(team_role)
            await ctx.reply(f"{user.mention} you are now substitute manager of {team_role.mention}. Please give the bot at most a minute to refresh their cache.")
        else:
            return await ctx.reply("Error: Team not found.")

    @commands.command(name='removesubstitute', aliases=['removesub', 'delsubstitute', 'delsub'])
    @commands.has_role('bot operator')
    async def remove_substitute(self, ctx, team_id: str):
        """Removes a substitute (if there is any) and their team role, and reinstates the official manager."""
        team_id = team_id.lower()
        team = await self.bot.db.fetchrow('SELECT teamname, manager, substitute FROM teams WHERE teamid = $1', team_id)
        if team is not None:
            await self.bot.write(f"UPDATE teams SET substitute = NULL WHERE teamid = '{team_id}'")
            team_role = discord.utils.get(ctx.guild.roles, name=team['teamname'])
            existing_coach = discord.utils.get(ctx.guild.members, id=team['manager'])
            await existing_coach.add_roles(team_role)
            if team['substitute'] is not None:
                existing_sub = discord.utils.get(ctx.guild.members, id=team['substitute'])
                await existing_sub.remove_roles(team_role)
            await ctx.reply(f"Substitute for team {team_role.mention} has been removed.")
        else:
            return await ctx.reply("Error: Team not found.")


class GameManagement(commands.Cog, name='Game Management'):
    """Allows bot operators to start, abandon, and rerun games."""
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name='startgame', aliases=['startmatch'])
    @commands.has_role('bot operator')
    async def start_game(self, ctx, hometeam: str, awayteam: str):
        """Starts a game between two teams from the database."""
        hometeam, awayteam = hometeam.lower(), awayteam.lower()

        if hometeam == awayteam:
            return await ctx.reply('Error: Cannot start game with same two teams.')

        home_team_exists = await self.bot.db.fetchval('SELECT EXISTS(SELECT 1 FROM teams WHERE teamid = $1)', hometeam)
        away_team_exists = await self.bot.db.fetchval('SELECT EXISTS(SELECT 1 FROM teams WHERE teamid = $1)', awayteam)

        if home_team_exists and away_team_exists:
            games_category = discord.utils.get(ctx.guild.categories, name='Game Threads')
            channel = await ctx.guild.create_text_channel(f'{hometeam}-{awayteam}', category=games_category)

            home_team_name = await self.bot.db.fetchval('SELECT teamname FROM teams WHERE teamid = $1', hometeam)
            away_team_name = await self.bot.db.fetchval('SELECT teamname FROM teams WHERE teamid = $1', awayteam)

            home_role = discord.utils.get(ctx.guild.roles, name=home_team_name)
            away_role = discord.utils.get(ctx.guild.roles, name=away_team_name)

            query = "INSERT INTO games(hometeam, awayteam, channelid, homeroleid, awayroleid, deadline) VALUES ($1, $2, $3, $4, $5, 'now'::timestamp + INTERVAL '1 day')"
            await self.bot.write(query, hometeam, awayteam, channel.id, home_role.id, away_role.id)

            gameid = await self.bot.db.fetchval(f"SELECT gameid FROM games WHERE hometeam = '{hometeam}' AND awayteam = '{awayteam}' ORDER BY gameid DESC")
            listener_cog = self.bot.get_cog('Listener')
            listener_cog.offcache[channel.id] = (gameid, hometeam, awayteam, 'AWAY', channel.id)

            message = await channel.send(RANGES_IMAGE_URL)
            await message.pin()
            await channel.send(f'Game has started between {home_role.mention} and {away_role.mention}\n\n'
                               f'{hometeam.upper()} 0-0 {awayteam.upper()} '
                               f'0:00\n\n'
                               f'{away_role.mention}, please call **heads** or **tails**.')
            return await ctx.reply(f'Game successfully started in {channel.mention}.')
        else:
            return await ctx.reply(f'Error: One or both of your teams does not exist. Run command {self.bot.command_prefix}teamlist for a list of teams.')

    @commands.command(name='startscrim')
    @commands.has_role('bot operator')
    async def start_scrim(self, ctx, hometeam: str, awayteam: str):
        """Starts a scrimmage between two teams from the database."""
        hometeam, awayteam = hometeam.lower(), awayteam.lower()

        if hometeam == awayteam:
            return await ctx.reply('Error: Cannot start game with same two teams.')

        home_team_exists = await self.bot.db.fetchval('SELECT EXISTS(SELECT 1 FROM teams WHERE teamid = $1)', hometeam)
        away_team_exists = await self.bot.db.fetchval('SELECT EXISTS(SELECT 1 FROM teams WHERE teamid = $1)', awayteam)

        if home_team_exists and away_team_exists:
            games_category = discord.utils.get(ctx.guild.categories, name='scrimmages')
            channel = await ctx.guild.create_text_channel(f'{hometeam}-{awayteam}-scrim', category=games_category)

            home_team_name = await self.bot.db.fetchval('SELECT teamname FROM teams WHERE teamid = $1', hometeam)
            away_team_name = await self.bot.db.fetchval('SELECT teamname FROM teams WHERE teamid = $1', awayteam)

            home_role = discord.utils.get(ctx.guild.roles, name=home_team_name)
            away_role = discord.utils.get(ctx.guild.roles, name=away_team_name)

            query = "INSERT INTO games(hometeam, awayteam, channelid, homeroleid, awayroleid, deadline, isscrimmage) VALUES ($1, $2, $3, $4, $5, 'now'::timestamp + INTERVAL '1 day', true)"
            await self.bot.write(query, hometeam, awayteam, channel.id, home_role.id, away_role.id)

            gameid = await self.bot.db.fetchval(
                f"SELECT gameid FROM games WHERE hometeam = '{hometeam}' AND awayteam = '{awayteam}' ORDER BY gameid DESC")
            listener_cog = self.bot.get_cog('Listener')
            listener_cog.offcache[channel.id] = (gameid, hometeam, awayteam, 'AWAY', channel.id)

            message = await channel.send(RANGES_IMAGE_URL)
            await message.pin()
            await channel.send(f'Game has started between {home_role.mention} and {away_role.mention}\n\n'
                               f'{hometeam.upper()} 0-0 {awayteam.upper()} '
                               f'0:00\n\n'
                               f'{away_role.mention}, please call **heads** or **tails**.')
            return await ctx.reply(f'Scrimmage successfully started in {channel.mention}.')
        else:
            return await ctx.reply(
                f'Error: One or both of your teams does not exist. Run command {self.bot.command_prefix}teamlist for a list of teams.')

    @commands.command(name='startgameovertime', aliases=['startmatchovertime', 'startot'])
    @commands.has_role('bot operator')
    async def start_game_overtime(self, ctx, hometeam: str, awayteam: str):
        """Start a game with overtime rules using two teams from the database."""
        hometeam, awayteam = hometeam.lower(), awayteam.lower()

        if hometeam == awayteam:
            return await ctx.reply('Error: Cannot start game with same two teams.')

        home_team_exists = await self.bot.db.fetchval('SELECT EXISTS(SELECT 1 FROM teams WHERE teamid = $1)', hometeam)
        away_team_exists = await self.bot.db.fetchval('SELECT EXISTS(SELECT 1 FROM teams WHERE teamid = $1)', awayteam)

        if home_team_exists and away_team_exists:
            games_category = discord.utils.get(ctx.guild.categories, name='Game Threads')
            channel = await ctx.guild.create_text_channel(f'{hometeam}-{awayteam}', category=games_category)

            home_team_name = await self.bot.db.fetchval('SELECT teamname FROM teams WHERE teamid = $1', hometeam)
            away_team_name = await self.bot.db.fetchval('SELECT teamname FROM teams WHERE teamid = $1', awayteam)

            home_role = discord.utils.get(ctx.guild.roles, name=home_team_name)
            away_role = discord.utils.get(ctx.guild.roles, name=away_team_name)

            query = "INSERT INTO games(hometeam, awayteam, channelid, homeroleid, awayroleid, deadline, overtimegame) VALUES ($1, $2, $3, $4, $5, 'now'::timestamp + INTERVAL '1 day', true)"
            await self.bot.write(query, hometeam, awayteam, channel.id, home_role.id, away_role.id)

            gameid = await self.bot.db.fetchval(
                f"SELECT gameid FROM games WHERE hometeam = '{hometeam}' AND awayteam = '{awayteam}' ORDER BY gameid DESC")
            listener_cog = self.bot.get_cog('Listener')
            listener_cog.offcache[channel.id] = (gameid, hometeam, awayteam, 'AWAY', channel.id)

            message = await channel.send(RANGES_IMAGE_URL)
            await message.pin()
            await channel.send(f'Game has started between {home_role.mention} and {away_role.mention}\n\n'
                               f'{hometeam.upper()} 0-0 {awayteam.upper()} '
                               f'0:00\n\n'
                               f'{away_role.mention}, please call **heads** or **tails**.')
            return await ctx.reply(f'Game successfully started in {channel.mention}.')
        else:
            return await ctx.reply(
                f'Error: One or both of your teams does not exist. Run command {self.bot.command_prefix}teamlist for a list of teams.')

    @commands.command(name='abandongame')
    @commands.has_role('bot operator')
    async def abandon_game(self, ctx):
        """Abandons a game in a channel."""
        game = await self.bot.db.fetchrow(f'SELECT homeroleid, awayroleid, homescore, awayscore FROM games WHERE channelid = {ctx.channel.id}')
        try:
            home_role = discord.utils.get(ctx.guild.roles, id=game['homeroleid'])
            away_role = discord.utils.get(ctx.guild.roles, id=game['awayroleid'])
        except TypeError:
            return await ctx.reply('Error: Channel does not appear to be game channel.')
        await self.bot.write(f"UPDATE games SET gamestate = 'ABANDONED' WHERE channelid = {ctx.channel.id}")
        scores_channel = discord.utils.get(ctx.guild.channels, name='scores')
        await scores_channel.send(f'GAME ABANDONED: {home_role.mention} {game["homescore"]}-{game["awayscore"]} {away_role.mention}')
        await ctx.reply('Game Abandoned. You may delete this channel at any time.')

    @commands.command(name='forceendgame', aliases=['stopgame', 'endgame'])
    @commands.has_role('bot operator')
    async def force_end_game(self, ctx):
        """Forces a game to end in a channel."""
        game = await self.bot.db.fetchrow(
            f'SELECT homeroleid, awayroleid, homescore, awayscore FROM games WHERE channelid = {ctx.channel.id}')
        try:
            home_role = discord.utils.get(ctx.guild.roles, id=game['homeroleid'])
            away_role = discord.utils.get(ctx.guild.roles, id=game['awayroleid'])
        except TypeError:
            return await ctx.reply('Error: Channel does not appear to be game channel.')
        await self.bot.write(f"UPDATE games SET gamestate = 'FINAL' WHERE channelid = {ctx.channel.id}")
        scores_channel = discord.utils.get(ctx.guild.channels, name='scores')
        await scores_channel.send(
            f'GAME ENDED EARLY: {home_role.mention} {game["homescore"]}-{game["awayscore"]} {away_role.mention}')
        writeup = f'The game was ended early by a bot operator.\n\nAnd that\'s the end of the game!'
        if game['homescore'] > game['awayscore']:
            writeup += f' {home_role.mention} has defeated {away_role.mention} by a score of {game["homescore"]}-{game["awayscore"]}.'
        elif game['awayscore'] > game['homescore']:
            writeup += f' {away_role.mention} has defeated {home_role.mention} by a score of {game["awayscore"]}-{game["homescore"]}.'
        else:
            writeup += f' {home_role.mention} and {away_role.mention} drew by a score of {game["homescore"]}-{game["awayscore"]}.'
        writeup += ' Drive home safely!\nYou may delete this channel whenever you want.'
        await ctx.reply(writeup)

    @commands.command(name='forcechew')
    @commands.has_role('bot operator')
    async def force_chew(self, ctx):
        """Toggles on or off force chew mode in a game channel."""
        game = await self.bot.db.fetchrow(f'SELECT homeroleid, awayroleid, default_chew FROM games WHERE channelid = {ctx.channel.id}')
        try:
            home_role = discord.utils.get(ctx.guild.roles, id=game['homeroleid'])
            away_role = discord.utils.get(ctx.guild.roles, id=game['awayroleid'])
        except TypeError:
            return await ctx.reply('Error: Channel does not appear to be game channel.')
        if not game['default_chew']:
            await self.bot.write(f'UPDATE games SET default_chew = true WHERE channelid = {ctx.channel.id}')
            return await ctx.reply(f'{home_role.mention} {away_role.mention} The game is now in chew only mode.')
        await self.bot.write(f'UPDATE games SET default_chew = false WHERE channelid = {ctx.channel.id}')
        return await ctx.reply(f'{home_role.mention} {away_role.mention} The game is no longer in chew only mode.')

    @commands.command(name='addscore', aliases=['addgoal'])
    @commands.has_role('bot operator')
    async def add_score(self, ctx, arg: str):
        """Allows bot operator to manually add a point to the game in the game channel."""
        arg = arg.lower()
        if arg not in ['home', 'away']:
            return await ctx.reply('Please specify home or away.')
        game = await self.bot.db.fetchrow(f'SELECT homeroleid, awayroleid FROM games WHERE channelid = {ctx.channel.id}')
        try:
            home_role = discord.utils.get(ctx.guild.roles, id=game['homeroleid'])
            away_role = discord.utils.get(ctx.guild.roles, id=game['awayroleid'])
        except TypeError:
            return await ctx.reply('Error: Channel does not appear to be game channel.')
        await self.bot.write(f"UPDATE games SET {'homescore' if arg == 'home' else 'awayscore'} = {'homescore' if arg == 'home' else 'awayscore'} + 1 WHERE channelid = {ctx.channel.id}")
        return await ctx.reply(f'{home_role.mention if arg == "home" else away_role.mention} has been granted one goal by a bot operator.')

    @commands.command(name='rerun')
    @commands.has_role('bot operator')
    async def rerun(self, ctx):
        """Reruns the play. Asks the defense for the defensive number again."""
        game = await self.bot.db.fetchrow(f'SELECT hometeam, awayteam, homeroleid, awayroleid, homescore, awayscore, seconds, waitingon, def_off FROM games WHERE channelid = {ctx.channel.id}')
        try:
            home_role = discord.utils.get(ctx.guild.roles, id=game['homeroleid'])
            away_role = discord.utils.get(ctx.guild.roles, id=game['awayroleid'])
        except TypeError:
            return await ctx.reply('Error: Channel does not appear to be game channel.')
        if game['def_off'] == 'DEFENSE':
            waitingon = game['waitingon']
        else:
            waitingon = 'HOME' if game['waitingon'] == 'AWAY' else 'AWAY'
        await self.bot.write(f"UPDATE games SET "
                             f"def_off = 'DEFENSE'::def_off, "
                             f"waitingon = '{waitingon}' "
                             f"WHERE channelid = {ctx.channel.id}")
        listener_cog = self.bot.get_cog('Listener')
        defensive_user_id = await listener_cog.user_id_from_team(game['hometeam'] if waitingon == 'HOME' else game['awayteam'])
        await self.bot.get_user(defensive_user_id).send(DEFENSIVE_MESSAGE.format(hometeam=game['hometeam'].upper(),
                                                                                 awayteam=game['awayteam'].upper(),
                                                                                 homescore=game['homescore'],
                                                                                 awayscore=game['awayscore'],
                                                                                 game_time=utils.seconds_to_time(game['seconds'])))
        await ctx.reply(f'{home_role.mention} {away_role.mention} Current play is being rerun. Awaiting defensive number.')


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
            embed = discord.Embed(title='Eval', description=f'```py\n{await result}\n```', color=discord.Color(0x000000))
        else:
            embed = discord.Embed(title='Eval', description=f'```py\n{result}\n```', color=discord.Color(0x000000))
        await ctx.reply(embed=embed)


def setup(bot: Bot):
    bot.add_cog(Teams(bot))
    bot.add_cog(GameManagement(bot))
    bot.add_cog(Eval(bot))
