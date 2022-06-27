"""
Game listener for the Fake Soccer Bot

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

import datetime
from random import choice

import nextcord
from nextcord.ext import commands, tasks

from discord_db_client import Bot
from ranges import ATTACK, MIDFIELD, DEFENSE, FREE_KICK, PENALTY, BREAKAWAY
from utils import seconds_to_time, calculate_diff, extra_time_bell_curve
from write_result import ClockUse, DBResult


OFFENSIVE_MESSAGE = '{mention} Please submit an offensive number between `1` and `1000`. Add the phrase **chew** to use more time, and **hurry** to use less.\n\n{state}\n\n{hometeam} {homescore}-{awayscore} {awayteam} {game_time}.'
DEFENSIVE_MESSAGE = 'Please submit a defensive number between `1` and `1000`.\n\n{hometeam} {homescore}-{awayscore} {awayteam} {game_time}.'
guild_id = 843971716883021865

# TODO: Optimize some SELECT functions throughout by removing hometeamid and awayteamid (they are already provided by cache)


class Listener(commands.Cog):
    """Handles game-related functions and tasks."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.offcache = {}
        self.defcache = {}
        self.teamcache = {}
        self.refresh_game_team_cache.start()
        self.check_for_deadline.start()

    def cog_unload(self):
        self.refresh_game_team_cache.cancel()
        self.check_for_deadline.cancel()

    async def team_id_from_user(self, userid: int):
        teamid = await self.bot.db.fetchval("SELECT teamid FROM teams WHERE manager = $1", userid)
        return teamid

    async def user_id_from_team(self, teamid: str) -> int:
        userid = await self.bot.db.fetchval("SELECT CASE WHEN substitute IS NULL THEN manager ELSE substitute END FROM teams WHERE teamid = $1", teamid)
        return userid

    @tasks.loop(minutes=1)
    async def refresh_game_team_cache(self):
        """Natural refresh of the game and team cache. Not as necessary anymore but will sometimes catch a bugged game before it gets rerun."""
        self.offcache = {}
        self.defcache = {}
        self.teamcache = {}
        games = await self.bot.db.fetch("SELECT gameid, channelid, hometeam, awayteam, def_off, waitingon, gamestate FROM games WHERE gamestate != 'FINAL' AND gamestate != 'ABANDONED' AND gamestate != 'FORFEIT'")
        for game in games:
            if game['gamestate'] in ['ABANDONED', 'FINAL', 'FORFEIT']:
                # For some reason the connection bugs out and sometimes selects those games anyways. This is a hacky fix
                continue
            if game['def_off'] == 'OFFENSE':
                self.offcache[game['channelid']] = (game['gameid'], game['hometeam'], game['awayteam'], game['waitingon'], game['channelid'])
            else:
                self.defcache[game['channelid']] = (game['gameid'], game['hometeam'], game['awayteam'], game['waitingon'], game['channelid'])
        teams = await self.bot.db.fetch('SELECT teamname, teamid, substitute, manager FROM teams')
        for team in teams:
            manager_or_sub = team['manager']
            if team['substitute'] is not None:
                manager_or_sub = team['substitute']
            self.teamcache[team['teamid']] = (team['teamname'], manager_or_sub)

    @tasks.loop(hours=1)
    async def check_for_deadline(self):
        """Checks each active game and either gives warning, awards goal, or forfeits game."""
        games = await self.bot.db.fetch("SELECT gameid, deadline FROM games WHERE gamestate != 'FINAL' AND gamestate != 'ABANDONED' AND gamestate != 'FORFEIT'")
        for game in games:
            if game['deadline'] - datetime.timedelta(hours=12) < nextcord.utils.utcnow() < game['deadline'] - datetime.timedelta(hours=11):
                gameinfo = await self.bot.db.fetchrow(f'SELECT waitingon, homeroleid, awayroleid, channelid FROM games WHERE gameid = {game["gameid"]}')
                channel = self.bot.get_channel(gameinfo['channelid'])
                user_to_ping = nextcord.utils.get(channel.guild.roles, id=gameinfo['homeroleid'] if gameinfo['waitingon'] == 'HOME' else gameinfo['awayroleid'])
                return await channel.send(f'{user_to_ping.mention} You have about 12 hours left on your deadline.\nFailure to submit will lead to concession of a goal and/or a forfeit.')

            if game['deadline'] < nextcord.utils.utcnow():
                gameinfo = await self.bot.db.fetchrow(f'SELECT gamestate, waitingon, hometeam, awayteam, homedelays, awaydelays, channelid, homeroleid, awayroleid FROM games WHERE gameid = {game["gameid"]}')
                if gameinfo['gamestate'] == 'SHOOTOUT':
                    if gameinfo['waitingon'] == 'HOME':
                        await self.bot.write(f"UPDATE games SET "
                                             f"gamestate = 'FORFEIT', "
                                             f"awayscore = (CASE WHEN ABS(awayscore-homescore)>2 THEN awayscore ELSE 3 END), "
                                             f"homescore = (CASE WHEN ABS(awayscore-homescore)>2 THEN homescore ELSE 0 END), "
                                             f"homedelays = 3 "
                                             f"WHERE gameid = {game['gameid']}")
                        game_channel = self.bot.get_channel(gameinfo['channelid'])
                        home_role = nextcord.utils.get(game_channel.guild.roles, id=gameinfo['homeroleid'])
                        away_role = nextcord.utils.get(game_channel.guild.roles, id=gameinfo['awayroleid'])
                        await game_channel.send(f'{home_role.mention} has surpassed the deadline during a shootout. The game has been automatically forfeited.\n\n'
                                                f'The game is over! {away_role.mention} has won!\n\n'
                                                f'The score is 0-3.')
                        scores = await self.bot.db.fetchrow(f"SELECT homescore, awayscore FROM games WHERE channelid = {gameinfo['chennalid']}")
                        score_channel = nextcord.utils.get(game_channel.guild.channels, name='scores')
                        return await score_channel.send(f'SHOOTOUT FORFEIT: {home_role.mention} {scores["homescore"]}-{scores["awayscore"]} {away_role.mention}')
                    else:
                        await self.bot.write(f"UPDATE games SET "
                                             f"gamestate = 'FORFEIT', "
                                             f"awayscore = (CASE WHEN ABS(awayscore-homescore)>2 THEN awayscore ELSE 0 END), "
                                             f"homescore = (CASE WHEN ABS(awayscore-homescore)>2 THEN homescore ELSE 3 END), "
                                             f"awaydelays = 3 "
                                             f"WHERE gameid = {game['gameid']}")
                        game_channel = self.bot.get_channel(gameinfo['channelid'])
                        home_role = nextcord.utils.get(game_channel.guild.roles, id=gameinfo['homeroleid'])
                        away_role = nextcord.utils.get(game_channel.guild.roles, id=gameinfo['awayroleid'])
                        await game_channel.send(
                            f'{away_role.mention} has surpassed the deadline during a shootout. The game has been automatically forfeited.\n\n'
                            f'The game is over! {home_role.mention} has won!\n\n'
                            f'The score is 0-3.')
                        score_channel = nextcord.utils.get(game_channel.guild.channels, name='scores')
                        scores = await self.bot.db.fetchrow(f"SELECT homescore, awayscore FROM games WHERE channelid = {gameinfo['chennalid']}")
                        return await score_channel.send(
                            f'SHOOTOUT FORFEIT: {home_role.mention} {scores["homescore"]}-{scores["awayscore"]} {away_role.mention}')
                if gameinfo['waitingon'] == 'HOME':
                    if gameinfo['homedelays'] == 2:
                        await self.bot.write(f"UPDATE games SET "
                                             f"gamestate = 'FORFEIT', "
                                             f"awayscore = (CASE WHEN ABS(awayscore-homescore)>2 THEN awayscore ELSE 3 END), "
                                             f"homescore = (CASE WHEN ABS(awayscore-homescore)>2 THEN homescore ELSE 0 END), "
                                             f"homedelays = 3 "
                                             f"WHERE gameid = {game['gameid']}")
                        game_channel = self.bot.get_channel(gameinfo['channelid'])
                        home_role = nextcord.utils.get(game_channel.guild.roles, id=gameinfo['homeroleid'])
                        away_role = nextcord.utils.get(game_channel.guild.roles, id=gameinfo['awayroleid'])
                        scores = await self.bot.db.fetchrow(f"SELECT homescore, awayscore FROM games WHERE channelid = {gameinfo['channelid']}")
                        await game_channel.send(f'{home_role.mention} has reached the limit of 3 delays of game.\n\n'
                                                f'The game is over! {away_role.mention} has won!\n\n'
                                                f'The score is {scores["homescore"]}-{scores["awayscore"]}.')
                        score_channel = nextcord.utils.get(game_channel.guild.channels, name='scores')
                        return await score_channel.send(f'AUTOMATIC FORFEIT: {home_role.mention} {scores["homescore"]}-{scores["awayscore"]} {away_role.mention}')
                    else:
                        await self.bot.write(f"UPDATE games SET "
                                             f"gamestate = 'MIDFIELD', "
                                             f"awayscore = awayscore + 1, "
                                             f"homedelays = homedelays + 1, "
                                             f"waitingon = 'AWAY', "
                                             f"def_off = 'DEFENSE',"
                                             f"deadline = 'now'::timestamp + INTERVAL '1 day' "
                                             f"WHERE gameid = {game['gameid']}")
                        game_channel = self.bot.get_channel(gameinfo['channelid'])
                        home_role = nextcord.utils.get(game_channel.guild.roles, id=gameinfo['homeroleid'])
                        away_role = nextcord.utils.get(game_channel.guild.roles, id=gameinfo['awayroleid'])
                        # This variable is shortened because the non shortened one was too spammy
                        m = await self.bot.db.fetchrow(f'SELECT seconds, awayscore, homescore, hometeam, awayteam, extratime1, extratime2 FROM games WHERE gameid = {game["gameid"]}')
                        game_time = seconds_to_time(m["seconds"], m["extratime1"], m["extratime2"])
                        await game_channel.send(f'{home_role.mention} has taken their {"first" if gameinfo["homedelays"] == 0 else "second"} delay of game.\n\n'
                                                f'They have automatically conceded a goal. Ball is placed back at midfield, {home_role.mention} kickoff.\n\n'
                                                f'{m["hometeam"].upper()} {m["homescore"]}-{m["awayscore"]} {m["awayteam"].upper()} '
                                                f'{game_time}\n\n'
                                                f'Waiting on {away_role.mention} for defensive number')
                        defensive_user_id = await self.bot.db.fetchval(
                            f"SELECT (CASE WHEN substitute IS NULL THEN manager ELSE substitute END) FROM teams WHERE teamid = '{m['awayteam']}'")
                        defensive_user = self.bot.get_user(defensive_user_id)
                        await defensive_user.send(DEFENSIVE_MESSAGE.format(hometeam=m['hometeam'].upper(),
                                                                           awayteam=m['awayteam'].upper(),
                                                                           homescore=m['homescore'],
                                                                           awayscore=m['awayscore'],
                                                                           game_time=game_time))
                        waitingon = 'AWAY'
                else:
                    if gameinfo['awaydelays'] == 2:
                        await self.bot.write(f"UPDATE games SET "
                                             f"gamestate = 'FORFEIT', "
                                             f"awayscore = CASE WHEN ABS(awayscore-homescore)>2 THEN awayscore ELSE 0 END, "
                                             f"homescore = CASE WHEN ABS(awayscore-homescore)>2 THEN homescore ELSE 3 END, "
                                             f"awaydelays = 3 "
                                             f"WHERE gameid = {game['gameid']}")
                        game_channel = self.bot.get_channel(gameinfo['channelid'])
                        home_role = nextcord.utils.get(game_channel.guild.roles, id=gameinfo['homeroleid'])
                        away_role = nextcord.utils.get(game_channel.guild.roles, id=gameinfo['awayroleid'])
                        scores = await self.bot.db.fetchrow(f"SELECT homescore, awayscore FROM games WHERE channelid = {gameinfo['channelid']}")
                        await game_channel.send(f'{away_role.mention} has reached the limit of 3 delays of game.\n\n'
                                                f'The game is over! {home_role.mention} has won!\n\n'
                                                f'The score is {scores["homescore"]}-{scores["awayscore"]}.')
                        score_channel = nextcord.utils.get(game_channel.guild.channels, name='scores')
                        return await score_channel.send(f'AUTOMATIC FORFEIT: {home_role.mention} {scores["homescore"]}-{scores["awayscore"]} {away_role.mention}')
                    else:
                        await self.bot.write(f"UPDATE games SET "
                                             f"gamestate = 'MIDFIELD', "
                                             f"homescore = homescore + 1, "
                                             f"awaydelays = awaydelays + 1, "
                                             f"waitingon = 'HOME', "
                                             f"def_off = 'DEFENSE',"
                                             f"deadline = 'now'::timestamp + INTERVAL '1 day' "
                                             f"WHERE gameid = {game['gameid']}")
                        game_channel = self.bot.get_channel(gameinfo['channelid'])
                        home_role = nextcord.utils.get(game_channel.guild.roles, id=gameinfo['homeroleid'])
                        away_role = nextcord.utils.get(game_channel.guild.roles, id=gameinfo['awayroleid'])
                        # This variable is shortened because the non shortened one was too spammy
                        m = await self.bot.db.fetchrow(
                            f'SELECT seconds, awayscore, homescore, hometeam, awayteam, extratime1, extratime2 FROM games WHERE gameid = {game["gameid"]}')
                        game_time = seconds_to_time(m["seconds"], m["extratime1"], m["extratime2"])
                        await game_channel.send(
                            f'{away_role.mention} has taken their {"first" if gameinfo["awaydelays"] == 0 else "second"} delay of game.\n\n'
                            f'They have automatically conceded a goal. Ball is placed back at midfield, {away_role.mention} kickoff.\n\n'
                            f'{m["hometeam"].upper()} {m["homescore"]}-{m["awayscore"]} {m["awayteam"].upper()} '
                            f'{game_time}\n\n'
                            f'Waiting on {home_role.mention} for defensive number')
                        defensive_user_id = await self.bot.db.fetchval(
                            f"SELECT CASE WHEN substitute IS NULL THEN manager ELSE substitute END FROM teams WHERE teamid = '{m['hometeam']}'")
                        defensive_user = self.bot.get_user(defensive_user_id)
                        await defensive_user.send(DEFENSIVE_MESSAGE.format(hometeam=m['hometeam'].upper(),
                                                                           awayteam=m['awayteam'].upper(),
                                                                           homescore=m['homescore'],
                                                                           awayscore=m['awayscore'],
                                                                           game_time=game_time))
                        waitingon = 'HOME'
                try:
                    self.defcache[gameinfo['channelid']] = (self.offcache[gameinfo['channelid']][0], self.offcache[gameinfo['channelid']][1], self.offcache[gameinfo['channelid']][2], waitingon, self.offcache[gameinfo['channelid']][4])
                    del self.offcache[gameinfo['channelid']]
                except KeyError:
                    pass

    @check_for_deadline.before_loop
    async def before_start_checking_deadline(self):
        """Prevents deadline messages from firing before properly logged in to Discord"""
        await self.bot.wait_until_ready()

    @commands.Cog.listener(name='on_message')
    async def process_game(self, message):
        # Do not listen to messages that are sent by the bot itself or commands
        if message.content.startswith(self.bot.command_prefix) or message.author.id == self.bot.user.id:
            return

        # Do not process messages that are not sent by a manager of the team, and assign those teams to a variable
        target_teams = (key for key, value in self.teamcache.items() if message.author.id == value[1])
        if target_teams == ():
            return

        for target_team in target_teams:
            try:
                target_game_off = next(value for key, value in self.offcache.items() if target_team in value)
            except StopIteration:
                pass
            else:
                gameid, game_home, game_away, waiting_on_side, game_channel_id = target_game_off
                if message.channel.id == game_channel_id:
                    if (waiting_on_side == 'HOME' and game_home == target_team) or (waiting_on_side == 'AWAY' and game_away == target_team):
                        field_position = await self.bot.db.fetchval(f"SELECT gamestate FROM games WHERE gameid = {gameid}")
                        if field_position == 'COIN_TOSS':
                            if not any(x in message.content.lower() for x in ['heads', 'tails']):
                                return await message.reply('Did not call heads or tails.')

                            winner = choice(('HOME', 'AWAY'))
                            await self.bot.write(f"UPDATE games SET gamestate = 'COIN_TOSS_CHOICE', "
                                                 f"waitingon = '{winner}',"
                                                 f"deadline = 'now'::timestamp + INTERVAL '1 day' "
                                                 f"WHERE gameid = {gameid}")

                            try:
                                self.offcache[game_channel_id] = self.offcache[game_channel_id][:3] + (winner, game_channel_id)

                            except KeyError:
                                pass

                            if winner == 'HOME':
                                gameinfo = await self.bot.db.fetchrow(f'SELECT hometeam, awayteam, homeroleid FROM games WHERE gameid = {gameid}')
                                home_role = nextcord.utils.get(message.channel.guild.roles, id=gameinfo['homeroleid'])
                                return await message.reply(f'{home_role.mention} won the coin toss. Please choose to **kick** off the ball now or to **defer** to the second half.\n'
                                                           f'{gameinfo["hometeam"].upper()} 0-0 {gameinfo["awayteam"].upper()} 0:00')

                            gameinfo = await self.bot.db.fetchrow(f'SELECT hometeam, awayteam, awayroleid FROM games WHERE gameid = {gameid}')
                            away_role = nextcord.utils.get(message.channel.guild.roles, id=gameinfo['awayroleid'])
                            return await message.reply(f'{away_role.mention} won the coin toss. Please choose to **kick** off the ball now or to **defer** to the second half.\n'
                                                       f'{gameinfo["hometeam"].upper()} 0-0 {gameinfo["awayteam"].upper()} 0:00')

                        if field_position == 'COIN_TOSS_CHOICE':
                            if 'kick' in message.content.lower() and 'defer' in message.content.lower():
                                return await message.reply('Error: Both "kick" and "defer" were found in your message. Please try again.')
                            if 'kick' in message.content.lower():
                                kickoff = waiting_on_side
                            elif 'defer' in message.content.lower():
                                kickoff = 'AWAY' if waiting_on_side == 'HOME' else 'HOME'
                            else:
                                return await message.reply('Neither **kick** or **defer** were found in your message. Please try again.')
                            await self.bot.write(f"UPDATE games SET gamestate = 'MIDFIELD', "
                                                 f"waitingon = '{'AWAY' if kickoff == 'HOME' else 'HOME'}', "
                                                 f"deadline = 'now'::timestamp + INTERVAL '1 day', "
                                                 f"def_off = 'DEFENSE',"
                                                 f"first_half_kickoff = '{kickoff}' "
                                                 f"WHERE gameid = {gameid}")

                            try:
                                self.defcache[game_channel_id] = self.offcache[game_channel_id][:3] + ('AWAY' if kickoff == 'HOME' else 'HOME', game_channel_id)
                                del self.offcache[game_channel_id]
                            except KeyError:
                                pass

                            gameinfo = await self.bot.db.fetchrow(f'SELECT waitingon, hometeam, awayteam, homeroleid, awayroleid FROM games WHERE gameid = {gameid}')
                            home_role = nextcord.utils.get(message.channel.guild.roles, id=gameinfo['homeroleid'])
                            away_role = nextcord.utils.get(message.channel.guild.roles, id=gameinfo['awayroleid'])
                            await message.reply(f'{home_role.mention if kickoff == "HOME" else away_role.mention} will kick off in the first half.\n\n'
                                                f'{gameinfo["hometeam"].upper()} 0-0 {gameinfo["awayteam"].upper()} 0:00\n\n'
                                                f'Waiting on defensive number')
                            if kickoff == 'HOME':
                                user_to_dm = await self.user_id_from_team(gameinfo['awayteam'])
                            else:
                                user_to_dm = await self.user_id_from_team(gameinfo['hometeam'])
                            user_to_dm = self.bot.get_user(user_to_dm)
                            return await user_to_dm.send(DEFENSIVE_MESSAGE.format(hometeam=gameinfo["hometeam"].upper(),
                                                                                  awayteam=gameinfo["awayteam"].upper(),
                                                                                  homescore='0',
                                                                                  awayscore='0',
                                                                                  game_time='0:00'))

                        offnumbers = [int(x) for x in message.content.split() if x.isdigit()]

                        if len(offnumbers) >= 2:
                            return await message.reply('Multiple numbers were found in your message.')
                        if len(offnumbers) == 0:
                            return await message.reply('No numbers were found in your message. Please try again.')
                        offnumbers = offnumbers[0]
                        if 1 > offnumbers or 1000 < offnumbers:
                            return await message.reply('Error: Number out of range.')

                        if 'hurry' in message.content.lower() and 'chew' in message.content.lower():
                            return await message.reply('Error: Both "hurry" and "chew" were found in your message. Please try again.')
                        clock_mode = ClockUse.NORMAL
                        if 'hurry' in message.content.lower():
                            clock_mode = ClockUse.HURRY
                        if 'chew' in message.content.lower():
                            clock_mode = ClockUse.CHEW

                        game_row = await self.bot.db.fetchrow(f'SELECT defnumber, default_chew FROM games WHERE gameid = {gameid}')
                        if game_row['default_chew']:
                            clock_mode = ClockUse.CHEW
                        defnumber = game_row['defnumber']
                        diff = calculate_diff(offnumbers, defnumber)
                        ranges = None

                        if field_position == 'SHOOTOUT':
                            # TODO: Shootout code
                            pass

                        if field_position == 'PENALTY':
                            ranges = PENALTY

                        if field_position == 'FREEKICK':
                            ranges = FREE_KICK

                        if field_position == 'ATTACK':
                            ranges = ATTACK

                        if field_position == 'MIDFIELD':
                            ranges = MIDFIELD

                        if field_position == 'DEFENSE':
                            ranges = DEFENSE

                        if field_position == 'BREAKAWAY':
                            ranges = BREAKAWAY

                        outcome = None
                        previous_value = list(ranges.values())[0]
                        for key, value in ranges.items():
                            if key > diff:
                                outcome = previous_value
                                break
                            previous_value = value
                        outcome = list(ranges.values())[-1] if outcome is None else outcome

                        result = DBResult(result=outcome, clock_use=clock_mode)
                        await result.send(self.bot, gameid=gameid, home_away=waiting_on_side.lower())
                        gameinfo = await self.bot.db.fetchrow(f'SELECT first_half_kickoff, isscrimmage, homescore, awayscore, seconds, waitingon, hometeam, awayteam, homeroleid, awayroleid, extratime1, extratime2, secondhalf, overtimegame FROM games WHERE gameid = {gameid}')
                        seconds = gameinfo['seconds']
                        home_role = nextcord.utils.get(message.channel.guild.roles, id=gameinfo['homeroleid'])
                        away_role = nextcord.utils.get(message.channel.guild.roles, id=gameinfo['awayroleid'])
                        if gameinfo['waitingon'] == 'HOME':
                            mention_role = home_role
                            user_to_dm = await self.user_id_from_team(gameinfo['hometeam'])
                        else:
                            mention_role = away_role
                            user_to_dm = await self.user_id_from_team(gameinfo['awayteam'])
                        user_to_dm = self.bot.get_user(user_to_dm)

                        writeup_text = await self.bot.db.fetchval(f"SELECT writeuptext FROM writeups WHERE gamestate = '{field_position}' AND result = '{outcome.name}' AND disabled = FALSE ORDER BY random() LIMIT 1")
                        if writeup_text is None:
                            writeup_text = f"If you're seeing this, no writeup could be found. The result was {outcome.name}."
                        writeup = f'{writeup_text.format(offteam=home_role.mention if waiting_on_side == "HOME" else away_role.mention, defteam=home_role.mention if waiting_on_side == "AWAY" else away_role.mention)}\n\nOffensive Number: {offnumbers}\nDefensive Number: {defnumber}\nDiff: {diff}\nResult: {outcome.name}\n\n{mention_role.mention}'
                        extratime1 = 0 if gameinfo['extratime1'] is None else gameinfo['extratime1']  # To avoid TypeErrors
                        waitingon = gameinfo['waitingon']
                        if outcome.name not in ['PENALTY_KICK', 'FREE_KICK', 'TURNOVER_FREE_KICK', 'TURNOVER_PENALTY', 'BREAKAWAY', 'TURNOVER_BREAKAWAY']:
                            if gameinfo['seconds'] >= 2700 and gameinfo['extratime1'] is None:
                                minutes_to_add = extra_time_bell_curve()
                                await self.bot.write(f'UPDATE games SET extratime1 = {minutes_to_add} WHERE gameid = {gameid}')
                                writeup += f'\n\nStoppage time for the first half has started. There will be {minutes_to_add} extra minutes.'
                            elif gameinfo['seconds'] >= (2700+(extratime1*60)) and not gameinfo['secondhalf']:
                                if gameinfo['first_half_kickoff'] == 'HOME':
                                    second_half_kickoff = 'AWAY'
                                    user_to_dm = await self.user_id_from_team(gameinfo['hometeam'])
                                else:
                                    second_half_kickoff = 'HOME'
                                    user_to_dm = await self.user_id_from_team(gameinfo['awayteam'])
                                await self.bot.write(f"UPDATE games SET gamestate = 'MIDFIELD', "
                                                     f"def_off = 'DEFENSE', "
                                                     f"waitingon = '{'HOME' if second_half_kickoff == 'AWAY' else 'AWAY'}', "
                                                     f"secondhalf = true,"
                                                     f"seconds = 2700 + ({extratime1}*60) "
                                                     f"WHERE gameid = {gameid}")
                                seconds = 2700 + (extratime1 * 60)
                                writeup += f'\n\nAnd that\'s the end of the first half! The second half will begin at midfield with {away_role.mention if second_half_kickoff == "AWAY" else home_role.mention} getting the ball first.'
                                user_to_dm = self.bot.get_user(user_to_dm)
                                waitingon = gameinfo['first_half_kickoff']
                            extratime2 = 0 if gameinfo['extratime2'] is None else gameinfo['extratime2']
                            if gameinfo['seconds'] >= (5400+(extratime1*60)) and gameinfo['extratime2'] is None:
                                minutes_to_add = extra_time_bell_curve()
                                await self.bot.write(f'UPDATE games SET extratime2 = {minutes_to_add} WHERE gameid = {gameid}')
                                writeup += f'\n\nStoppage time for the second half has started. There will be {minutes_to_add} extra minutes.'
                            elif gameinfo['seconds'] >= (5400+(extratime1*60)+(extratime2*60)):
                                if gameinfo['overtimegame']:
                                    pass  # TODO
                                else:
                                    await self.bot.write(f"UPDATE games SET gamestate = 'FINAL' "
                                                         f"WHERE gameid = {gameid}")
                                    writeup += f'\n\nAnd that\'s the end of the game!'
                                    if gameinfo['homescore'] > gameinfo['awayscore']:
                                        writeup += f' {home_role.mention} has defeated {away_role.mention} by a score of {gameinfo["homescore"]}-{gameinfo["awayscore"]}.'
                                    elif gameinfo['awayscore'] > gameinfo['homescore']:
                                        writeup += f' {away_role.mention} has defeated {home_role.mention} by a score of {gameinfo["awayscore"]}-{gameinfo["homescore"]}.'
                                    else:
                                        writeup += f' {home_role.mention} and {away_role.mention} drew by a score of {gameinfo["homescore"]}-{gameinfo["awayscore"]}.'
                                    writeup += ' Drive home safely!\nYou may delete this channel whenever you want.'
                                    try:
                                        del self.offcache[game_channel_id]
                                    except KeyError:
                                        pass
                                    score_channel = nextcord.utils.get(message.guild.channels, name='scores')
                                    if gameinfo['isscrimmage']:
                                        await score_channel.send(f'SCRIMMAGE: {home_role.mention} {gameinfo["homescore"]}-{gameinfo["awayscore"]} {away_role.mention}')
                                    else:
                                        await score_channel.send(f'FINAL: {home_role.mention} {gameinfo["homescore"]}-{gameinfo["awayscore"]} {away_role.mention}')
                                    return await message.reply(writeup)

                        await message.reply(writeup)

                        try:
                            self.defcache[game_channel_id] = self.offcache[game_channel_id][:3] + (waitingon, game_channel_id)
                            del self.offcache[game_channel_id]
                        except KeyError:
                            pass
                        game_time = seconds_to_time(seconds, gameinfo['extratime1'], gameinfo['extratime2'])
                        await user_to_dm.send(DEFENSIVE_MESSAGE.format(hometeam=gameinfo['hometeam'].upper(),
                                                                       awayteam=gameinfo['awayteam'].upper(),
                                                                       homescore=gameinfo['homescore'],
                                                                       awayscore=gameinfo['awayscore'],
                                                                       game_time=game_time))

            try:
                target_game_def = next(value for key, value in self.defcache.items() if target_team in value)
            except StopIteration:
                continue
            else:
                gameid, game_home, game_away, waiting_on_side, game_channel_id = target_game_def
                if type(message.channel) is nextcord.DMChannel:
                    if (waiting_on_side == 'HOME' and game_home == target_team) or (waiting_on_side == 'AWAY' and game_away == target_team):
                        defnumbers = [int(x) for x in message.content.split() if x.isdigit()]

                        if len(defnumbers) >= 2:
                            return await message.reply('Multiple numbers were found in your message.')
                        if len(defnumbers) == 0:
                            return await message.reply('No numbers were found in your message. Please try again.')
                        defnumbers = defnumbers[0]
                        if 1 > defnumbers or 1000 < defnumbers:
                            return await message.reply('Error: Number out of range.')

                        waitingon = 'AWAY' if waiting_on_side == 'HOME' else 'HOME'

                        await self.bot.write(f"UPDATE games SET "
                                             f"def_off = 'OFFENSE', "
                                             f"waitingon = '{waitingon}', "
                                             f"defnumber = {defnumbers},"
                                             f"deadline = 'now'::timestamp + INTERVAL '1 day' "
                                             f"WHERE gameid = {gameid}")

                        game_channel = self.bot.get_channel(game_channel_id)

                        role_to_get = 'awayroleid' if waitingon == 'AWAY' else 'homeroleid'
                        m = await self.bot.db.fetchrow(f'SELECT gamestate, seconds, awayscore, homescore, hometeam, awayteam, extratime1, extratime2, {role_to_get} FROM games WHERE gameid = {gameid}')
                        game_time = seconds_to_time(m["seconds"], m["extratime1"], m["extratime2"])
                        role = nextcord.utils.get(game_channel.guild.roles, id=m[role_to_get])
                        gamestate = {'ATTACK': '{} has the ball on the opponents\' side of the field.',
                                     'MIDFIELD': '{} has the ball at midfield.',
                                     'DEFENSE': '{} has the ball in their own territory.',
                                     'FREEKICK': '{} has a free kick.',
                                     'SHOOTOUT': 'It\'s {}\'s turn in a shootout.',
                                     'BREAKAWAY': '{} is breaking away with the ball!',
                                     'PENALTY': '{} has a penalty kick.'}[m['gamestate']]
                        await game_channel.send(OFFENSIVE_MESSAGE.format(mention=role.mention,
                                                                         hometeam=m['hometeam'].upper(),
                                                                         awayteam=m['awayteam'].upper(),
                                                                         state=gamestate.format(role.mention),
                                                                         homescore=m['homescore'],
                                                                         awayscore=m['awayscore'],
                                                                         game_time=game_time))
                        try:
                            self.offcache[game_channel_id] = self.defcache[game_channel_id][:3] + (waitingon, game_channel_id)
                            del self.defcache[game_channel_id]
                        except KeyError:
                            pass
                        return await message.reply(f"I've got {defnumbers} as your number.")


def setup(bot: Bot):
    bot.add_cog(Listener(bot))


def teardown(bot: Bot):
    bot.remove_cog('Listener')
