from database import db

class User(db.Model):
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(20), unique=True)
    created_at = db.Column(db.String(50), nullable=False)

class WordBook(db.Model):
    __tablename__ = 'WordBook'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.String(50), nullable=False)
    words = db.relationship('Word', backref='wordbook', cascade='all, delete')

class Word(db.Model):
    __tablename__ = 'Word'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    wordbook_id = db.Column(db.Integer, db.ForeignKey('WordBook.id', ondelete='CASCADE'), nullable=False)
    unit = db.Column(db.String(50), nullable=False)
    english = db.Column(db.String(50), nullable=False)
    chinese = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.String(50), nullable=False)

class UserWordProgress(db.Model):
    __tablename__ = 'UserWordProgress'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id', ondelete='CASCADE'), nullable=False)
    wordbook_id = db.Column(db.Integer, db.ForeignKey('WordBook.id', ondelete='CASCADE'), nullable=False)
    unit = db.Column(db.String(50), nullable=False)
    is_completed_a = db.Column(db.Integer, nullable=False, default=0)
    is_completed_b = db.Column(db.Integer, nullable=False, default=0)
    last_attempted = db.Column(db.String(50))
    correct_count_a = db.Column(db.Integer, nullable=False, default=0)
    incorrect_count_a = db.Column(db.Integer, nullable=False, default=0)
    correct_count_b = db.Column(db.Integer, nullable=False, default=0)
    incorrect_count_b = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.String(50), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'wordbook_id', 'unit', name='uix_user_wordbook_unit'),)

class UserWordMistake(db.Model):
    __tablename__ = 'UserWordMistake'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id', ondelete='CASCADE'), nullable=False)
    word_id = db.Column(db.Integer, db.ForeignKey('Word.id', ondelete='CASCADE'), nullable=False)
    wordbook_id = db.Column(db.Integer, db.ForeignKey('WordBook.id', ondelete='CASCADE'), nullable=False)
    unit = db.Column(db.String(50), nullable=False)

    mode = db.Column(db.String(10), nullable=False, default='B')

    incorrect_count = db.Column(db.Integer, nullable=False, default=0)

    correct_count = db.Column(db.Integer, nullable=False, default=0)

    last_incorrect = db.Column(db.String(50))
    created_at = db.Column(db.String(50), nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'word_id', 'mode', name='uix_user_word_mistake'),)

    # Add relationship to Word
    word = db.relationship('Word', backref='mistakes')

class DeviceAuth(db.Model):
    __tablename__ = 'DeviceAuth'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id', ondelete='CASCADE'), nullable=False)
    device_fingerprint = db.Column(db.String(255), nullable=False)  # 设备指纹
    device_name = db.Column(db.String(100))  # 设备名称（如"儿子的iPad"）
    auth_token = db.Column(db.String(255), unique=True, nullable=False)  # 授权令牌
    created_at = db.Column(db.String(50), nullable=False)
    last_used = db.Column(db.String(50))
    is_active = db.Column(db.Integer, nullable=False, default=1)  # 是否启用
    
    __table_args__ = (db.UniqueConstraint('user_id', 'device_fingerprint', name='uix_user_device'),)