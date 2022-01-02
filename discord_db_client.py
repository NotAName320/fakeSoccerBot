"""
Creates an async PostgreSQL connection that can be accessed with a discord.py commands client

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

from asyncpg import Pool
from nextcord.ext import commands


class Bot(commands.Bot):
    """Represents both a connection to the PostgreSQL Client and Discord."""
    def __init__(self, **kwargs):
        self.db: Pool = kwargs.pop('db')
        super().__init__(**kwargs)

    async def write(self, query: str, *args):
        """Write something to the database."""
        connection = await self.db.acquire()
        async with connection.transaction():
            await self.db.execute(query, *args)
        await self.db.release(connection)
