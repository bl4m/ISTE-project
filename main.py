from fastapi import FastAPI,Depends,WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from typing import Optional

from database import get_db_session,init_db, get_session_dependency
from models import Team,Player,Card
from auth import get_password_hash,verify_password,create_access_token,get_current_user,decode_access_token, get_current_user_from_cookie
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

get_session = get_session_dependency


init_db()

@app.get("/health")
async def root():
    return {"status": "ok"}


class SignupData(BaseModel):
    username: str
    password: str
    join_team_id: Optional[str] = None
    team_name: Optional[str] = None


class LoginData(BaseModel):
    username: str
    password: str


@app.post("/signup")
def signup(data: SignupData, session: Session = Depends(get_session)):
    existing = session.query(Player).filter(Player.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    try:
        hashed = get_password_hash(data.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    new_player = Player(username=data.username, hashed_password=hashed)

    # handle team join/create
    if data.join_team_id:
        team: Team = session.query(Team).filter(Team.id == data.join_team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        if len(team.players) >= 4:
            raise HTTPException(status_code=400, detail="Team is full")

        new_player.team_id = team.id
        new_player.team = team
    else:
        team = Team(name=data.team_name or f"Team {data.username}")
        session.add(team)
        session.flush()
        new_player.team_id = team.id
        new_player.team = team

    session.add(new_player)
    session.commit()
    session.refresh(new_player)
    session.refresh(team)
    return {"id": new_player.id, "username": new_player.username}


@app.post("/login")
def login(data: LoginData, session: Session = Depends(get_session)):
    player:Player = session.query(Player).filter(Player.username == data.username).first()
    if not player:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    try:
        ok = verify_password(data.password, player.hashed_password or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token({"sub": player.username})
    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        key="session_id",
        value=access_token,
        httponly=True,
        secure=False,  # set True in production when using HTTPS
        samesite="lax",
        max_age=60*60*24
    )
    return resp

active_connections = {}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # try query param first, fall back to cookie header
    token = websocket.query_params.get("token")
    if not token:
        cookie_header = websocket.headers.get("cookie", "")
        # simple cookie parse
        for part in cookie_header.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                if k == "session_id":
                    token = v
                    break

    if not token:
        await websocket.close(code=1008)
        return

    # validate token and load user with a short-lived session
    try:
        payload = decode_access_token(token)
    except Exception:
        await websocket.close(code=1008)
        return

    username = payload.get("sub")
    if not username:
        await websocket.close(code=1008)
        return

    with get_db_session() as session:
        player = session.query(Player).filter(Player.username == username).first()
        if not player:
            await websocket.close(code=1008)
            return
        # read primary key while the instance is attached so it won't trigger refresh later
        player_id = player.id

    await websocket.accept()
    active_connections[player_id] = websocket
    await websocket.send_text("WebSocket connection established.")

    try:
        while True:
            data = await websocket.receive_json()

            try:
                data["author_id"] = player_id
                card = Card.model_validate(data)
                await websocket.send_text(f"Received valid card: {card}")
                # persist each card in its own short session
                with get_db_session() as session:
                    session.add(card)
            except Exception as e:
                await websocket.send_json({
                    "error": "Validation failed",
                    "details": e.errors() if hasattr(e, "errors") else str(e)
                })

    except WebSocketDisconnect:
        print("Client disconnected")
        if player_id in active_connections:
            del active_connections[player_id]