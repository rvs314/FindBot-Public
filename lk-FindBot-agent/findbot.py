
import asyncio
import heapq
import io
import multiprocessing as mp
import os
import pickle
import socket
import socketserver
import traceback
import typing
from dataclasses import dataclass
from typing import Never, Self

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")

from livekit.agents import JobContext
from livekit.agents.worker import Worker, WorkerOptions

import sheets
from data import dataset
from interview import Interview
from interviewer import Interviewer
from programmer import Programmer
from ranker import Ranker

if not os.path.exists("./test"):
    os.mkfifo("./test")

async def _select() -> Never:
    while True:
        try:
            fifo = open("./test", 'br')
            (convo, num) = pickle.load(fifo)
            
            notes = sheets.Notes.from_id(num)

            iv = Interview(convo, notes)
                
            programmer = Programmer(iv)
            listings = await programmer.query(dataset)
                
            ranked = await Ranker.rank_all(iv, listings)
                
            best = heapq.nlargest(5, ranked, key=lambda k: k[1].final_score)
                
            ending_status = f"COMPLETED: FindBot chose {', '.join(str(l.zpid) for (l, _) in best)}"
                
            iv.notes.status(ending_status)

            fifo.close()
        except Exception as e:
            sio = io.StringIO()
            iv.notes.status(f"FAILED: {e}")
            traceback.TracebackException.from_exception(e).print(file=sio)
            iv.notes.log(sio.getvalue())

@dataclass
class FindBot:

    def __init__(self: Self):
        pass

    def start(self):
        print('STARTING')
        pr = mp.Process(target=lambda: asyncio.run(_select()))
        pr.start()
        asyncio.run(self._interview())
        pr.join()

    @staticmethod
    async def on_job(ctx: JobContext):
        await ctx.connect()

        client = await ctx.wait_for_participant()

        iv = await Interviewer().run_interview(ctx, client)

        iv.notes.flush()

        with open("./test", 'bw') as fifo:
            pickle.dump((iv.convo, iv.notes.number), fifo)

        ctx.shutdown()


    async def _interview(self):
        await Worker(WorkerOptions(
            entrypoint_fnc=FindBot.on_job,
            ws_url=os.environ['LIVEKIT_URL'],
        )).run()

if __name__ == "__main__":
    from livekit.agents.cli.log import setup_logging
    setup_logging('INFO', True)

    FindBot().start()
