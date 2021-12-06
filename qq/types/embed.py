from typing import List, TypedDict


class EmbedField(TypedDict, total=False):
    name: str
    value: str


class Embed(TypedDict, total=False):
    title: str
    description: str
    prompt: str
    timestamp: str
    fields: List[EmbedField]