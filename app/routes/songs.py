import os
import shutil
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Header, Query
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.song import SongModel
from app.services.mega_service import MegaService

router = APIRouter()
mega_service = MegaService()
security = HTTPBearer()

UPLOADS_DIR = "uploads"
MP3_DIR = os.path.join(UPLOADS_DIR, "mp3")
COVERS_DIR = os.path.join(UPLOADS_DIR, "covers")

os.makedirs(MP3_DIR, exist_ok=True)
os.makedirs(COVERS_DIR, exist_ok=True)

def check_auth(authorization: str = Header(None)):
    """
    Dependency helper to enforce API security for the upload endpoint.
    Artists must provide: 'Authorization: Bearer richmurd2002_uploader_token'
    """
    expected_token = os.getenv("UPLOAD_AUTH_TOKEN", "richmurd2002_uploader_token")
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Upload request must include: 'Authorization: Bearer <token>'"
        )
        
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization schema. Use Bearer token authorization format."
        )
        
    if token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized. The uploaded artist security token is invalid or expired."
        )
    return token

@router.post("/upload-song", status_code=status.HTTP_201_CREATED)
async def upload_song(
    title: str = Form(...),
    artist: str = Form(...),
    genre: str = Form(...),
    song_file: UploadFile = File(...),
    cover_image: UploadFile = File(...),
    token: str = Depends(check_auth),
    db: Session = Depends(get_db)
):
    if not song_file.filename.lower().endswith((".mp3", ".wav", ".m4a")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported audio format. Please upload .mp3, .wav, or .m4a."
        )
        
    if not cover_image.filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image format. Artwork must be .jpg, .png, or .webp."
        )

    timestamp_prefix = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip()
    
    song_filename = f"{timestamp_prefix}_{safe_title}.mp3"
    cover_filename = f"{timestamp_prefix}_{safe_title}_art.jpg"
    
    local_mp3_path = os.path.join(MP3_DIR, song_filename)
    local_cover_path = os.path.join(COVERS_DIR, cover_filename)

    try:
        with open(local_mp3_path, "wb") as buffer:
            shutil.copyfileobj(song_file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write audio stream to filesystem: {str(e)}"
        )

    try:
        with open(local_cover_path, "wb") as buffer:
            shutil.copyfileobj(cover_image.file, buffer)
    except Exception as e:
        if os.path.exists(local_mp3_path):
            os.remove(local_mp3_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write artwork stream to filesystem: {str(e)}"
        )

    try:
        new_song = SongModel(
            title=title,
            artist=artist,
            genre=genre,
            cover_image=f"/static/covers/{cover_filename}",
            local_file_path=local_mp3_path,
            status="pending"
        )
        
        db.add(new_song)
        db.commit()
        db.refresh(new_song)
        
        return {
            "success": True,
            "message": "Song successfully uploaded and registered in the queue! Awaiting admin review.",
            "song": new_song.to_dict()
        }
    except Exception as e:
        if os.path.exists(local_mp3_path):
            os.remove(local_mp3_path)
        if os.path.exists(local_cover_path):
            os.remove(local_cover_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database write exception: {str(e)}"
        )

@router.get("/pending-songs", response_model=List[dict])
def get_pending_songs(db: Session = Depends(get_db)):
    pending = db.query(SongModel).filter(SongModel.status == "pending").order_by(SongModel.created_at.desc()).all()
    return [song.to_dict() for song in pending]

@router.post("/approve/{song_id}")
def approve_song(song_id: int, db: Session = Depends(get_db)):
    song = db.query(SongModel).filter(SongModel.id == song_id).first()
    
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested song ID does not exist in our catalog registries."
        )
        
    if song.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve this song. Current status is already: '{song.status}'"
        )

    if not song.local_file_path or not os.path.exists(song.local_file_path):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The local raw .mp3 audio binary was missing or moved from server cache workspace."
        )

    try:
        mega_link = mega_service.upload_file(song.local_file_path)
        
        if not mega_link:
            raise Exception("Cloud transport failed to deliver destination streaming url link.")
            
        song.mega_link = mega_link
        song.status = "approved"
        db.commit()
        db.refresh(song)
        
        return {
            "success": True,
            "message": f"Successfully approved '{song.title}'! Master file permanently published to MEGA cloud nodes.",
            "mega_link": mega_link,
            "song": song.to_dict()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Approval pipeline failure: {str(e)}"
        )

@router.post("/reject/{song_id}")
def reject_song(song_id: int, db: Session = Depends(get_db)):
    song = db.query(SongModel).filter(SongModel.id == song_id).first()
    
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Song ID not found."
        )
        
    if song.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject song with existing status: '{song.status}'"
        )

    try:
        if song.local_file_path and os.path.exists(song.local_file_path):
            os.remove(song.local_file_path)
            
        song.status = "rejected"
        db.commit()
        db.refresh(song)
        
        return {
            "success": True,
            "message": f"The release master entry for '{song.title}' has been successfully flagged as rejected.",
            "song": song.to_dict()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rejection process error: {str(e)}"
        )

@router.get("/songs", response_model=List[dict])
def get_approved_songs(
    search: Optional[str] = Query(None, description="Search queries for title or artist matching"),
    genre: Optional[str] = Query(None, description="Filter specifically by genre standard terms"),
    db: Session = Depends(get_db)
):
    query = db.query(SongModel).filter(SongModel.status == "approved")
    
    if genre:
        query = query.filter(SongModel.genre.ilike(f"%{genre}%"))
        
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (SongModel.title.ilike(search_filter)) | 
            (SongModel.artist.ilike(search_filter)) |
            (SongModel.genre.ilike(search_filter))
        )
        
    songs = query.order_by(SongModel.created_at.desc()).all()
    return [song.to_dict() for song in songs]

@router.get("/stream/{song_id}")
def stream_song(song_id: int, db: Session = Depends(get_db)):
    song = db.query(SongModel).filter(SongModel.id == song_id).first()
    
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Streaming target song ID not found."
        )
        
    if song.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This release is not approved."
        )

    if song.mega_link:
        return RedirectResponse(url=song.mega_link, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        
    if song.local_file_path and os.path.exists(song.local_file_path):
        return FileResponse(path=song.local_file_path, media_type="audio/mpeg", filename=f"{song.title}.mp3")
        
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No live media stream paths are active for this song database record."
    )