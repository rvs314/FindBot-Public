# FindBot

FindBot is a basic example of a multimodal voice agent using LiveKit and the Python [Agents Framework](https://github.com/livekit/agents).

## Dev Setup

Set up the environment by filling the required values into `.env.local`:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `OPENAI_API_KEY`
- `DATASET_PATH`

Run the agent:

```console
python3 agent.py dev
```

This agent requires a frontend application to communicate with. The sandbox which FindBot uses is [here](https://crypto-protocol-1cnzgp.sandbox.livekit.io).

## Architecture

FindBot is made up of three AI agents:
- The Interviewer: A voice model, which conducts the interview with the user. Currently based on OpenAI's realtime model via LiveKit
- The Programmer: A text model, which constructs a query over the database. Currently uses OpenAI's 4o model
- The Selector: An image+text model which evaluates the results of the database query. Currently uses OpenAI's 4o-mini model

