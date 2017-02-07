import os
import time
import json
import signal
import logging
from functools import lru_cache

from slackclient import SlackClient

logging.basicConfig()
logger = logging.getLogger('upright')


class Bot(object):
    def __init__(self, token=os.environ.get('SLACK_BOT_TOKEN'), bot_id=os.environ.get('SLACK_BOT_ID')):
        self.slack_client = SlackClient(token)
        self.bot_id = bot_id
        self.firehose_finished = False

    @lru_cache(maxsize=10, typed=False)
    def get_channels(self):
        _channels = self.slack_client.api_call('channels.list')
        if not _channels.get('ok'):
            logger.error(str(_channels))
            return []

        return _channels['channels']

    @lru_cache(maxsize=10, typed=False)
    def get_groups(self):
        _groups = self.slack_client.api_call('groups.list')
        if not _groups.get('ok'):
            logger.error(str(_groups))
            return []

        return _groups['groups']

    @lru_cache(maxsize=10, typed=False)
    def get_users(self):
        _users = self.slack_client.api_call('users.list')
        if not _users.get('ok'):
            logger.error(str(_users))
            return []

        return _users['members']

    @lru_cache(maxsize=10, typed=False)
    def channel_name_to_id(self, channel_name):
        channels = self.get_channels() + self.get_groups()
        return next(iter(filter(lambda c: c['name'] == channel_name, channels)), {}).get('id')

    @lru_cache(maxsize=10, typed=False)
    def channel_id_to_name(self, channel_id):
        channels = self.get_channels() + self.get_groups()
        return next(iter(filter(lambda c: c['id'] == channel_id, channels)), {}).get('name')

    @lru_cache(maxsize=10, typed=False)
    def user_name_to_id(self, user_name):
        users = self.get_users()
        return next(iter(filter(lambda c: c['name'] == user_name, users)), {}).get('id')

    @lru_cache(maxsize=10, typed=False)
    def user_id_to_name(self, user_id):
        users = self.get_users()
        return next(iter(filter(lambda c: c['id'] == user_id, users)), {}).get('name')

    def do_teams(self, _, _event):
        logger.debug('Command: teams')
        # TODO:  Get this from a database
        teams = [
            {
                'name': 'search',
                'channel': 'boehmer-test',
                'schedule': {
                    'period': 'weekdays',
                    'time': '10:30:00',
                    'tz': 'America/New_York',
                },
                'members': [
                    self.bot_id,
                    'boehmer'
                ]
            }
        ]

        teams_message = [
            {
                "fallback": json.dumps(team),
                "color": "#36a64f",
                "title": 'Team: {}'.format(team['name']),
                "text": ','.join(["<@{member}>".format(member=member) for member in team['members']]),
                "fields": [
                    {
                        "title": "Channel",
                        # TODO: Figure out why this doesn't render as a link in the channel
                        "value": '<#{}|{}>'.format(self.channel_name_to_id(team['channel']), team['channel']),
                        "short": True
                    },
                    {
                        "title": "Period",
                        "value": team['schedule']['period'],
                        "short": True
                    },
                    {
                        "title": "Time",
                        "value": team['schedule']['time'],
                        "short": True
                    },
                    {
                        "title": "Timezone",
                        "value": team['schedule']['tz'],
                        "short": True
                    }
                ],
            } for team in teams
            ]
        self.slack_client.api_call("chat.postMessage", channel=_event.get('channel'), attachments=teams_message,
                                   as_user=True, reply_broadcast=False)

    def do_help(self, _, _event):
        logger.debug('Command: help')
        self.slack_client.rtm_send_message(channel=_event.get('channel'),
                                           message="*Commands*:```help: \tShow this message\nteams:\tList all teams```",
                                           reply_broadcast=False)

    def handle_command(self, _command, _event):
        commands = {
            'help': self.do_help,
            'teams': self.do_teams
        }

        command_name = _command[0].lower()
        do_function = commands.get(command_name) or self.do_help
        do_function(_command, _event)

    def parse_slack_event(self, _events):
        for _event in _events:
            if _event.get('type') == 'message':
                text = _event.get('text', '').strip().split()
                if text and text[0].lower() == "<@{}>".format(self.bot_id).lower():
                    yield text[1:], _event
                elif _event['channel'][0] == 'D' and 'bot_id' not in _event:
                    yield text, _event
        return

    def consume_firehose(self):
        def finish():
            self.firehose_finished = True

        signal.signal(signal.SIGTERM, lambda signal, frame: finish())
        READ_WEBSOCKET_DELAY = 0.1  # 1 second delay between reading from firehose
        if self.slack_client.rtm_connect():
            logger.info("Upright connected and running!")
            while not self.firehose_finished:
                try:
                    events = self.slack_client.rtm_read()
                    for command, event in self.parse_slack_event(events):
                        if command and event:
                            self.handle_command(command, event)
                    time.sleep(READ_WEBSOCKET_DELAY)
                except ConnectionResetError as _:
                    self.slack_client.rtm_connect()
        else:
            logger.error("Connection failed. Invalid Slack token or bot ID?")


if __name__ == "__main__":
    logger.setLevel('INFO')
    bot = Bot()
    bot.consume_firehose()
