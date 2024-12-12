
import heapq
from functools import lru_cache
from typing import Self

import openai
from openai.types.chat import (ChatCompletionContentPartImageParam,
                               ChatCompletionContentPartTextParam,
                               ChatCompletionUserMessageParam)
from pydantic import AnyUrl, BaseModel, Field

from data import Listing, Listings, Photo
from interview import Interview
from sheets import Notes
from textagent import TextAgent


class ListingScore(BaseModel):
    benefits : list[str] = Field(description="Things the user would like about this apartment, each five words or fewer.")
    drawbacks : list[str] = Field(description="Things the user would dislike about this apartment, each five words or fewer.")
    final_score : float = Field(description="A score representing how interested the user would be in this apartment, on a scale from 0 to 100")


class Ranker(TextAgent):
    INSTRUCTIONS = """
Your interview has now concluded. Your next task is to rate the following apartment based on the user's preferences. You should give reasoning by listing a set of benefits (things the user would like about the apartment) and a set of drawbacks (things the user would dislike about the apartment). Incorporate both of those pieces of reasoning into a final score, which is a floating point number between zero and one hundred.
"""

    def __init__(self, it: Interview):
        super().__init__(init=it.convo, model="gpt-4o-mini", notes=it.notes)

        self.system(self.INSTRUCTIONS, noteworthy=False)

    async def rank(self, lst: Listing) -> ListingScore | None:
        def good_photo(photo: Photo) -> AnyUrl | None:
            links = photo.mixedSources.jpeg

            best = min(links, key=lambda l: abs(450 - l.width), default=None)
            return None if best is None else best.url

        images : list[ChatCompletionContentPartTextParam | ChatCompletionContentPartImageParam] = [
            {"type": "image_url",
             "image_url": {"url": str(good_photo(photo)), "detail": "low"}}
            for photo in lst.photos[:10]
            if good_photo(photo) is not None
        ]

        text : list[ChatCompletionContentPartTextParam | ChatCompletionContentPartImageParam] = [
            { "type": "text",
              "text": lst.summarize() }
        ]

        listing_message : ChatCompletionUserMessageParam = {
            "role": "user",
            "content": text + images
        }

        self.user(listing_message, noteworthy=False)

        try:
            score = await self.generate_to_spec(ListingScore, noteworthy=False)
        except openai.BadRequestError as brq:
            if brq.code != "invalid_image_url": raise brq
            self.notes.log(f"ERROR: invalid image URL for listing {lst.zpid}")
            return None

        if not score:
            self.notes.log("ERROR: Failed to generate listing score")
            return None

        self.notes.log(f"{lst.zpid} ({score.final_score}) - Benefits: {score.benefits} | Drawbacks: {score.drawbacks}")

        return score

    @classmethod
    async def rank_all(cls: type[Self], it: Interview, listings: Listings) -> list[tuple[Listing, ListingScore]]:
        it.notes.status("Started Ranking")

        res = []

        for listing in listings.root:
            ranker = cls(it)
            rnk = await ranker.rank(listing)
            if rnk: res.append((listing, rnk))

        return res

    @classmethod
    async def top(cls, it: Interview, listings: Listings, count=5) -> list[tuple[Listing, ListingScore]]:
        return heapq.nlargest(count, await cls.rank_all(it, listings), key=lambda k: k[1].final_score)

