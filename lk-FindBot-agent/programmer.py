
from typing import Self

from pydantic import BaseModel, Field

from data import Listing, Listings
from interview import Interview
from maps import geocode, includes
from textagent import TextAgent


class Neighborhood(BaseModel):
    """
    A neighborhood, district, or general area in Manhattan.
    """
    name: str = Field(description="The name of the neighborhood. For example, 'Chelsea', 'The Financial District', 'Chinatown', etc")

class ApartmentQuery(BaseModel):
    @classmethod
    def ANY(cls) -> Self:
        return cls(
            minimum_rent = 0,
            maximum_rent = None,
            minimum_bathrooms = 0,
            minimum_bedrooms = 0,
            neighborhoods = None
        )

    minimum_rent : int = Field(
        description="The minimum rent the user is willing to pay. This should never be negative.")
    maximum_rent : int | None = Field(description="The maximum rent the user is willing to pay or `null` if there is no maximum. This should never be negative.")

    minimum_bathrooms : int = Field(description="The minimum number of bathrooms the user wants in their apartment. This should never be negative.")
    minimum_bedrooms : int = Field(description="The minimum number of bedrooms the user wants in their apartment. This should never be negative.")

    neighborhoods : list[Neighborhood] | None = Field(description="A complete list of neighborhoods in which the user may be interested or `null` if the user has no specific neighborhood in mind.")

    def matches(self, lst: Listing) -> bool:
        well_priced = self.minimum_rent <= lst.price <= (self.maximum_rent or lst.price)

        well_fit = (self.minimum_bathrooms <= lst.bathrooms
                    and self.minimum_bedrooms <= lst.bedrooms)

        well_placed = (self.neighborhoods is None
                       or any(includes(loc['geometry'], lst)
                              for hood in self.neighborhoods
                              for loc in geocode(hood.name)))

        return well_priced and well_fit and well_placed



class Programmer(TextAgent):
    INSTRUCTIONS = """
Your interview has now concluded. Your next task is to generate a set of constraints over possible apartments. These should help limit the search space of possible apartments to those the user may possibly be interested in. These constraints should be relatively loose: it is better to include apartments the user would be uninterested in than remove ones which they would be interested in.
    """

    def __init__(self, it: Interview):
        super().__init__(init=it.convo, notes=it.notes)

        self.system(self.INSTRUCTIONS)

    async def write_query(self) -> ApartmentQuery:
        parse = await self.generate_to_spec(ApartmentQuery)

        if not parse:
            if self.notes:
                self.notes.log(f"ERROR: Failed to parse apartment query: {parse}")
            return ApartmentQuery.ANY()

        return parse

    def search_dataset(self, dataset: Listings, query: ApartmentQuery) -> Listings:
        return Listings([l for l in dataset.root if query.matches(l) ])

    async def query(self, dataset: Listings, retries=5, min=5, max=100) -> Listings:

        if self.notes:
            self.notes.status("Query is begin generated.")

        for i in range(retries):
            qry = await self.write_query()
            res = self.search_dataset(dataset, qry)

            if min <= len(res.root) <= max:
                if self.notes: self.notes.status(f"Query Generated: {len(res.root)} apartments found")
                return res
            elif min > len(res.root):
                self.system("This query is too tight - it restricts the set of available apartments too heavily. Try again.")
            elif max < len(res.root):
                self.system("This query is too loose - it doesn't restrict the set of available apartments enough. Try again.")

        if self.notes:
            self.notes.log(
                f"Failed to find an appropraite apartment set after {retries} tries, returning {len(res.root)} entries")

        return res
