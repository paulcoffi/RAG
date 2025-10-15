from pydantic import BaseModel

class User(BaseModel):

    username: str
    email: str
    password: str

class showUser(BaseModel):

    username: str
    email: str

    class Config():

        orm_mode = True

class updateUsername(BaseModel):

    password: str
    new_username: str

class updatePassword(BaseModel):

    old_password: str
    new_password: str

class Message(BaseModel):

    message: str

class showMessage(BaseModel):

    message: str

    class Config():

        orm_mode = True

class Login(BaseModel):

    username: str

    password: str 

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None