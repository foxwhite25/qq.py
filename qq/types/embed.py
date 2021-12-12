from typing import List, TypedDict, Optional


class EmbedField(TypedDict, total=False):
    name: str
    value: str


class Embed(TypedDict, total=False):
    title: str
    description: str
    prompt: str
    timestamp: str
    fields: List[EmbedField]


class ArkObjKv(TypedDict, total=False):
    key: str
    value: str


class ArkObj(TypedDict, total=False):
    obj_kv: List[ArkObjKv]


class ArkKv(TypedDict, total=False):
    key: str
    value: Optional[str]
    obj: Optional[List[ArkObj]]


class Ark(TypedDict, total=False):
    template_id: int
    kv: List[ArkKv]
