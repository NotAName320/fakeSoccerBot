"""
Results enumeration and Ranges implementation for Fake Soccer Bot

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
from typing import Dict


class Results(Enum):
    """Possible results for range dicts"""
    GOAL = 1
    PENALTY_KICK = 2
    FREE_KICK = 3
    ATTACK = 4
    MIDFIELD = 5
    DEFENSE = 6
    BREAKAWAY = 7
    TURNOVER_DEFENSE = 8  # Refers to the state now being defense, not ball being on other side
    TURNOVER_MIDFIELD = 9
    TURNOVER_ATTACK = 10
    TURNOVER_FREE_KICK = 11
    TURNOVER_BREAKAWAY = 12
    TURNOVER_PENALTY = 13
    OPPOSING_GOAL = 14


RangeDict = Dict[int, Results]


ATTACK: RangeDict = {
    0: Results.GOAL,
    21: Results.PENALTY_KICK,
    26: Results.FREE_KICK,
    51: Results.ATTACK,
    201: Results.MIDFIELD,
    301: Results.TURNOVER_DEFENSE,
    381: Results.TURNOVER_MIDFIELD,
    441: Results.TURNOVER_ATTACK,
    471: Results.TURNOVER_FREE_KICK,
    495: Results.TURNOVER_BREAKAWAY,
    500: Results.OPPOSING_GOAL
}

MIDFIELD: RangeDict = {
    0: Results.GOAL,
    11: Results.PENALTY_KICK,
    13: Results.BREAKAWAY,
    28: Results.FREE_KICK,
    41: Results.ATTACK,
    151: Results.MIDFIELD,
    276: Results.DEFENSE,
    326: Results.TURNOVER_DEFENSE,
    383: Results.TURNOVER_MIDFIELD,
    431: Results.TURNOVER_ATTACK,
    466: Results.TURNOVER_FREE_KICK,
    490: Results.TURNOVER_BREAKAWAY,
    499: Results.OPPOSING_GOAL
}

DEFENSE: RangeDict = {
    0: Results.GOAL,
    1: Results.PENALTY_KICK,
    3: Results.BREAKAWAY,
    23: Results.FREE_KICK,
    31: Results.ATTACK,
    101: Results.MIDFIELD,
    201: Results.DEFENSE,
    351: Results.TURNOVER_MIDFIELD,
    421: Results.TURNOVER_ATTACK,
    461: Results.TURNOVER_FREE_KICK,
    495: Results.TURNOVER_PENALTY,
    498: Results.OPPOSING_GOAL
}

FREE_KICK: RangeDict = {
    0: Results.GOAL,
    36: Results.ATTACK,
    201: Results.MIDFIELD,
    276: Results.TURNOVER_DEFENSE,
    376: Results.TURNOVER_MIDFIELD,
    451: Results.TURNOVER_ATTACK,
    476: Results.TURNOVER_FREE_KICK,
    493: Results.TURNOVER_BREAKAWAY,
    500: Results.OPPOSING_GOAL
}

PENALTY: RangeDict = {
    0: Results.GOAL,
    376: Results.TURNOVER_DEFENSE
}

BREAKAWAY: RangeDict = {
    0: Results.GOAL,
    81: Results.ATTACK,
    201: Results.MIDFIELD,
    251: Results.TURNOVER_DEFENSE,
    371: Results.TURNOVER_MIDFIELD,
    461: Results.TURNOVER_ATTACK,
    481: Results.TURNOVER_FREE_KICK,
    495: Results.TURNOVER_BREAKAWAY,
    500: Results.OPPOSING_GOAL
}
