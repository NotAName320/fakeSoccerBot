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
    TURNOVER_DEFENSE = 7  # Refers to the state now being defense, not ball being on other side
    TURNOVER_MIDFIELD = 8
    TURNOVER_ATTACK = 9
    TURNOVER_FREE_KICK = 10
    OPPOSING_GOAL = 11


RangeDict = Dict[int, Results]


ATTACK: RangeDict = {
    0: Results.GOAL,
    21: Results.PENALTY_KICK,
    26: Results.FREE_KICK,
    51: Results.ATTACK,
    176: Results.MIDFIELD,
    251: Results.TURNOVER_DEFENSE,
    351: Results.TURNOVER_MIDFIELD,
    470: Results.TURNOVER_ATTACK,
    500: Results.OPPOSING_GOAL
}

MIDFIELD: RangeDict = {
    0: Results.GOAL,
    11: Results.ATTACK,
    151: Results.MIDFIELD,
    226: Results.TURNOVER_DEFENSE,
    256: Results.TURNOVER_MIDFIELD,
    351: Results.TURNOVER_ATTACK,
    471: Results.TURNOVER_FREE_KICK,
    498: Results.OPPOSING_GOAL
}

DEFENSE: RangeDict = {
    0: Results.GOAL,
    1: Results.ATTACK,
    51: Results.MIDFIELD,
    226: Results.DEFENSE,
    326: Results.TURNOVER_MIDFIELD,
    401: Results.TURNOVER_ATTACK,
    470: Results.TURNOVER_FREE_KICK,
    495: Results.OPPOSING_GOAL
}

FREE_KICK: RangeDict = {
    0: Results.GOAL,
    26: Results.ATTACK,
    151: Results.MIDFIELD,
    226: Results.TURNOVER_DEFENSE,
    351: Results.TURNOVER_MIDFIELD,
    470: Results.TURNOVER_DEFENSE,
    500: Results.OPPOSING_GOAL
}

PENALTY: RangeDict = {
    0: Results.GOAL,
    326: Results.TURNOVER_DEFENSE
}
