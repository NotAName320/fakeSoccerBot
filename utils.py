"""
Utility functions for the Fake Soccer Bot

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

from typing import Optional
from random import randint


def seconds_to_time(seconds: int, extra1: Optional[int] = None, extra2: Optional[int] = None) -> str:
    """Takes seconds and turns into time string."""
    if extra1 is None:
        extra1 = 0
    if extra2 is None:
        extra2 = 0
    if 2700 + (extra1 * 60) > seconds >= 2700:
        m, s = divmod(seconds - 2700, 60)
        return f'45:00+{m:d}:{s:02d}'
    if 5400 + (extra2 * 60) > seconds - (extra1 * 60) >= 5400:
        m, s = divmod(seconds - (5400 + (extra1 * 60)), 60)
        return f'90:00+{m:d}:{s:02d}'
    seconds -= (extra1 * 60) + (extra2 * 60)
    m, s = divmod(seconds, 60)
    return f'{m:d}:{s:02d}'


def calculate_diff(num1: int, num2: int) -> int:
    """Calculates a diff number from 0 to 500 based on two numbers from 1 to 1000 with wraparounds."""
    diff = abs(num1 - num2)
    if diff > 500:
        return 1000 - diff
    return diff


def extra_time_bell_curve():
    """Random extra time based on bell curve distribution"""
    d1000 = randint(1, 1000)
    if d1000 <= 23:
        return 1
    if d1000 <= 46:
        return 6
    if d1000 <= 182:
        return 2
    if d1000 <= 318:
        return 5
    if d1000 <= 659:
        return 3
    return 4
