from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models
from app.schemas.candidate import CandidateCreate, CandidateResponse

router = APIRouter(prefix="/candidate", tags=["Candidate"])

@router.post("/register", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
def register_candidate(candidate_in: CandidateCreate, db: Session = Depends(get_db)) -> CandidateResponse:
    """
    Registers a new candidate, creates their profile, and returns a unique candidate_id.
    """
    # Check if email already registered (optional, let's allow re-registration or find existing)
    existing_candidate = db.query(models.Candidate).filter(models.Candidate.email == candidate_in.email).first()
    if existing_candidate:
        # For ease of testing and reuse, let's just return the existing candidate
        return existing_candidate
        
    db_candidate = models.Candidate(
        name=candidate_in.name,
        email=candidate_in.email,
        phone=candidate_in.phone,
        qualification=candidate_in.qualification,
        experience=candidate_in.experience,
        role=candidate_in.role,
        skillset=candidate_in.skillset
    )
    
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    
    return db_candidate
