from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.database.connection import Base

class SongModel(Base):
    """
    SQLAlchemy Database Model for the 'songs' table.
    Tracks song release cycles from Artist Upload (pending) to Admin Approval (approved + MEGA uploaded).
    """
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(150), nullable=False)
    artist = Column(String(100), nullable=False)
    genre = Column(String(50), nullable=False)
    
    # Store path or URL representing the cover image file
    cover_image = Column(String(255), nullable=True)
    
    # Stores the local raw system path of the uploaded mp3 audio file while pending
    local_file_path = Column(String(255), nullable=True)
    
    # Full streaming / preview link on MEGA Cloud storage (populated on Admin Approval)
    mega_link = Column(String(512), nullable=True)
    
    # Current status: "pending", "approved", "rejected"
    status = Column(String(20), default="pending", nullable=False)
    
    # Date of upload creation in UTC
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "genre": self.genre,
            "cover_image": self.cover_image,
            "mega_link": self.mega_link,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }