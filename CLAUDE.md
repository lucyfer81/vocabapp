# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VocabApp is a Flask-based vocabulary learning application with user authentication, wordbook management, and progressive learning modes. The application uses SQLite for data storage and follows a simple MVC-like architecture.

## Development Commands

Since this is a Python Flask application without traditional package management files, use these commands:

### Running the Application
```bash
# Development mode
export FLASK_CONFIG=development
python app.py

# Production mode (uses waitress)
# The app runs as a service managed by systemd
```

### Database Operations
```bash
# Initialize database (tables are created automatically on first run)
python app.py

# View database schema
sqlite3 wordbook.db ".schema"

# Check database tables
sqlite3 wordbook.db ".tables"
```

### Testing
There are no automated tests currently. Manual testing involves:
- Testing user registration and login flows
- Verifying wordbook CRUD operations
- Testing practice modes A and B
- Checking admin functionality

## Architecture

### Core Components

**app.py** - Main Flask application containing:
- All routes and business logic
- Authentication decorators (@login_required, @admin_required)
- Word practice logic (modes A and B)
- CSV import functionality
- Device authentication system

**models.py** - SQLAlchemy database models:
- User: User accounts with authentication
- WordBook: Vocabulary collections
- Word: Individual vocabulary items with unit organization
- UserWordProgress: Tracks completion status and statistics
- UserWordMistake: Records incorrect answers for review
- DeviceAuth: Device fingerprint-based authentication

**config.py** - Configuration classes:
- DevelopmentConfig (SQLite: dev-wordbook.db)
- ProductionConfig (SQLite: instance/wordbook.db)

**database.py** - SQLAlchemy database initialization

### Database Schema

The application uses a relational database with these key relationships:
- WordBook → Word (one-to-many with cascade delete)
- User → UserWordProgress (one-to-many per wordbook/unit)
- User → UserWordMistake (tracks learning mistakes)
- User → DeviceAuth (device-based authentication)

### Learning System Architecture

**Two-Stage Learning Process:**
1. **Mode A**: Partial word completion (20% letters hidden)
   - Must complete perfectly to unlock Mode B
   - Tracks correct/incorrect attempts

2. **Mode B**: Full word completion (all letters hidden)
   - Unlocked after perfect Mode A completion
   - Mistakes added to review system
   - Requires 2 consecutive correct answers to remove from mistakes

**Progress Tracking:**
- Unit-based completion tracking
- Separate statistics for each mode
- Mistake review system with adaptive removal

### Authentication System

**Session-based authentication** with device fingerprinting:
- Traditional username/password login
- Device fingerprint-based auto-login
- Admin role (hardcoded 'admin' user)
- CSRF protection via Flask session management

### Frontend Structure

**Templates** (organized by feature):
- Authentication: login.html, register.html
- Wordbook Management: wordbook_*.html
- Practice Modes: practice_a.html, practice_b.html
- Review System: review.html, review_mode_b.html
- Admin: admin_user_progress.html

**Static Assets:**
- Pico CSS for styling
- Custom CSS for application-specific styling
- JavaScript for interactive practice functionality

## Key Development Patterns

### Error Handling
- Comprehensive logging throughout the application
- Try-catch blocks with proper database rollback
- User-friendly error messages in Chinese
- HTTP status codes for API responses

### Data Validation
- Regex patterns for username/email validation
- Length validation for all text fields
- Database uniqueness constraints
- Form data sanitization

### Security Practices
- Password hashing with Werkzeug
- SQL injection protection via SQLAlchemy
- Input validation and sanitization
- Session-based authentication

## Admin Features

- CSV import functionality for bulk word addition
- User progress monitoring across all wordbooks
- Wordbook CRUD operations
- Access to all user learning statistics

## Deployment Workflow

This project follows a Git-flow style workflow (documented in instruction.md):
- **Production**: `/home/ubuntu/PyProjects/vocabapp` (main branch)
- **Development**: `/home/ubuntu/PyProjects/vocabapp-dev` (develop branch)
- Features developed in feature/* branches, merged to develop, then to main

## Database Notes

- Uses SQLite with foreign key constraints
- Cascade deletes for maintaining data integrity
- Timestamps stored as strings (not datetime objects)
- Unique constraints prevent duplicate data
- Device authentication with fingerprint-based auto-login

## Code Style Conventions

- Chinese language for user-facing messages
- English for code comments and variable names
- Flask-Blueprints style routing (all routes in app.py)
- SQLAlchemy ORM for database operations
- Comprehensive logging with different levels