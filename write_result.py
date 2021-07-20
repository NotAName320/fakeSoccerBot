"""
Result processor and writer for Fake Soccer Bot

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

from enum import Enum
from typing import Literal

from discord_db_client import Bot
from ranges import Results


class ClockUse(Enum):
    """Enumeration representing the clock use action."""
    HURRY = 1
    NORMAL = 2
    CHEW = 3


class DBResult:
    def __init__(self, result: Results, clock_use: ClockUse = ClockUse.NORMAL):
        self.result = result
        self.clock_use = clock_use

    async def send(self, client: Bot, gameid: int, home_away: Literal['home', 'away']):
        if self.clock_use == ClockUse.HURRY:
            seconds_to_add = 30
        elif self.clock_use == ClockUse.CHEW:
            seconds_to_add = 60
        else:
            seconds_to_add = 45
        if home_away == 'home':
            opposite = 'away'
            home_score_to_add = 1 if self.result is Results.GOAL else 0
            away_score_to_add = 1 if self.result is Results.OPPOSING_GOAL else 0
        else:
            opposite = 'home'
            home_score_to_add = 1 if self.result is Results.OPPOSING_GOAL else 0
            away_score_to_add = 1 if self.result is Results.GOAL else 0
        if self.result in [Results.GOAL, Results.TURNOVER_ATTACK, Results.TURNOVER_MIDFIELD, Results.TURNOVER_DEFENSE, Results.TURNOVER_FREE_KICK]:
            waitingon = home_away
        else:
            waitingon = opposite
        if self.result in [Results.ATTACK, Results.TURNOVER_ATTACK]:
            field_position = 'ATTACK'
        elif self.result in [Results.MIDFIELD, Results.TURNOVER_MIDFIELD, Results.GOAL, Results.OPPOSING_GOAL]:
            field_position = 'MIDFIELD'
        elif self.result in [Results.DEFENSE, Results.TURNOVER_DEFENSE]:
            field_position = 'DEFENSE'
        elif self.result in [Results.FREE_KICK, Results.TURNOVER_FREE_KICK]:
            field_position = 'FREEKICK'
        else:
            field_position = 'PENALTY'
        await client.write(f"UPDATE games SET "
                           f"homescore = homescore + {home_score_to_add}, "
                           f"awayscore = awayscore + {away_score_to_add}, "
                           f"seconds = seconds + {seconds_to_add}, "
                           f"gamestate = '{field_position}', "
                           f"def_off = 'DEFENSE'::def_off, "
                           f"waitingon = '{waitingon.upper()}' "
                           f"WHERE gameid = {gameid}")
