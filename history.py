from fastapi import APIRouter, Depends, status, HTTPException
import schemas, models
from sqlalchemy.orm import Session
from database import get_db
from hashing import Hashing
import os
from dotenv import load_dotenv
import langchain
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_redis import RedisChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import oauth2

load_dotenv()

def get_redis_history(session_id: str) -> BaseChatMessageHistory:

    history = RedisChatMessageHistory(session_id, redis_url=REDIS_URL)

    all_message = history.messages

    if len(all_message) > 2:

        history.clear()

        for msg in all_message[-50:]:

            if type(msg).__name__ == "AIMessage":

                history.add_ai_message(msg)
            
            else:

                history.add_user_message(msg)

    return history

import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
print(f"Connecting to Redis at: {REDIS_URL}")

router = APIRouter(tags = ['History'], prefix = "/History")

@router.post('/')

def ask_chatbot(request: schemas.Message, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):

    llm = ChatGroq(model = "llama-3.3-70b-versatile", temperature = 0, max_tokens = 1024)

    loader = PyPDFLoader("routers/guide_r6.pdf")

    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size = 100, chunk_overlap = 100)

    text_splitted = splitter.split_documents(docs)

    embedding = HuggingFaceEmbeddings(model_name = "sentence-transformers/all-MiniLM-L6-v2", model_kwargs={"device": "cpu"})

    vector_store = FAISS.from_documents(text_splitted, embedding)

    question = request.message

    retrieved_docs = vector_store.similarity_search(question, k = 4)


    prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "Tu es un agent IA spécialisé pour répondre à des questions sur le jeu vidéo Rainbow Six Siege encore appelé siege ou R6 à partir de ce contexte {context}"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])

    chain = prompt | llm

    chain_with_history = RunnableWithMessageHistory(
    chain, get_redis_history, input_messages_key="input", history_messages_key="history")

    response = chain_with_history.invoke(
    {"context": retrieved_docs,"input": question},
    config={"configurable": {"session_id": str(current_user.id)}})

    new = models.Message(user_message = question, ai_message = response.content, user_id = current_user.id)

    db.add(new)

    db.commit()

    db.refresh(new)

    return response.content

@router.post('/delete_redis/')

def delete_redis_history(current_user: models.User = Depends(oauth2.get_current_user)):

    history = RedisChatMessageHistory(session_id = str(current_user.id), redis_url=REDIS_URL)

    history.clear()

    return "Historique supprimé"