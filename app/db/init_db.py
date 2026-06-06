"""
Database initializer.
- Creates all tables automatically (ORM-based, no manual SQL needed)
- Creates Super Admin (Prakhar Sir) if not exists
"""

from sqlalchemy.orm import Session
from app.db.session import engine, SessionLocal, Base
from app.models.models import User, UserRole  # import models so Base knows them
from app.core.security import get_password_hash
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def init_db():
    """Create all tables. Safe to run multiple times — won't drop existing tables."""
    logger.info("📦 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Tables created (or already exist)")

    _create_super_admin()


def _create_super_admin():
    """Create Prakhar Sir's account if it doesn't exist."""
    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
        if existing:
            logger.info(f"✅ Super Admin already exists: {existing.name}")
            return

        admin = User(
            name=settings.SUPER_ADMIN_NAME,
            phone=settings.SUPER_ADMIN_PHONE,
            email=settings.SUPER_ADMIN_EMAIL,
            hashed_password=get_password_hash(settings.SUPER_ADMIN_PASSWORD),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        logger.info(f"🎉 Super Admin created: {settings.SUPER_ADMIN_NAME} | Phone: {settings.SUPER_ADMIN_PHONE}")
    except Exception as e:
        logger.error(f"❌ Error creating super admin: {e}")
        db.rollback()
    finally:
        db.close()
