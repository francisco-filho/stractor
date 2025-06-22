from pydantic import BaseModel

class Function(BaseModel):
    name: str
    parameters: str | None
    return_type: str | None
    documentation: str | None
    body: str | None

class Entity(BaseModel):
    name: str
    type: str = 'class'
    documentation: str | None
    methods: list[Function]

class SourceFile(BaseModel):
    path: str
    documentation: str | None
    imports: list[str] = []
    top_level_attributes: list[str] = []
    top_level_functions: list[Function]
    entities: list[Entity]

