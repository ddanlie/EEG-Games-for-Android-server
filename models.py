from pydantic import BaseModel

# class Item(BaseModel):
#     name: str
#     description: str | None = None


# class ItemResponse(BaseModel):
#     id: int
#     name: str
#     description: str | None = None


class UserIdentity(BaseModel):
    token: str
    userId: str

class EmailCodeRequest(BaseModel):
    email: str
    code: str

class EmailRequest(BaseModel):
    email: str
