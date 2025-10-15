from fastapi import APIRouter, Depends, status, HTTPException, Response
import schemas, models
from sqlalchemy.orm import Session
from database import get_db
from hashing import Hashing
from JWTtoken import create_access_token
from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter(tags=['Login'], prefix='/login')

@router.post('/')

def login(response: Response, request: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):

    query = db.query(models.User).filter(models.User.email == request.username)

    data = query.first()

    if not data:

        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Utilisateur introuvable")
    
    if not Hashing.verify(request.password, data.password):

        raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED, detail = "Mot de passe incorrect")
    
    access_token = create_access_token(
        data={"sub": data.email})   

    return {"access_token": access_token, "token-type": "bearer"}