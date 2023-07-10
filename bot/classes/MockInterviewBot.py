import asyncio
import os
import random
from collections import defaultdict

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord.ext import commands


class MockInterviewBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        # Channels where the messages will be sent.
        self.__channels = set()
        # The active participation message of each guild.
        self.__active_mock_interviews_participation_messages = defaultdict(lambda: None)
        # The active no team user message of each guild.
        self.__no_team_user_messages = defaultdict(lambda: None)
        # The participants of the mock interviews of the week of each guild.
        self.__mock_interview_participants = defaultdict(set)
        # The mock interview teams of the week of each guild.
        self.__mock_interview_teams = defaultdict(lambda: None)
        # The user who has no team of the week of each guild.
        self.__no_team_user = defaultdict(lambda: None)

        self.__mock_interviews_participation_message = None
        self.__mock_interview_teams_message = None

        # Store the unicode code of some emojis.
        self.__emojis = {
            'COMPUTER' : '\U0001F4BB',
            'CHECK' :'\U00002705',
            'X': '\U0000274C',
            'HANDSHAKE': '\U0001F91D',
            'HAND_SPLAYED': '\U0001F590',
            'SAD': '\U0001F622',
            'NERD': '\U0001F913',
            'DATE': '\U0001F4C5',
        }

        # Tool to handle cron jobs and send the messages every monday and tuesday.
        self.SCHEDULER = AsyncIOScheduler()
        super().__init__(*args, **kwargs)
        

    ##########################
    # Discord client methods #
    ##########################
    async def on_ready(self)->None:
        """ Setup the bot environment.
        """
        print(f'MockInterviewBot connected as {self.user.name}')

        if not self.SCHEDULER.get_jobs():
            self.SCHEDULER.add_job(self.__mock_interview_participation_job, 
                                   'cron', day_of_week='mon', hour=10)

            self.SCHEDULER.add_job(self.__create_interview_teams_job,
                                   'cron', day_of_week='tue', hour=10)

            self.SCHEDULER.add_job(self.__mock_interview_teams_job, 
                                   'cron', day_of_week='tue', hour=11)

            self.SCHEDULER.start()

        # Retrieving all the channels where the bot will send the messages.
        for channel in self.get_all_channels():
            if channel.name == 'interviews':
                self.__channels.add(channel)
                print(f'Found interviews channel in {channel.guild.name}')


    async def on_reaction_add(self, reaction, user)->None:
        """Handles when a reaction is added to the weekly mock interview message or
            the lonely user message message.

            Args:
                reaction: The reaction that was added in a message.
                user: The user that reacted to a message.
        """
        if user == self.user:
            return

        ## Getting the guild id where the reaction was added.
        guild_id = reaction.message.guild.id
        reaction_emoji = reaction.emoji

        if reaction_emoji == self.__emojis['COMPUTER']:
            # Verify if the reaction was added to the weekly mock interview message.
            reacted_to_active_mock_interview_message = reaction.message == \
                  self.__active_mock_interviews_participation_messages[guild_id]

            if reacted_to_active_mock_interview_message:
                self.__mock_interview_participants[guild_id].add(user)
                message = f'{user.mention} joined to the mock interviews. {self.__emojis["CHECK"]}'
                channel = reaction.message.channel
                await self.__send_message(channel, message)

        elif reaction_emoji == self.__emojis['HAND_SPLAYED']:
            # Verify if the reaction was added to the active no team user message.
            reacted_to_active_no_team_user_message = reaction.message == \
                    self.__no_team_user_messages[guild_id]
            
            can_team_up = user != self.__no_team_user[guild_id]
            
            if reacted_to_active_no_team_user_message and can_team_up:
                message = f'{user.mention} is the partner of ' + \
                        f'{self.__no_team_user[guild_id].mention} this week. {self.__emojis["HANDSHAKE"]}'
                self.__no_team_user[guild_id] = None
                channel = reaction.message.channel
                await self.__send_message(channel, message)
                # Delete the message because the no team user has found a team.
                await reaction.message.delete()


    async def on_reaction_remove(self, reaction, user)->None:
        """Handles when a reaction is removed to the weekly mock interview message.

            Args:
                reaction: The reaction that was removed in a message.
                user: The user that deleted their to a message.
        """
        if user == self.user:
            return

        guild_id = reaction.message.guild.id
        removed_reaction_in_active_mock_interview_message = reaction.message == \
                self.__active_mock_interviews_participation_messages[guild_id]

        if removed_reaction_in_active_mock_interview_message:
            self.__mock_interview_participants[guild_id].remove(user)
            message = f'{user.mention} left the mock interviews. {self.__emojis["X"]}'
            channel = reaction.message.channel
            await self.__send_message(channel, message)


    async def on_guild_join(self, guild)->None:
        """Handles when the bot joins a server.
        """
        interviews_channel = discord.utils.get(guild.channels, name='interviews')
        
        if interviews_channel:
            self.__channels.add(interviews_channel)
            welcome_message = f'Hello! I\'m MockInterviewBot. I will help you to organize the mock interviews of the week.\n\n'
            await self.__send_message(interviews_channel, welcome_message)
        else:
            print(f'No interviews channel found in {guild.name}')


    ####################
    # Cron job methods #
    ####################
    async def __mock_interview_participation_job(self)->None:
        """Sends the message to participate in the mock interviews of the week to each guild.
        """
        # Clear the participants of the mock interviews of the week of each guild.
        for participants in self.__mock_interview_participants.values():
            participants.clear()

        self.__mock_interviews_participation_message = self.__get_mock_interview_participation_message()

        for channel in self.__channels:
            guild_id = channel.guild.id
            discord_message = await self.__send_message(channel, 
                                                        self.__mock_interviews_participation_message)
            await self.__react_to_a_message(discord_message, self.__emojis['COMPUTER'])

            # Update the active participation message of the guild.
            self.__active_mock_interviews_participation_messages[guild_id] = discord_message


    async def __mock_interview_teams_job(self)->None:
        """Sends the message with the mock interview teams to each guild.
        """
        for channel in self.__channels:
            guild_id = channel.guild.id
            teams = self.__mock_interview_teams[guild_id]
            self.__mock_interview_teams_message = self.__get_interview_teams_message(teams)
            has_no_team_user = self.__no_team_user[guild_id] != None

            await self.__send_message(channel, self.__mock_interview_teams_message)

            if has_no_team_user:
                no_team_user = self.__no_team_user[guild_id]
                no_team_user_message = self.__get_no_team_user_message(no_team_user)
                discord_message = await self.__send_message(channel, no_team_user_message)
                # Update the active no team user message of the guild.
                self.__no_team_user_messages[guild_id] = discord_message
                await self.__react_to_a_message(discord_message, self.__emojis['HAND_SPLAYED'])


    async def __create_interview_teams_job(self):
        """Creates the mocking interview teams of the week.
        """
        for guild_id, participants in self.__mock_interview_participants.items():
            self.__mock_interview_teams[guild_id] = self.__create_interview_teams(participants)


    ###############################
    # Channel interaction methods # 
    ###############################  
    async def __send_message(self, channel, message:str):
        """Send a message in the specified channel.

            Args:
                channel (_type_): The channel where the message will be sent.
                message (str): The message that will be sent.

            Returns:
                The discord message object.
        """
        discord_message = await channel.send(message)

        return discord_message


    async def __react_to_a_message(self, message, reaction:str)->None:
        """Adds the specified reaction to the message.

        Args:
            message: The message where the reaction will be added.
            reaction (str): The reaction in unicode format.
        """
        await message.add_reaction(reaction)


    #################
    # Utils methods #
    #################
    def __get_mock_interview_participation_message(self)->str:
        """Generates the message to participate in the mock interviews of the week.

            Returns:
                str: The message to participate in the mock interviews of the week.
        """
        message = '@everyone\nIt\'s mock interviews time!\n\n'
        message += f'React to this message with {self.__emojis["COMPUTER"]} ' + \
                   f'if you want to join the mock interviews of the week.\n\n'
        message += '**You have 24 hours to react to this message to be considered ' + \
                    'in the mock interview teams.**\n\n'

        return message


    def __get_no_team_user_message(self, no_team_user)->str:
        """Generates the message to show the user who has no team.

            Args:
                no_team_user: The user who has no team.

            Returns:
                str: The message to show the user who has no team.
        """
        message = f'{no_team_user.mention} has no team this week. {self.__emojis["SAD"]}\n\n'
        message += f'@everyone\nReact to this message with {self.__emojis["HAND_SPLAYED"]} ' + \
                    f'if you want to team up with {no_team_user.mention} this week.'

        return message


    def __get_interview_teams_message(self, teams)->str:
        """Generate the message to show the mock interview teams.

            Returns:
                str: The message to show the mock interview teams.
        """

        if not teams:
            return f'@everyone\nThere are no enough people to create mock interview teams! {self.__emojis["SAD"]}'

        message = '@everyone\nThe mock interview teams has been created!.\n'
        message += f'Please get in touch with your team to agree on a date and time for the interviews. {self.__emojis["DATE"]}\n\n'
        message += f'Good luck! {self.__emojis["NERD"]}\n\n'
        message += 'Mock interview teams:\n'

        print(teams, type(teams))

        for participant1, participant2 in teams:
            if participant1 and participant2:
                message += f'{participant1.mention} - {participant2.mention} {self.__emojis["HANDSHAKE"]}\n'
            else:
                self.__no_team_user = participant1 if participant1 else participant2

        return message


    def __create_interview_teams(self, participants)->None:
        """Creates the mock interview teams of the week.

            Args:
                participants (set): The participants of the mock interviews of the week.

            Returns:
                The mock interview teams of the week or None if there are no enough people.
        """
        teams = None

        if len(participants) > 1:
            interview_participants = list(participants)

            if len(interview_participants) % 2 != 0:
                interview_participants.append(None)

            random.shuffle(interview_participants)
            teams = zip(interview_participants[0::2], 
                                            interview_participants[1::2])

        return teams
