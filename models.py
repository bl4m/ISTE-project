from enum import Enum
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import Column, Enum as SAEnum, JSON
from sqlmodel import Field, Relationship, SQLModel
from pydantic import BaseModel


# Authentication will use `Player` model only — no separate `User` model.

class CardType(str, Enum):
    Task = "Task"
    Attack = "Attack"
    Backstab = "Backstab"
    Suspicion = "Suspicion"
    Alliance = "Alliance"


class Team(SQLModel, table=True):
    """Combined SQLModel (Pydantic + SQLAlchemy) model for teams."""

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True, index=True)
    name: str = Field(nullable=False, index=True)
    allied: bool = Field(default=False)
    ally_id: Optional[str] = Field(default=None, foreign_key="team.id")
    health: int = Field(default=5000)

    players: List["Player"] = Relationship(back_populates="team")


class Player(SQLModel, table=True):
    """Combined SQLModel model for players."""

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True, index=True)
    # single identifier used as both display name and login
    username: str = Field(nullable=False, index=True)
    hashed_password: Optional[str] = Field(default=None)
    team_id: Optional[str] = Field(default=None, foreign_key="team.id")

    team: Optional[Team] = Relationship(back_populates="players")


class PlayerCreate(BaseModel):
    """Pydantic model for creating a player. This is used for request validation."""

    username: str
    join_team_id: Optional[str] = None # Optional team ID to join
    team_name: Optional[str] = None # Optional team name to create and join

class Card(SQLModel, table=True):
    """Combined SQLModel model for cards. Each card has a unique id and flags.

    - `type` is a single CardType
    - `flags` stores extra CardType values as JSON list
    """

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True, index=True)
    type: CardType = Field(sa_column=Column(SAEnum(CardType), nullable=False))
    flags: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    author_id: str = Field(default=None, foreign_key="player.id")


# Note: this file now uses `sqlmodel` (install via `pip install sqlmodel`).