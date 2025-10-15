from passlib.context import CryptContext

pwd_cxt = CryptContext(schemes=["bcrypt"], deprecated ='auto')

class Hashing:

    def hash(password):

        return pwd_cxt.hash(password)
    
    def verify(plain_pwd, encoded_pwd):

        return pwd_cxt.verify(plain_pwd, encoded_pwd)