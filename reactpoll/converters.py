import logging
import re
from typing import List, Union, Dict
from datetime import timedelta

from discord.ext.commands.converter import Converter
from discord.ext.commands.errors import BadArgument
from redbot.core import commands

log = logging.getLogger("red.flapjackcogs.reactpoll")

# the following regex is slightly modified from Red
# https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/core/commands/converter.py#L55
TIME_RE_STRING = r"|".join(
    [
        r"((?P<weeks>\d+?)\s?(weeks?|w))",
        r"((?P<days>\d+?)\s?(days?|d))",
        r"((?P<hours>\d+?)\s?(hours?|hrs|hr?))",
        r"((?P<minutes>\d+?)\s?(minutes?|mins?|m(?!o)))",  # prevent matching "months"
        r"((?P<seconds>\d+?)\s?(seconds?|secs?|s))",
    ]
)
TIME_RE = re.compile(TIME_RE_STRING, re.I)
QUESTION_RE = re.compile(r"([^;]+)(?<=\?)\s?", re.I)
OPTIONS_RE = re.compile(r"([\S\s]+)(?=;)[\S\s]+", re.I)
SPLIT_RE = re.compile(r";")
TIME_SPLIT = re.compile(r"t(?:ime)?=")
MULTI_RE = re.compile(r"(multi-vote)", re.I)


class PollOptions(Converter):
    """
    This will parse my defined multi response pattern and provide usable formats
    to be used in multiple reponses
    """

    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> Dict[str, Union[List[str], str, bool, timedelta]]:
        result: Dict[str, Union[List[str], str, bool, timedelta]] = {}
        if MULTI_RE.findall(argument):
            result["multiple_votes"] = True
            argument = MULTI_RE.sub("", argument)
        result, argument = self.strip_question(result, argument)
        # log.info(argument)
        result, argument = self.strip_time(result, argument)
        # log.info(argument)
        result, argument = self.strip_options(result, argument)
        # log.info(argument)
        result["author_id"] = ctx.author.id
        return result

    def strip_question(self, result: Dict[str, Union[List[str], str, bool, timedelta]], argument: str):
        match = QUESTION_RE.match(argument)
        if not match:
            raise BadArgument("That doesn't look like a question.")
        result["question"] = match[0]
        no_question = QUESTION_RE.sub("", argument)
        return result, no_question

    def strip_options(self, result: Dict[str, Union[List[str], str, bool, timedelta]], argument: str):
        possible_options = OPTIONS_RE.match(argument)
        if not possible_options:
            raise BadArgument("You have no options for this poll.")
        options = [s.strip() for s in SPLIT_RE.split(possible_options[0]) if s.strip()]
        if len(options) > 20:
            raise BadArgument("Use less options for the poll. Max options: 20.")
        result["options"] = options
        no_options = OPTIONS_RE.sub("", argument)
        return result, no_options

    def strip_time(self, result: Dict[str, Union[List[str], str, bool, timedelta]], argument: str):
        time_split = TIME_SPLIT.split(argument)
        if time_split:
            maybe_time = time_split[-1]
        else:
            maybe_time = argument

        time_data = {}
        for time in TIME_RE.finditer(maybe_time):
            argument = argument.replace(time[0], "")
            for k, v in time.groupdict().items():
                if v:
                    time_data[k] = int(v)
        if time_data:
            result["duration"] = timedelta(**time_data)
        return result, argument
