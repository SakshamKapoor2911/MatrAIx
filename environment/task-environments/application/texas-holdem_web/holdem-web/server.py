"""FastAPI server for Texas Hold'em heads-up game."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import game as g

app = FastAPI(title="Texas Hold'em")
app.mount("/static", StaticFiles(directory="static"), name="static")

_state: Optional[g.GameState] = None


@app.get("/", response_class=HTMLResponse)
def root():
    return FileResponse("static/index.html")


@app.post("/new-game")
def new_game():
    global _state
    _state = g.new_game()
    return g.state_to_dict(_state)


@app.get("/state")
def get_state():
    if _state is None:
        raise HTTPException(status_code=400, detail="No game in progress. POST /new-game first.")
    return g.state_to_dict(_state)


class ActionRequest(BaseModel):
    action: str
    amount: int = g.RAISE_SIZE


@app.post("/action")
def take_action(req: ActionRequest):
    if _state is None:
        raise HTTPException(status_code=400, detail="No game in progress. POST /new-game first.")
    if _state.status != "playing":
        raise HTTPException(status_code=400, detail="Game is finished. POST /new-game to start again.")
    valid = {"fold", "check", "call", "raise"}
    if req.action not in valid:
        raise HTTPException(status_code=422, detail=f"action must be one of {sorted(valid)}")
    g.apply_action(_state, req.action, req.amount)
    return g.state_to_dict(_state)
