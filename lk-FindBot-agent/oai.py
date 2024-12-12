
import openai
from openai.types.chat import ChatCompletionMessageParam


client = openai.AsyncOpenAI()
Conversation = list[ChatCompletionMessageParam]
