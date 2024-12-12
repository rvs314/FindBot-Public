import asyncio
import typing
from asyncio import Future
from typing import Callable

from livekit.agents import JobContext
from livekit.agents.llm.chat_context import ChatContent, ChatMessage
from livekit.agents.multimodal import MultimodalAgent
from livekit.plugins.openai.realtime import RealtimeModel, ServerVadOptions
from livekit.rtc import RemoteParticipant
from openai.types.chat import (ChatCompletionContentPartParam,
                               ChatCompletionMessageParam)

import log
from interview import Interview
from oai import Conversation
from sheets import Notes
from utils import panic


def convert(chatmsg: ChatMessage) -> ChatCompletionMessageParam:
    def convert_part(part: ChatContent) -> ChatCompletionContentPartParam:
        if isinstance(part, str):
            return { "type": "text", "text": part }
        else:
            return panic("Non-text chat audio cannot be converted")

    contents = chatmsg.content if isinstance(chatmsg.content, list) else \
               [] if chatmsg.content is None else \
               [chatmsg.content]

    return typing.cast(ChatCompletionMessageParam,
                       { "role": chatmsg.role,
                         "content": [convert_part(c) for c in contents] })



class Interviewer(RealtimeModel):
    INSTRUCTIONS = """
You are FindBot, an AI voice agent whose role is to help users find their ideal rental apartment in the Manhattan borough of New York City. You are approachable and easy to talk to. To that end, you are interviewing the user in order to get a sense of what they want out of a potential apartment. Don't ask for too many pieces of information at once. By the end of the conversation, you should know all the basic facts about the user's desired apartment: rental amounts, size, location, furnishing, etc. However, you should let the conversation flow naturally. When you ask a question and they give a response, don't parrot what they said back to them. Build on it, asking them relevant follow-up questions. To this end, get to know the user: Why are they moving to New York? What do they do for a living? Do they have kids? What about pets? Your goal is to get a sense of what the user values in a living space, not just a set of search constraints. Don't be afraid to ask questions that aren't immediately relevant to the task. Take as much time as the user will allow you: this will be the only dialogue you have with the user, so gather a comprehensive idea of their preferences. Once you believe you have had enough information, describe back to them what you think preferences are and ask if you got everything correct. The user has the ability to end the conversation, so if the conversation comes to a natural conclusion, tell them to press the end-conversation button, which is a red 'x'. 
"""

    INITIAL_MESSAGE = ChatMessage(
            role="assistant",
            content="Begin the conversation with the user. Introduce yourself, ask for their name, then move on to the interview."
        )

    def __init__(self):
        super().__init__(instructions=self.INSTRUCTIONS,
                         voice="ash",
                         turn_detection=ServerVadOptions(
                             threshold=0.6, prefix_padding_ms=200, silence_duration_ms=500
                         ))

    def run_interview(self, ctx: JobContext, participant: RemoteParticipant) -> Future[Interview]:
        notes = Notes()

        notes.status(f"Interviewing {participant.name}")

        agent = MultimodalAgent(model=self)
        agent.start(ctx.room, participant)

        session = self.sessions[-1]

        session.conversation.item.create(self.INITIAL_MESSAGE)
        session.response.create()

        future = asyncio.get_event_loop().create_future()

        @ctx.room.on("participant_disconnected")
        def on_disconnect(who_left: RemoteParticipant):
            if who_left.identity != participant.identity: return

            notes.status(f"Finished Interviewing #{who_left.identity}")

            msgs = session.chat_ctx_copy().messages

            for msg in msgs:
                notes.log(f"{msg.role}: {msg.content}")

            future.set_result(Interview([convert(c) for c in msgs], notes))

        return future


