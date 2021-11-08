# fakeSoccerBot
A bot created for the [Fake Soccer Discord server](https://discord.gg/BS4zpNnsv5).

# Requirements
To run this Discord bot, you need:
* Python 3.10 (Python 3.8 and 3.9 should also work, but are not tested)
* PostgreSQL
* The libraries listed in requirements.txt
* [This PostgreSQL schema](https://cdn.discordapp.com/attachments/395638697497985035/867157138912968754/fakesoccerschema)
* Previous experience with PostgreSQL and Discord bots (recommended)

# Setup
How to run this bot for yourself:
1. First, create a role called 'bot operator' (in lowercase) in your Discord server and grant it to yourself.
2. Then, clone this Github repo and create a file called credentials.json. Then, follow this general outline:![](https://cdn.discordapp.com/attachments/395638697497985035/867148844189220894/Screenshot_2021-07-20_135932.png)
3. Create a PostgreSQL database with the name "fakesoccer" and import [this schema](https://cdn.discordapp.com/attachments/395638697497985035/867157138912968754/fakesoccerschema) into the database.
4. Go to the [Discord Developer portal](https://discord.com/developers/applications) and create a new application, obtaining the bot token.
5. Place PostgreSQL credentials and Discord token in credentials.json.
6. Run bot.
