from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path

from .database import Base, engine, get_db
from .models import User, Event, Registration, Team, TeamMember, Submission, Notification
from .schemas import Signup, Login, EventCreate, TeamCreate, SubmissionCreate, ScoreUpdate
from .auth import hash_password, verify_password, create_token, current_user, require_role

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Brisk Hack AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Brisk Hack AI"}


@app.post("/api/auth/signup")
def signup(data: Signup, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(409, "Email already registered")
    if data.role not in {"participant", "organizer", "sponsor", "judge"}:
        raise HTTPException(400, "Invalid role")
    user = User(name=data.name, email=data.email.lower(), password_hash=hash_password(data.password), role=data.role, skills=data.skills)
    db.add(user); db.commit(); db.refresh(user)
    return {"access_token": create_token(user), "token_type": "bearer", "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role}}


@app.post("/api/auth/login")
def login(data: Login, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return {"access_token": create_token(user), "token_type": "bearer", "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role}}


@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role, "skills": user.skills}


@app.get("/api/events")
def list_events(db: Session = Depends(get_db)):
    events = db.query(Event).order_by(Event.created_at.desc()).all()
    return [{"id": e.id, "name": e.name, "description": e.description, "format": e.format, "team_size": e.team_size, "tracks": e.tracks, "start_date": e.start_date, "end_date": e.end_date, "status": e.status, "organizer_id": e.organizer_id} for e in events]


@app.post("/api/events")
def create_event(data: EventCreate, db: Session = Depends(get_db), user: User = Depends(require_role("organizer"))):
    event = Event(**data.model_dump(), organizer_id=user.id)
    db.add(event); db.commit(); db.refresh(event)
    return {"id": event.id, "message": "Event created", "event": data.model_dump()}


@app.post("/api/events/{event_id}/register")
def register(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not db.query(Event).filter(Event.id == event_id).first():
        raise HTTPException(404, "Event not found")
    existing = db.query(Registration).filter_by(event_id=event_id, user_id=user.id).first()
    if existing:
        return {"message": "Already registered"}
    db.add(Registration(event_id=event_id, user_id=user.id))
    db.add(Notification(user_id=user.id, title="Registration confirmed", message=f"You are registered for event #{event_id}"))
    db.commit()
    return {"message": "Registration successful"}


@app.post("/api/teams")
def create_team(data: TeamCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not db.query(Registration).filter_by(event_id=data.event_id, user_id=user.id).first():
        raise HTTPException(400, "Register for the event first")
    team = Team(name=data.name, event_id=data.event_id, owner_id=user.id, track=data.track)
    db.add(team); db.commit(); db.refresh(team)
    db.add(TeamMember(team_id=team.id, user_id=user.id)); db.commit()
    return {"id": team.id, "message": "Team created"}


@app.post("/api/teams/{team_id}/join")
def join_team(team_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team: raise HTTPException(404, "Team not found")
    if db.query(TeamMember).filter_by(team_id=team_id, user_id=user.id).first():
        return {"message": "Already a team member"}
    event = db.query(Event).filter(Event.id == team.event_id).first()
    member_count = db.query(TeamMember).filter(TeamMember.team_id == team_id).count()
    if member_count >= event.team_size: raise HTTPException(400, "Team is full")
    db.add(TeamMember(team_id=team_id, user_id=user.id)); db.commit()
    return {"message": "Joined team"}


@app.get("/api/team-matches")
def team_matches(event_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    candidates = db.query(User).join(Registration, Registration.user_id == User.id).filter(Registration.event_id == event_id, User.id != user.id).limit(10).all()
    mine = {x.strip().lower() for x in user.skills.split(",") if x.strip()}
    result = []
    for c in candidates:
        theirs = {x.strip().lower() for x in c.skills.split(",") if x.strip()}
        complement = len(theirs - mine)
        overlap = len(theirs & mine)
        score = min(99, 60 + complement * 8 + overlap * 3)
        result.append({"id": c.id, "name": c.name, "skills": c.skills, "match_score": score})
    return sorted(result, key=lambda x: x["match_score"], reverse=True)


@app.post("/api/submissions")
def submit(data: SubmissionCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    team = db.query(Team).filter(Team.id == data.team_id).first()
    if not team: raise HTTPException(404, "Team not found")
    if not db.query(TeamMember).filter_by(team_id=team.id, user_id=user.id).first():
        raise HTTPException(403, "Not a member of this team")
    existing = db.query(Submission).filter(Submission.team_id == team.id).first()
    if existing:
        for key, value in data.model_dump().items(): setattr(existing, key, value)
        db.commit(); return {"id": existing.id, "message": "Submission updated"}
    item = Submission(**data.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, "message": "Project submitted"}


@app.patch("/api/submissions/{submission_id}/score")
def score_submission(submission_id: int, data: ScoreUpdate, db: Session = Depends(get_db), user: User = Depends(require_role("judge", "organizer"))):
    item = db.query(Submission).filter(Submission.id == submission_id).first()
    if not item: raise HTTPException(404, "Submission not found")
    item.score = data.score; db.commit()
    return {"message": "Score saved", "score": item.score}


@app.get("/api/events/{event_id}/leaderboard")
def leaderboard(event_id: int, db: Session = Depends(get_db)):
    rows = db.query(Team, Submission).join(Submission, Submission.team_id == Team.id).filter(Team.event_id == event_id).order_by(Submission.score.desc()).all()
    return [{"rank": i + 1, "team_id": t.id, "team": t.name, "track": t.track, "score": s.score, "title": s.title} for i, (t, s) in enumerate(rows)]


@app.get("/api/notifications")
def notifications(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).all()
    return [{"id": n.id, "title": n.title, "message": n.message, "is_read": n.is_read, "created_at": n.created_at} for n in rows]


@app.get("/api/organizer/analytics")
def analytics(db: Session = Depends(get_db), user: User = Depends(require_role("organizer"))):
    event_ids = [e.id for e in db.query(Event).filter(Event.organizer_id == user.id).all()]
    registrations = db.query(Registration).filter(Registration.event_id.in_(event_ids)).count() if event_ids else 0
    teams = db.query(Team).filter(Team.event_id.in_(event_ids)).count() if event_ids else 0
    submissions = db.query(Submission).join(Team).filter(Team.event_id.in_(event_ids)).count() if event_ids else 0
    return {"events": len(event_ids), "registrations": registrations, "teams": teams, "submissions": submissions}


FRONTEND = Path(__file__).resolve().parents[2] / "index.html"
@app.get("/")
def frontend():
    return FileResponse(FRONTEND)
