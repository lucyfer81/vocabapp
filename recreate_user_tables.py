
import os
from app import app, db
from models import User, UserWordProgress, UserWordMistake, DeviceAuth

from sqlalchemy import text

def recreate_user_tables():
    """
    Drops and recreates user-related tables to apply schema changes
    without affecting wordbook data.
    """
    with app.app_context():
        print("Dropping user-related tables...")

        # Temporarily disable foreign key checks to allow dropping User table
        if db.engine.name == 'sqlite':
            db.session.execute(text('PRAGMA foreign_keys=OFF;'))

        # Drop tables in a safe order
        UserWordMistake.__table__.drop(db.engine, checkfirst=True)
        UserWordProgress.__table__.drop(db.engine, checkfirst=True)
        DeviceAuth.__table__.drop(db.engine, checkfirst=True)
        User.__table__.drop(db.engine, checkfirst=True)

        if db.engine.name == 'sqlite':
            db.session.execute(text('PRAGMA foreign_keys=ON;'))

        print("User-related tables dropped.")

        print("Recreating tables from current models...")
        # db.create_all() will create missing tables based on model definitions
        db.create_all()
        
        db.session.commit()
        print("Tables recreated successfully.")
        print("IMPORTANT: You must re-register your users.")

if __name__ == '__main__':
    recreate_user_tables()
