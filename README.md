# RAG - Chatbot Rainbow Six Siege

API FastAPI qui fait tourner un chatbot RAG (Retrieval-Augmented Generation) spécialisé sur Rainbow Six Siege. Le bot répond aux questions en s'appuyant sur un guide PDF, garde un historique de conversation par utilisateur, et le tout est protégé par une authentification JWT classique.

Il n'y avait pas de README dans le dépôt, ce document a été écrit en lisant le code (`main.py`, `history.py`, `authentication.py`, `user.py`, `models.py`, etc.).

## Stack

- FastAPI + Uvicorn
- SQLAlchemy / SQLite pour les users et l'historique
- Redis pour la mémoire de conversation (via langchain-redis)
- LangChain pour l'orchestration du RAG
- Groq (llama-3.3-70b-versatile) comme LLM
- FAISS pour la recherche vectorielle
- HuggingFace (all-MiniLM-L6-v2) pour les embeddings
- JWT (python-jose) + bcrypt (passlib) pour l'auth

## Architecture

```
                      Client
                        │
                        │ HTTP
                        ▼
                   FastAPI API
                        │
            ┌───────────┼───────────┐
            │           │           │
            ▼           ▼           ▼
     Authentification  Users     History
          (JWT)          │           │
                          ▼           ▼
                       SQLite      Redis


Question utilisateur
          │
          ▼
   Authentification (JWT)
          │
          ▼
      RAG Pipeline
          │
          ├── PDF (guide_r6.pdf)
          │      ↓
          │   Chunking
          │      ↓
          │   Embeddings
          │      ↓
          │   FAISS
          │      ↓
          │   Top-K documents
          │
          ▼
        Groq
   Llama 3.3 70B
          │
          ▼
   Réponse générée
          │
    ┌─────┴─────┐
    ▼           ▼
 SQLite       Redis
(historique) (conversation)
```

L'authentification passe par SQLite (table `users`), le pipeline RAG passe par le PDF + FAISS + Groq, et chaque échange finit stocké à la fois dans SQLite (table `messages`, pour la persistance) et dans Redis (pour que le LLM garde le contexte de la conversation d'une requête à l'autre).

## Structure du projet

```
RAG/
├── main.py            → point d'entrée, montage des routers, CORS
├── database.py         → moteur SQLAlchemy, session, Base
├── models.py            → modèles User / Message
├── schemas.py             → schémas Pydantic
├── hashing.py               → hash / vérif des mots de passe (bcrypt)
├── JWTtoken.py                → création des tokens JWT
├── oauth2.py                    → décodage du token, user courant
├── authentication.py              → route /login
├── user.py                         → routes /User (CRUD)
├── history.py                       → route /History (RAG + historique)
├── guide_r6.pdf                       → source de connaissances du RAG
├── rag.db                              → base SQLite (générée au démarrage)
└── requirements.txt
```

À noter : `main.py` importe `from routers import user, history, authentication` et `history.py` charge `routers/guide_r6.pdf`. Dans la vue racine du dépôt ces fichiers apparaissent à plat, donc soit ils sont en fait dans un dossier `routers/`, soit les imports sont à corriger pour que l'app démarre.

## Installation

```bash
git clone https://github.com/paulcoffi/RAG.git
cd RAG

python -m venv venv
source venv/bin/activate   # venv\Scripts\activate sous Windows

pip install -r requirements.txt
```

Le `requirements.txt` du dépôt est en fait un export complet d'un environnement Conda (485 lignes, avec Jupyter, Spyder, etc. dedans). Ça marche mais c'est très lourd pour rien. Dans les faits, ce dont l'app a vraiment besoin c'est :

```
fastapi
uvicorn
sqlalchemy
pydantic
passlib[bcrypt]
python-jose
python-multipart
python-dotenv
langchain
langchain-community
langchain-core
langchain-groq
langchain-huggingface
langchain-redis
langchain-text-splitters
faiss-cpu
redis
sentence-transformers
pypdf
```

## Configuration

Un serveur Redis doit tourner (local ou distant), et une clé API Groq est nécessaire pour appeler le LLM.

Fichier `.env` à créer à la racine :

```env
REDIS_URL=redis://localhost:6379
GROQ_API_KEY=votre_cle_groq
```

Seule `REDIS_URL` est lue explicitement dans le code via `os.getenv`. `GROQ_API_KEY` est la variable standard attendue par `langchain-groq`, il faut vérifier qu'elle est bien récupérée automatiquement.

## Lancer l'app

```bash
uvicorn main:app --reload
```

Au démarrage, les tables SQL sont créées automatiquement (`Base.metadata.create_all`). L'API tourne sur `http://127.0.0.1:8000`, avec le swagger sur `/docs`.

## Endpoints

### POST /login/

Auth classique OAuth2 form (`username` = l'email, `password`). Retourne un access token JWT valable 180 minutes.

```json
{
  "access_token": "eyJhbGciOi...",
  "token-type": "bearer"
}
```
404 si l'utilisateur n'existe pas, 401 si le mot de passe est faux.

### /User

- `POST /User/` — crée un utilisateur (`username`, `email`, `password`)
- `GET /User/{id}` — récupère un utilisateur
- `PUT /User/{id}` — change le username (demande le password actuel)
- `PUT /User/{id}` — change le password (demande l'ancien password)
- `DELETE /User/{id}` — supprime un utilisateur

Deux remarques sur ces routes :
- les deux `PUT /User/{id}` ont la même signature, donc une seule des deux est réellement joignable, il faut leur donner des chemins différents.
- aucune de ces routes n'est protégée par le JWT (`oauth2.get_current_user` n'est pas branché dessus), donc n'importe qui avec un ID peut lire, modifier ou supprimer un compte.

### /History (protégé, header `Authorization: Bearer <token>`)

- `POST /History/` — pose une question au chatbot, retourne la réponse en texte brut
- `POST /History/delete_redis/` — vide l'historique Redis de l'utilisateur courant

```json
{ "message": "Comment défendre Bank en attaque ?" }
```

## Le pipeline RAG en détail

À chaque appel de `POST /History/` :

1. le PDF `guide_r6.pdf` est chargé (`PyPDFLoader`)
2. il est découpé en chunks de 100 caractères, avec 100 de chevauchement
3. chaque chunk est vectorisé avec `all-MiniLM-L6-v2` (CPU)
4. un index FAISS est reconstruit en mémoire à partir de ces vecteurs
5. les 4 passages les plus proches de la question sont récupérés
6. un prompt système (en français, spécialisé R6 Siege) est construit avec ce contexte + l'historique
7. Groq (`llama-3.3-70b-versatile`, température 0) génère la réponse
8. la mémoire de conversation passe par Redis via `RunnableWithMessageHistory`, la session est indexée sur l'ID utilisateur, et seuls les 50 derniers messages sont gardés au-delà de 2
9. la question et la réponse sont sauvegardées dans SQLite

Le vrai problème ici : les étapes 1 à 4 (chargement du PDF, chunking, embeddings, FAISS) sont refaites à chaque question. Ça marche mais c'est lent et ça coûte cher pour rien — l'index devrait être construit une fois au démarrage et réutilisé.

## Modèle de données

**users**

| champ | type |
|---|---|
| id | int, PK |
| username | str, unique |
| email | str |
| password | str (haché bcrypt) |

**messages**

| champ | type |
|---|---|
| id | int, PK |
| user_message | str |
| ai_message | str |
| user_id | int, FK → users.id |
