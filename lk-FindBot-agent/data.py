
from os import getenv
from typing import Annotated, Literal, Optional

from pydantic import (AnyUrl, BaseModel, Field, NonNegativeFloat,
                      NonNegativeInt, RootModel, StringConstraints)

from utils import panic

Zipcode = Annotated[str, StringConstraints(pattern="^\\d{5}$")]

class Address(BaseModel):
    city: Literal['New York']
    state: Literal['NY']
    zipcode: Zipcode
    street_address: str = Field(alias='streetAddress')

class Property(BaseModel):
    title: str
    values: list[str]

    def summarize(self) -> str:
        nl = '\n'
        return f"""
        {self.title}:
        {nl.join('- ' + value for value in self.values)}
        """

class Photo(BaseModel):
    class MixedSource(BaseModel):
        class PhotoLink(BaseModel):
            url: AnyUrl
            width: NonNegativeInt

        jpeg: list[PhotoLink]

    mixedSources: MixedSource

class School(BaseModel):
    distance: NonNegativeFloat
    rating: Optional[NonNegativeInt] = None
    link: AnyUrl
    grades: str
    level: str
    type: str
    name: str

    def summarize(self) -> str:
        return f"{self.name} - {self.type} {self.level} school, grades {self.grades}. Ranking: {self.rating}"

class Listing(BaseModel):
    address: Address
    bedrooms: NonNegativeInt
    bathrooms: NonNegativeInt
    price: NonNegativeInt
    zipcode: Zipcode
    photos: list[Photo]
    description: str
    schools: list[School]
    longitude: float
    latitude: float
    zpid: NonNegativeInt
    properties: list[Property] = Field(alias='property')

    def summarize(self) -> str:
        nl = '\n'
        return f"""
        Address: {self.address.street_address}, {self.zipcode}
        Bedrooms: {self.bedrooms}
        Bathrooms: {self.bathrooms}
        Price: {self.price}
        {nl.join(map(Property.summarize, self.properties))}
        Nearby Schools:
        {nl.join("- " + school.summarize() for school in self.schools)}
        Listing Description: {self.description}
        """

    def __eq__(self, other):
        if isinstance(other, Listing):
            return self.zpid == other.zpid
        else:
            return NotImplemented

    def __hash__(self):
        return self.zpid

Listings = RootModel[list[Listing]]

dataset = Listings.parse_file(getenv("DATASET_PATH") or panic())
