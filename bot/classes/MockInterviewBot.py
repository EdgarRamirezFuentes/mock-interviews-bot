import asyncio
import os
import random

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord.ext import commands


class MockInterviewBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        # Channel id where the messages will be sent.
        self.__CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
        # The Id of the active 
        self.__mock_interviews_participation_message_id = None
        self.__mock_interviews_participation_message = None
        self.__mock_interview_participants = set()
        self.__mock_interview_teams = None
        self.__mock_interview_teams_message = None
        # Store the user who has no team this week, if exists.
        self.__no_team_user = None

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
        """ Notifies that the client connected to Discord and Set up the cron jobs to send messages.
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


    async def on_reaction_add(self, reaction, user)->None:
        """Handles when a reaction is added to the weekly mock interview message or
            the lonely user message message.

            Args:
                reaction: The reaction that was added in a message.
                user: The user that reacted to a message.
        """
        if user == self.user:
            return
        
        if reaction.message.id == self.__mock_interviews_participation_message_id:
            self.__mock_interview_participants.add(user)
            message = f'{user.mention} joined to the mock interviews. {self.__emojis["CHECK"]}'
            channel = reaction.message.channel
            await self.__send_message(channel, message)

        if reaction.message.id == self.no_team_user_message_id:
            message = f'{user.mention} is the partner of ' + \
                      f'{self.no_team_user_message_id.mention} this week. {self.__emojis["HANDSHAKE"]}'
            self.no_team_user = None
            channel = reaction.message.channel
            await self.__send_message(channel, message)
            # Delete the message because the lonely user has found a team.
            await reaction.message.delete()


    async def on_reaction_remove(self, reaction, user)->None:
        """Handles when a reaction is removed to the weekly mock interview message.

            Args:
                reaction: The reaction that was removed in a message.
                user: The user that deleted their to a message.
        """
        if user == self.user:
            return
        
        if reaction.message.id == self.__mock_interviews_participation_message_id:
            self.__mock_interview_participants.remove(user)
            message = f'{user.mention} left the mock interviews. {self.__emojis["X"]}'
            channel = reaction.message.channel
            await self.__send_message(channel, message)


    ####################
    # Cron job methods #
    ####################
    async def __mock_interview_participation_job(self)->None:
        self.__mock_interview_participants.clear()
        channel = self.get_channel(int(os.getenv('CHANNEL_ID')))
        self.__mock_interviews_participation_message = self.__get_mock_interview_participation_message()
        discord_message = await self.__send_message(channel, 
                                                    self.__mock_interviews_participation_message)
        self.__react_to_a_message(discord_message, self.__emojis['COMPUTER'])


    async def __mock_interview_teams_job(self)->None:
        """Sends the message with the mock interview teams.
        """
        channel = self.get_channel(int(os.getenv('CHANNEL_ID')))
        self.__mock_interview_teams_message = self.__get_interview_teams_message()
        await self.__send_message(channel, self.__mock_interview_teams_message)
        
        if self.__no_team_user:
            no_team_user_message = self.__get_no_team_user_message(self.__no_team_user)
            discord_message = await self.__send_message(channel, no_team_user_message)
            self.__react_to_a_message(discord_message, self.__emojis['HAND_SPLAYED'])

    
    async def __create_interview_teams_job(self):
        """Creates the mocking interview teams of the week.
        """
        if len(self.__mock_interview_participants) < 2:
            self.__mock_interview_teams = None
            return
        
        interview_participants = list(self.__mock_interview_participants)

        if len(interview_participants) % 2 != 0:
            interview_participants.append(None)

        random.shuffle(interview_participants)
        self.__mock_interview_teams = zip(interview_participants[0::2], 
                                          interview_participants[1::2])


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
        self.__mock_interviews_participation_message_id = discord_message.id

        return discord_message
    
    def __react_to_a_message(self, message, reaction:str)->None:
        """Adds the specified reaction to the message.

        Args:
            message: The message where the reaction will be added.
            reaction (str): The reaction in unicode format.
        """
        message.add_reaction(reaction)


    #############################
    # Message generator methods #
    #############################
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


    def __get_interview_teams_message(self)->str:
        """Generate the message to show the mock interview teams.

            Returns:
                str: The message to show the mock interview teams.
        """

        if not self.__mock_interview_teams:
            return f'@everyone\nThere are no enough people to create mock interview teams! {self.__emojis["SAD"]}'
        
        message = '@everyone\nThe mock interview teams has been created!.\n'
        message += f'Please get in touch with your team to agree on a date and time for the interviews. {self.__emojis["DATE"]}\n\n'
        message += f'Good luck! {self.__emojis["NERD"]}\n\n'
        message += 'Mock interview teams:\n'
        
        for participant1, participant2 in self.__mock_interview_teams:
            if participant1 and participant2:
                message += f'{participant1.mention} - {participant2.mention} {self.__emojis["HANDSHAKE"]}\n'
            else:
                self.__no_team_user = participant1 if participant1 else participant2

        return message