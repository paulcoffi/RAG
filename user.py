from fastapi import APIRouter, Depends, status, HTTPException
import schemas, models
from sqlalchemy.orm import Session
from database import get_db
from hashing import Hashing
import oauth2

router = APIRouter(tags=['User'], prefix='/User')

@router.post('/', response_model= schemas.showUser)

def create_user(request: schemas.User, db: Session = Depends(get_db)):

    query = db.query(models.User).filter(models.User.username == request.username).first()

    if query:

        raise HTTPException(status_code = status.HTTP_409_CONFLICT, detail = "Utilisateur existant")

    new = models.User(username = request.username, email = request.email, password = Hashing.hash(request.password))

    db.add(new)

    db.commit()

    db.refresh(new)

    return new

@router.get('/{id}', response_model = schemas.showUser)
def get_user(id: int, db: Session = Depends(get_db)):

    data = db.query(models.User).filter(models.User.id == id).first()

    if not data:

        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    return data

@router.put('/{id}', response_model= schemas.showUser)
def update_username(id: int, request: schemas.updateUsername, db: Session = Depends(get_db)):

    query = db.query(models.User).filter(models.User.id == id)

    data = query.first()

    if not data:

        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Utilisateur introuvable")
    
    if not Hashing.verify(request.password, data.password):

        raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED, detail = "Mot de passe incorrect")
    
    data.username = request.new_username

    db.commit()

    db.refresh(data)

    return data

@router.put('/{id}')
def update_password(id: int, request: schemas.updatePassword, db: Session = Depends(get_db)):

    query = db.query(models.User).filter(models.User.id == id)

    data = query.first()

    if not data:

        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Utilisateur introuvable")
    
    if not Hashing.verify(request.old_password, data.password):

        raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED, detail = "Mot de passe incorrect")
    
    data.password = request.new_password

    return "Mot de passe modifié"

@router.delete('/{id}', response_model = schemas.showUser)

def delete_user(id: int, db: Session = Depends(get_db)):

    query = db.query(models.User).filter(models.User.id == id)

    data = query.first()

    if not data:

        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Utilisateur introuvable")
    
    db.delete(data)

    db.commit()

    return data