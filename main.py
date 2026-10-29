from concurrent.futures import ThreadPoolExecutor
import os
from fastapi import FastAPI, Depends, HTTPException
from chat import run_chat_agent
from database import Base, engine, get_db, SessionLocal
import models
import schema
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langsmith import traceable
from fastapi.responses import StreamingResponse
from chat import run_chat_agent_stream
from fastapi.middleware.cors import CORSMiddleware
import time
from auth import router as auth_router
import oauth2
from hashing import Hash
import email_service
import security
from fastapi import BackgroundTasks
from fastapi import status, Response

load_dotenv()  

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")


app = FastAPI(
    title="IntelliChat API",
    description="AI chat backend: JWT login, email verification, private chats, "
                "tool-using LangGraph agent and streaming replies.",
    version="1.0.0",
)
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=list({FRONTEND_URL, "http://localhost:5173"}),   # live site + local development,
    allow_methods=["*"],
    allow_headers=["*"],
)


Base.metadata.create_all(bind=engine)   # when the app starts, create the tables in the database if they don't 

llm=init_chat_model("gemini-3.5-flash-lite", model_provider="google_genai")

title_executor = ThreadPoolExecutor(max_workers=4)



def get_conversation_history(conversation_id: str, db: Session, limit: int = 10,user: models.User = Depends(oauth2.get_current_user)) -> list:
    """Last `limit` messages of a chat, oldest first, in the format the LLM expects."""

    messages = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.timestamp.desc())  
        .limit(limit)                                  
        .all()
    )
    messages.reverse()   
    return [{"role": m.role, "content": m.content} for m in messages]


@app.post("/users", status_code=201, response_model=schema.UserResponse,tags=["Users"], summary="Create an account")
def create_user(request: schema.SignupRequest,background_tasks: BackgroundTasks,db: Session = Depends(get_db)):
    """Sign up with email and password. A verification link is emailed, and login stays blocked until the email is verified."""
    email = request.email.lower()
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
 
    db_user = models.User(email=email, password=Hash.bcrypt(request.password), is_verified=False)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
 
    token = security.create_verify_token(db_user.email)
    frontend = os.getenv("FRONTEND_URL", "http://localhost:5173")
    link = f"{frontend}/verify-email?token={token}"
    background_tasks.add_task(email_service.send_verification_email, db_user.email, link)
    return db_user



@app.patch("/conversations/{conversation_id}", response_model=schema.ConversationResponse,tags=["Chats"], summary="Rename a chat")
def rename_conversation(conversation_id: str, request: schema.ConversationUpdate, db: Session = Depends(get_db),user: models.User = Depends(oauth2.get_current_user)):
    """Rename one of my chats. Returns 404 if the chat is not mine."""
    conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id,models.Conversation.user_email == user.email).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    new_title = request.title.strip()
    if not new_title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    conversation.title = new_title
    db.commit()
    db.refresh(conversation)
    return conversation

@app.delete("/conversations/{conversation_id}", tags=["Chats"], summary="Delete a chat")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db),user: models.User = Depends(oauth2.get_current_user)):
    """Delete one of my chats together with all its messages. Returns 404 if the chat is not mine."""

    conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id,models.Conversation.user_email == user.email).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(conversation)
    db.commit()
    return {"message": "Conversation deleted", "conversation_id": conversation_id}


@app.get("/conversations", tags=["Chats"], summary="List my chats")
def get_user_conversations(db: Session = Depends(get_db),user: models.User = Depends(oauth2.get_current_user)):
    """All chats of the logged-in user, oldest first."""

    conversations = (
        db.query(models.Conversation)
        .filter(models.Conversation.user_email == user.email)
        .order_by(models.Conversation.created_at.asc())
        .all()
    )
    return conversations


 
 






def generate_title(first_message: str) -> str:
    """Make a short, meaningful title from the first message of a chat."""
    # title_prompt = f"Summarize this message into a short 3-5 word title (no quotes, no punctuation): {first_message}.By default the title should be in english, but if the message is in a different language, then generate the title in that language."
    title_prompt = (
    "Write a short chat title of 3 to 5 words for the message below.\n"
    "Rules:\n"
    "- Use the SAME language and the SAME script as the message.\n"
    "- If the message is Hindi written in English letters (Hinglish), write the title in Hinglish.\n"
    "- If the message is in Devanagari, write the title in Devanagari.\n"
    "- Use English only when the message is in English.\n"
    "- Name the TOPIC of the message. Do not copy the question words.\n"
    "- Skip filler words like kya, hai, hoti, samjhao, please, explain.\n"
    "- No quotes, no punctuation. Reply with the title only.\n\n"
    "Examples:\n"
    "Message: mujhe python decorators samjhao -> Python decorators ki jaankari\n"
    "Message: networking kya hoti hain ise samjhao -> Networking ki basic jaankari\n"
    "Message: what is RAG -> RAG explained\n\n"
    f"Message: {first_message}\n"
    "Title:"
)
    response = llm.invoke(title_prompt)   
    content = response.content
    #here content can be a list of dicts or a string, so we need to handle both cases because in database we can store only string
    if isinstance(content, list):
        content = content[0]["text"]
    return content.strip()




def save_title_when_ready(conversation_id, future):
    if future.exception() is not None:
        print(f"[title] failed: {future.exception()!r}")
        return
    db = SessionLocal()        
    try:
        conversation = (
            db.query(models.Conversation)
            .filter(models.Conversation.id == conversation_id)
            .first()
        )
        if conversation:
            conversation.title = future.result()
            db.commit()
    finally:
        db.close()

     

@app.post("/conversations/{conversation_id}/chat", tags=["AI Chat"],summary="Send a message and get the full answer")
@traceable(name="chat_in_conversation")  
def chat_in_conversation(conversation_id: str, request: schema.MessageCreate, db: Session = Depends(get_db),user: models.User = Depends(oauth2.get_current_user)):
    """Send a message to one of my chats and get the whole answer at once (no streaming)."""

    conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id, models.Conversation.user_email == user.email).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    existing_messages_count = db.query(models.Message).filter(models.Message.conversation_id == conversation_id).count()
    if existing_messages_count == 0:
        new_title = generate_title(request.content)
        conversation.title = new_title
        db.commit()

    #first i want get history from based on converstaion id 
    history = get_conversation_history(conversation_id, db,10)   # it return a lsit of human message and ai message

    user_message = models.Message(
        conversation_id=conversation_id,
        role="user",
        content=request.content,
    )
    db.add(user_message)
    db.commit()

    answer = run_chat_agent(request.content,history)   

    ai_message = models.Message(
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
    )
    db.add(ai_message)
    db.commit()

    return {"answer": answer}


@app.get("/conversations/{conversation_id}/messages", tags=["Chats"], summary="Get messages of a chat")
def get_conversation_messages(conversation_id: str, db: Session = Depends(get_db),user: models.User = Depends(oauth2.get_current_user)):
    """All messages of one of my chats, oldest first. Returns 404 if the chat is not mine."""

    conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id, models.Conversation.user_email == user.email).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.timestamp.asc())
        .all()
    )
    # we can also use this statement
    # messages = db.query(model.Message).filter_by(conversation_id=conversation_id).order_by(model.Message.timestamp.asc()).all()
    return messages




@app.post("/chat/new", response_model=schema.NewChatResponse,tags=["AI Chat"], summary="Start a new chat with its first message")
@traceable(name="start_new_chat")
def start_new_chat(request: schema.NewChatRequest,db: Session = Depends(get_db),user: models.User = Depends(oauth2.get_current_user)):
    """Create a chat, give it an AI-made title, save the first message and return the full answer."""

    user = db.query(models.User).filter(models.User.email == user.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")


    db_conversation = models.Conversation(
        user_email=user.email,
        title="New Chat",
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    conversation_id = db_conversation.id


    title_future = title_executor.submit(generate_title, request.content)

    user_message = models.Message(
        conversation_id=conversation_id,
        role="user",
        content=request.content,
    )
    db.add(user_message)
    db.commit()
    answer = run_chat_agent(request.content)
    ai_message = models.Message(
        conversation_id=db_conversation.id,
        role="assistant",
        content=answer,
    )
    db.add(ai_message)
    db.commit()
    title="New Chat"  
    try:
        title = title_future.result(timeout=5)
        db_conversation.title = title
        db.commit()
    except Exception:
        if not title_future.done():
            title_future.add_done_callback(
                lambda f: save_title_when_ready(conversation_id, f)
            )


    return {
        "conversation_id": db_conversation.id,
        "title": title,
        "answer": answer,
    }



@app.post("/conversations/{conversation_id}/chat/stream", tags=["AI Chat"],summary="Send a message and stream the answer")
def chat_stream(conversation_id: str, request: schema.MessageCreate, db: Session = Depends(get_db),user: models.User = Depends(oauth2.get_current_user)):
    """Send a message to one of my chats; the answer arrives piece by piece as it is written. The ownership check runs before the stream starts."""
    conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id, models.Conversation.user_email == user.email).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    history = get_conversation_history(conversation_id, db)

    db.add(models.Message(conversation_id=conversation_id, role="user", content=request.content))
    db.commit()

    def generate():
        full_answer = ""
        for chunk in run_chat_agent_stream(request.content, history):
            full_answer += chunk
            yield chunk

        db.add(models.Message(conversation_id=conversation_id, role="assistant", content=full_answer))
        db.commit()

    return StreamingResponse(generate(), media_type="text/event-stream")



@app.delete("/users/me",status_code=status.HTTP_204_NO_CONTENT,tags=["Users"],summary="Delete my account and all my chats")
def delete_my_account(db: Session = Depends(get_db),user: models.User = Depends(oauth2.get_current_user)):
    """Logged-in user apna account delete karta hai. Chats aur messages cascade se apne aap delete hote hain."""
 
    user = db.query(models.User).filter(models.User.email == user.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
 
    db.delete(user)      
    db.commit()
 
    return Response(status_code=status.HTTP_204_NO_CONTENT)


