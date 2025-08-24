from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from database import db
from models import User, WordBook, Word, UserWordProgress, UserWordMistake, DeviceAuth
import re
import datetime
import os
import logging
import math
import random
import csv
import io

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins='*', supports_credentials=True)  # 允许所有来源的跨域请求
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/ubuntu/PyProjects/vocabapp/wordbook.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# 输入验证正则表达式
USERNAME_PATTERN = r'^[a-zA-Z0-9_]+$'
EMAIL_PATTERN = r'^[\w\.-]+@[\w\.-]+\.\w+$'

# 检查登录状态的装饰器
def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# 检查管理员权限
def admin_required(f):
    def wrap(*args, **kwargs):
        if 'username' not in session or session['username'] != 'admin':
            logger.warning('Unauthorized access attempt')
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@app.route('/')
@login_required
def index():
    logger.debug('Accessing index page')
    is_admin = session['username'] == 'admin'
    return render_template('index.html', username=session['username'], is_admin=is_admin)

@app.route('/register', methods=['GET', 'POST'])
def register():
    logger.debug('Received request to /register')
    if request.method == 'POST':
        logger.debug('Processing POST request for /register')
        data = request.form
        logger.debug(f'Form data: {data}')
        username = data.get('username')
        password = data.get('password')
        email = data.get('email', '').strip()
        if not username or len(username) > 20 or not re.match(USERNAME_PATTERN, username):
            logger.warning(f'Invalid username: {username}')
            return jsonify({'error': '用户名必须为1-20字符，仅限字母、数字、下划线'}), 400
        if not password or len(password) < 6 or len(password) > 128:
            logger.warning('Invalid password length')
            return jsonify({'error': '密码必须为6-128字符'}), 400
        if email and (len(email) > 20 or not re.match(EMAIL_PATTERN, email)):
            logger.warning(f'Invalid email: {email}')
            return jsonify({'error': '邮箱格式无效或超过20字符'}), 400
        with app.app_context():
            try:
                if User.query.filter_by(username=username).first():
                    logger.warning(f'Username already exists: {username}')
                    return jsonify({'error': '用户名已存在'}), 400
                if email and User.query.filter_by(email=email).first():
                    logger.warning(f'Email already exists: {email}')
                    return jsonify({'error': '邮箱已存在'}), 400
                password_hash = generate_password_hash(password)
                new_user = User(
                    username=username,
                    password_hash=password_hash,
                    email=email or None,
                    created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                db.session.add(new_user)
                db.session.commit()
                logger.info(f'User registered successfully: {username}')
                return jsonify({'message': '注册成功，请登录'}), 200
            except Exception as e:
                logger.error(f'Error during registration: {str(e)}')
                return jsonify({'error': '服务器错误，请稍后重试'}), 500
    logger.debug('Rendering register.html')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    logger.debug('Received request to /login')
    if request.method == 'POST':
        logger.debug('Processing POST request for /login')
        
        # 支持JSON和表单两种提交方式
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
            
        logger.debug(f'Received data: {data}')
        username = data.get('username')
        password = data.get('password')
        device_fingerprint = data.get('device_fingerprint')
        device_name = data.get('device_name', '未知设备')
        
        if not username or not password:
            logger.warning('Username or password empty')
            return jsonify({'error': '用户名和密码不能为空'}), 400
            
        with app.app_context():
            try:
                user = User.query.filter_by(username=username).first()
                if not user or not check_password_hash(user.password_hash, password):
                    logger.warning(f'Login failed for username: {username}')
                    return jsonify({'error': '用户名或密码错误'}), 401
                
                session['user_id'] = user.id
                session['username'] = user.username
                logger.info(f'User logged in: {username}')
                
                # 如果提供了设备指纹，创建或更新设备授权
                if device_fingerprint:
                    auth_token = generate_auth_token()
                    
                    # 首先检查该设备指纹是否已被其他用户使用
                    existing_device_auth = DeviceAuth.query.filter_by(
                        device_fingerprint=device_fingerprint,
                        is_active=1
                    ).first()
                    
                    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    if existing_device_auth and existing_device_auth.user_id != user.id:
                        # 设备指纹已被其他用户使用，先禁用旧的授权
                        logger.warning(f'Device fingerprint {device_fingerprint[:16]}... was associated with user {existing_device_auth.user_id}, now reassigning to user {user.id}')
                        existing_device_auth.is_active = 0
                    
                    # 创建或更新当前用户的设备授权
                    device_auth = DeviceAuth.query.filter_by(
                        user_id=user.id,
                        device_fingerprint=device_fingerprint
                    ).first()
                    
                    if device_auth:
                        device_auth.auth_token = auth_token
                        device_auth.last_used = current_time
                        device_auth.device_name = device_name
                        device_auth.is_active = 1  # 确保启用
                    else:
                        device_auth = DeviceAuth(
                            user_id=user.id,
                            device_fingerprint=device_fingerprint,
                            device_name=device_name,
                            auth_token=auth_token,
                            created_at=current_time,
                            last_used=current_time,
                            is_active=1
                        )
                        db.session.add(device_auth)
                    
                    db.session.commit()
                    logger.info(f'Device auth updated for user {user.username} with fingerprint {device_fingerprint[:16]}...')
                    
                return jsonify({'message': '登录成功'}), 200
            except Exception as e:
                logger.error(f'Error during login: {str(e)}')
                return jsonify({'error': '服务器错误，请稍后重试'}), 500
    logger.debug('Rendering login.html')
    return render_template('login.html')

@app.route('/check_device_auth', methods=['POST'])
def check_device_auth():
    """检查设备授权并实现自动登录"""
    logger.debug('Received request to /check_device_auth')
    
    if not request.is_json:
        return jsonify({'error': '需要JSON数据'}), 400
        
    data = request.get_json()
    device_fingerprint = data.get('device_fingerprint')
    
    if not device_fingerprint:
        return jsonify({'error': '设备指纹不能为空'}), 400
        
    with app.app_context():
        try:
            device_auth = DeviceAuth.query.filter_by(
                device_fingerprint=device_fingerprint,
                is_active=1
            ).first()
            
            if device_auth:
                user = User.query.get(device_auth.user_id)
                if user:
                    session['user_id'] = user.id
                    session['username'] = user.username
                    device_auth.last_used = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    db.session.commit()
                    logger.info(f'Auto-login successful for user: {user.username} with device fingerprint: {device_fingerprint[:16]}...')
                    return jsonify({'success': True, 'token': device_auth.auth_token})
                else:
                    # 用户不存在，禁用此设备授权
                    device_auth.is_active = 0
                    db.session.commit()
                    logger.warning(f'Device auth found but user not found for fingerprint: {device_fingerprint[:16]}...')
            
            logger.debug(f'No active device auth found for fingerprint: {device_fingerprint[:16]}...')
            return jsonify({'success': False})
        except Exception as e:
            logger.error(f'Error checking device auth: {str(e)}')
            return jsonify({'error': '服务器错误'}), 500

def generate_auth_token():
    """生成安全的授权令牌"""
    import secrets
    return secrets.token_urlsafe(32)

@app.route('/logout')
def logout():
    logger.debug('User logging out')
    session.clear()
    return redirect(url_for('login'))

@app.route('/wordbook/list')
@login_required
def wordbook_list():
    logger.debug('Accessing wordbook list')
    with app.app_context():
        wordbooks = WordBook.query.order_by(WordBook.created_at.desc()).all()
        is_admin = session['username'] == 'admin'
        return render_template('wordbook_list.html', wordbooks=wordbooks, is_admin=is_admin)

@app.route('/wordbook/import_csv/<int:wordbook_id>', methods=['POST'])
@login_required
@admin_required
def import_csv_words(wordbook_id):
    """管理员导入CSV格式的单词数据"""
    logger.debug(f'Received CSV import request for wordbook {wordbook_id}')
    
    if 'csv_file' not in request.files:
        logger.warning('No CSV file uploaded')
        return jsonify({'error': '请选择CSV文件'}), 400
    
    file = request.files['csv_file']
    if file.filename == '':
        logger.warning('No file selected')
        return jsonify({'error': '请选择CSV文件'}), 400
    
    if not file.filename.endswith('.csv'):
        logger.warning(f'Invalid file type: {file.filename}')
        return jsonify({'error': '请上传CSV格式的文件'}), 400
    
    try:
        # 读取CSV文件内容
        content = file.read()
        logger.info(f'文件大小: {len(content)} 字节')
        
        # 尝试不同的编码
        encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312']
        decoded_content = None
        
        for encoding in encodings:
            try:
                decoded_content = content.decode(encoding)
                logger.info(f'成功使用 {encoding} 编码解码')
                break
            except UnicodeDecodeError:
                logger.warning(f'无法使用 {encoding} 编码解码')
                continue
        
        if decoded_content is None:
            logger.error('无法解码文件内容')
            return jsonify({'error': '文件编码不支持，请使用UTF-8编码保存CSV文件'}), 400
        
        # 移除BOM头（如果存在）
        if decoded_content.startswith('\ufeff'):
            decoded_content = decoded_content[1:]
            logger.info('移除BOM头')
        
        logger.info(f'文件内容前100字符: {repr(decoded_content[:100])}')
        
        csv_reader = csv.reader(io.StringIO(decoded_content))
        
        # 跳过标题行
        headers = next(csv_reader, None)
        if not headers or len(headers) < 3:
            logger.warning('Invalid CSV format')
            return jsonify({'error': 'CSV格式错误，至少需要3列数据'}), 400
        
        # 验证CSV格式
        expected_headers = ['unit', 'english', 'chinese']
        headers_lower = [h.lower().strip() for h in headers]
        logger.info(f'CSV headers: {headers}')
        logger.info(f'Headers lower: {headers_lower}')
        logger.info(f'Expected headers: {expected_headers}')
        
        if not all(h.lower() in headers_lower for h in expected_headers):
            missing_headers = [h for h in expected_headers if h.lower() not in headers_lower]
            logger.warning(f'Invalid CSV headers: {headers}')
            logger.warning(f'Missing headers: {missing_headers}')
            return jsonify({'error': f'CSV标题行必须包含：unit, english, chinese。缺少：{missing_headers}'}), 400
        
        # 获取列索引
        unit_idx = next((i for i, h in enumerate(headers) if h.lower().strip() == 'unit'), 0)
        english_idx = next((i for i, h in enumerate(headers) if h.lower().strip() == 'english'), 1)
        chinese_idx = next((i for i, h in enumerate(headers) if h.lower().strip() == 'chinese'), 2)
        
        imported_count = 0
        errors = []
        
        with app.app_context():
            wordbook = WordBook.query.get_or_404(wordbook_id)
            
            for row_num, row in enumerate(csv_reader, 2):  # 从第2行开始计数
                try:
                    if len(row) < 3:
                        errors.append(f'第{row_num}行：数据不完整')
                        continue
                    
                    unit = row[unit_idx].strip()
                    english = row[english_idx].strip()
                    chinese = row[chinese_idx].strip()
                    
                    # 验证数据
                    if not unit or len(unit) > 50:
                        errors.append(f'第{row_num}行：单元名称必须在1-50字符之间')
                        continue
                    
                    if not english or len(english) > 50:
                        errors.append(f'第{row_num}行：英文单词必须在1-50字符之间')
                        continue
                    
                    if not chinese or len(chinese) > 50:
                        errors.append(f'第{row_num}行：中文释义必须在1-50字符之间')
                        continue
                    
                    # 检查是否已存在相同的单词
                    existing_word = Word.query.filter_by(
                        wordbook_id=wordbook_id,
                        unit=unit,
                        english=english,
                        chinese=chinese
                    ).first()
                    
                    if existing_word:
                        errors.append(f'第{row_num}行：该单词已存在')
                        continue
                    
                    # 创建新单词
                    new_word = Word(
                        wordbook_id=wordbook_id,
                        unit=unit,
                        english=english,
                        chinese=chinese,
                        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                    db.session.add(new_word)
                    imported_count += 1
                    
                except Exception as e:
                    logger.error(f'Error processing row {row_num}: {str(e)}')
                    errors.append(f'第{row_num}行：处理错误 - {str(e)}')
                    continue
            
            if imported_count > 0:
                db.session.commit()
                logger.info(f'Successfully imported {imported_count} words for wordbook {wordbook_id}')
            else:
                db.session.rollback()
                
        # 返回结果
        result = {
            'message': f'成功导入 {imported_count} 个单词',
            'imported_count': imported_count,
            'errors': errors
        }
        
        if errors:
            result['message'] += f'，遇到 {len(errors)} 个错误'
            
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f'Error during CSV import: {str(e)}')
        return jsonify({'error': f'导入失败：{str(e)}'}), 500

@app.route('/wordbook/create', methods=['GET', 'POST'])
@login_required
@admin_required
def wordbook_create():
    logger.debug('Received request to /wordbook/create')
    if request.method == 'POST':
        data = request.form
        logger.debug(f'Form data: {data}')
        title = data.get('title', '').strip()
        if not title or len(title) > 100:
            logger.warning(f'Invalid title: {title}')
            return jsonify({'error': '标题必须为1-100字符'}), 400
        with app.app_context():
            try:
                if WordBook.query.filter_by(title=title).first():
                    logger.warning(f'Title already exists: {title}')
                    return jsonify({'error': '单词书标题已存在'}), 400
                new_wordbook = WordBook(
                    title=title,
                    created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                db.session.add(new_wordbook)
                db.session.commit()
                logger.info(f'Wordbook created: {title}')
                return jsonify({'message': '单词书创建成功', 'wordbook_id': new_wordbook.id}), 200
            except Exception as e:
                logger.error(f'Error creating wordbook: {str(e)}')
                return jsonify({'error': '服务器错误，请稍后重试'}), 500
    return render_template('wordbook_form_with_import.html', mode='create')

@app.route('/wordbook/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def wordbook_edit(id):
    logger.debug(f'Received request to /wordbook/{id}/edit')
    with app.app_context():
        wordbook = WordBook.query.get_or_404(id)
        if request.method == 'POST':
            data = request.form
            logger.debug(f'Form data: {data}')
            title = data.get('title', '').strip()
            words_data = []
            delete_words = data.getlist('delete_words')
            i = 0
            while f'words[{i}][unit]' in data:
                words_data.append({
                    'id': data.get(f'words[{i}][id]', ''),
                    'unit': data.get(f'words[{i}][unit]', '').strip(),
                    'english': data.get(f'words[{i}][english]', '').strip(),
                    'chinese': data.get(f'words[{i}][chinese]', '').strip()
                })
                i += 1
            if not title or len(title) > 100:
                logger.warning(f'Invalid title: {title}')
                return jsonify({'error': '标题必须为1-100字符'}), 400
            if title != wordbook.title and WordBook.query.filter_by(title=title).first():
                logger.warning(f'Title already exists: {title}')
                return jsonify({'error': '单词书标题已存在'}), 400
            for idx, word in enumerate(words_data, 1):
                if not word['unit'] or len(word['unit']) > 50:
                    logger.warning(f'Invalid unit at index {idx}')
                    return jsonify({'error': f'第{idx}个单词的单元必须为1-50字符'}), 400
                if not word['english'] or len(word['english']) > 50:
                    logger.warning(f'Invalid english at index {idx}')
                    return jsonify({'error': f'第{idx}个单词的英文必须为1-50字符'}), 400
                if not word['chinese'] or len(word['chinese']) > 50:
                    logger.warning(f'Invalid chinese at index {idx}')
                    return jsonify({'error': f'第{idx}个单词的中文必须为1-50字符'}), 400
            try:
                wordbook.title = title
                if delete_words:
                    Word.query.filter(Word.id.in_(delete_words)).delete()
                for word_data in words_data:
                    if word_data['id']:
                        word = Word.query.get(word_data['id'])
                        if word:
                            word.unit = word_data['unit']
                            word.english = word_data['english']
                            word.chinese = word_data['chinese']
                    else:
                        new_word = Word(
                            wordbook_id=wordbook.id,
                            unit=word_data['unit'],
                            english=word_data['english'],
                            chinese=word_data['chinese'],
                            created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        )
                        db.session.add(new_word)
                db.session.commit()
                logger.info(f'Wordbook {id} updated')
                return jsonify({'message': '单词书更新成功'}), 200
            except Exception as e:
                logger.error(f'Error updating wordbook: {str(e)}')
                db.session.rollback()
                return jsonify({'error': '服务器错误，请稍后重试'}), 500
        words = Word.query.filter_by(wordbook_id=id).all()
        return render_template('wordbook_edit.html', wordbook=wordbook, words=words)

@app.route('/wordbook/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def wordbook_delete(id):
    logger.debug(f'Received request to delete wordbook {id}')
    with app.app_context():
        wordbook = WordBook.query.get_or_404(id)
        try:
            db.session.delete(wordbook)
            db.session.commit()
            logger.info(f'Wordbook {id} deleted')
            return jsonify({'message': '单词书删除成功'}), 200
        except Exception as e:
            logger.error(f'Error deleting wordbook: {str(e)}')
            return jsonify({'error': '服务器错误，请稍后重试'}), 500

@app.route('/wordbook/<int:id>')
@login_required
def wordbook_detail(id):
    logger.debug(f'Received request to /wordbook/{id}')
    with app.app_context():
        wordbook = WordBook.query.get_or_404(id)
        units = db.session.query(Word.unit, db.func.count(Word.id).label('word_count')).filter_by(wordbook_id=id).group_by(Word.unit).all()
        progress = UserWordProgress.query.filter_by(user_id=session['user_id'], wordbook_id=id).all()
        progress_dict = {p.unit: {'is_completed_a': p.is_completed_a, 'is_completed_b': p.is_completed_b} for p in progress}
        units_data = [
            {
                'unit': unit,
                'word_count': word_count,
                'is_completed_a': progress_dict.get(unit, {}).get('is_completed_a', 0),
                'is_completed_b': progress_dict.get(unit, {}).get('is_completed_b', 0)
            } for unit, word_count in units
        ]
        is_admin = session['username'] == 'admin'
        return render_template('wordbook_detail.html', wordbook=wordbook, units=units_data, is_admin=is_admin)

@app.route('/wordbook/<int:id>/select', methods=['POST'])
@login_required
def wordbook_select(id):
    logger.debug(f'Received request to select wordbook {id}')
    with app.app_context():
        wordbook = WordBook.query.get_or_404(id)
        units = db.session.query(Word.unit).filter_by(wordbook_id=id).distinct().all()
        try:
            for unit in units:
                unit = unit[0]
                if not UserWordProgress.query.filter_by(user_id=session['user_id'], wordbook_id=id, unit=unit).first():
                    progress = UserWordProgress(
                        user_id=session['user_id'],
                        wordbook_id=id,
                        unit=unit,
                        is_completed_a=0,
                        is_completed_b=0,
                        last_attempted=None,
                        correct_count_a=0,
                        incorrect_count_a=0,
                        correct_count_b=0,
                        incorrect_count_b=0,
                        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                    db.session.add(progress)
            db.session.commit()
            logger.info(f'Wordbook {id} selected for user {session["user_id"]}')
            return jsonify({'message': '单词书选择成功'}), 200
        except Exception as e:
            logger.error(f'Error selecting wordbook: {str(e)}')
            db.session.rollback()
            return jsonify({'error': '服务器错误，请稍后重试'}), 500

# 生成20%空白的单词（用于模式A）
def generate_partial_word(word):
    if not word:
        return word
    length = len(word)
    hide_count = max(1, math.ceil(length * 0.2))  # 至少隐藏1个字母
    indices = list(range(1, length))  # 避免隐藏首字母
    hide_indices = random.sample(indices, min(hide_count, len(indices)))
    word_chars = list(word)
    for idx in hide_indices:
        word_chars[idx] = '_'
    return ''.join(word_chars)

# 生成全空白的单词（用于模式B）
def generate_full_blank_word(word):
    if not word:
        return ''
    return ' '.join('_' * len(word))

@app.route('/wordbook/<int:id>/practice_a/<unit>', methods=['GET'])
@login_required
def practice_a(id, unit):
    logger.debug(f'Received request to /wordbook/{id}/practice_a/{unit}')
    with app.app_context():
        wordbook = WordBook.query.get_or_404(id)
        words = Word.query.filter_by(wordbook_id=id, unit=unit).all()
        if not words:
            logger.warning(f'No words found for wordbook {id}, unit {unit}')
            return jsonify({'error': '该单元没有单词'}), 404
        words_data = [{
            'id': w.id,
            'chinese': w.chinese,
            'english': w.english,
            'partial': generate_partial_word(w.english),
            'wordbook_id': id,
            'unit': unit
        } for w in words]
        return render_template('practice_a.html', wordbook=wordbook, unit=unit, words=words_data)

@app.route('/wordbook/<int:id>/practice_a/<unit>/submit', methods=['POST'])
@login_required
def practice_a_submit(id, unit):
    logger.debug(f'Received request to /wordbook/{id}/practice_a/{unit}/submit')
    data = request.form
    logger.debug(f'Form data: {data}')
    word_id = data.get('word_id')
    answer = data.get('answer', '').strip().lower()
    if not word_id or not answer:
        logger.warning('Word ID or answer missing')
        return jsonify({'error': '单词ID或答案不能为空'}), 400
    with app.app_context():
        try:
            word = Word.query.get_or_404(word_id)
            if word.wordbook_id != id or word.unit != unit:
                logger.warning(f'Invalid word ID {word_id} for wordbook {id}, unit {unit}')
                return jsonify({'error': '无效的单词ID'}), 400
            correct = answer == word.english.lower()
            progress = UserWordProgress.query.filter_by(
                user_id=session['user_id'], wordbook_id=id, unit=unit
            ).first()
            if not progress:
                progress = UserWordProgress(
                    user_id=session['user_id'],
                    wordbook_id=id,
                    unit=unit,
                    is_completed_a=0,
                    is_completed_b=0,
                    last_attempted=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    correct_count_a=0,
                    incorrect_count_a=0,
                    correct_count_b=0,
                    incorrect_count_b=0,
                    created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                db.session.add(progress)
            if correct:
                progress.correct_count_a += 1
                message = '正确'
            else:
                progress.incorrect_count_a += 1
                message = f'错误，正确答案是 {word.english}'
            progress.last_attempted = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            words = Word.query.filter_by(wordbook_id=id, unit=unit).count()
            if progress.correct_count_a >= words and progress.incorrect_count_a == 0:
                progress.is_completed_a = 1
            db.session.commit()
            logger.info(f'Answer submitted for word {word_id}: {"correct" if correct else "incorrect"}')
            return jsonify({'correct': correct, 'message': message}), 200
        except Exception as e:
            logger.error(f'Error submitting answer: {str(e)}')
            db.session.rollback()
            return jsonify({'error': '服务器错误，请稍后重试'}), 500

@app.route('/wordbook/<int:id>/practice_a/<unit>/complete', methods=['POST'])
@login_required
def practice_a_complete(id, unit):
    logger.debug(f'Received request to /wordbook/{id}/practice_a/{unit}/complete')
    with app.app_context():
        try:
            progress = UserWordProgress.query.filter_by(
                user_id=session['user_id'], wordbook_id=id, unit=unit
            ).first_or_404()
            progress.is_completed_a = 1
            progress.last_attempted = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            db.session.commit()
            logger.info(f'Practice A completed for wordbook {id}, unit {unit} for user {session["user_id"]}')
            return jsonify({
                'message': '练习完成！现在可以开始第二阶段的练习了。',
                'redirect_url': url_for('wordbook_detail', id=id)
            }), 200
        except Exception as e:
            logger.error(f'Error completing practice A: {str(e)}')
            db.session.rollback()
            return jsonify({'error': '服务器错误，请稍后重试'}), 500

@app.route('/wordbook/<int:id>/practice_b/<unit>', methods=['GET'])
@login_required
def practice_b(id, unit):
    logger.debug(f'Received request to /wordbook/{id}/practice_b/{unit}')
    with app.app_context():
        wordbook = WordBook.query.get_or_404(id)
        progress = UserWordProgress.query.filter_by(user_id=session['user_id'], wordbook_id=id, unit=unit).first()
        if not progress or not progress.is_completed_a:
            logger.warning(f'Mode B not unlocked for wordbook {id}, unit {unit}')
            return jsonify({'error': '请先完成填空模式（模式A）'}), 403
        words = Word.query.filter_by(wordbook_id=id, unit=unit).all()
        if not words:
            logger.warning(f'No words found for wordbook {id}, unit {unit}')
            return jsonify({'error': '该单元没有单词'}), 404
        words_data = [{
            'id': w.id,
            'chinese': w.chinese,
            'english': w.english,
            'full_blank': generate_full_blank_word(w.english),
            'wordbook_id': id,
            'unit': unit
        } for w in words]
        return render_template('practice_b.html', wordbook=wordbook, unit=unit, words=words_data)

@app.route('/wordbook/<int:id>/practice_b/<unit>/submit', methods=['POST'])
@login_required
def practice_b_submit(id, unit):
    logger.debug(f'Received request to /wordbook/{id}/practice_b/{unit}/submit')
    data = request.form
    logger.debug(f'Form data: {data}')
    word_id = data.get('word_id')
    answer = data.get('answer', '').strip().lower()
    if not word_id or not answer:
        logger.warning('Word ID or answer missing')
        return jsonify({'error': '单词ID或答案不能为空'}), 400
    with app.app_context():
        try:
            word = Word.query.get_or_404(word_id)
            if word.wordbook_id != id or word.unit != unit:
                logger.warning(f'Invalid word ID {word_id} for wordbook {id}, unit {unit}')
                return jsonify({'error': '无效的单词ID'}), 400
            correct = answer == word.english.lower()
            progress = UserWordProgress.query.filter_by(
                user_id=session['user_id'], wordbook_id=id, unit=unit
            ).first()
            if not progress:
                progress = UserWordProgress(
                    user_id=session['user_id'],
                    wordbook_id=id,
                    unit=unit,
                    is_completed_a=0,
                    is_completed_b=0,
                    last_attempted=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    correct_count_a=0,
                    incorrect_count_a=0,
                    correct_count_b=0,
                    incorrect_count_b=0,
                    created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                db.session.add(progress)
            mistake = UserWordMistake.query.filter_by(
                user_id=session['user_id'], word_id=word_id, mode='B'
            ).first()
            if correct:
                progress.correct_count_b += 1
                message = '正确'
                if mistake:
                    mistake.correct_count += 1
                    if mistake.correct_count >= 2:
                        db.session.delete(mistake)
                        message = '正确，此单词已熟练掌握，已从错题本移除'
            else:
                progress.incorrect_count_b += 1
                message = f'错误，正确答案是 {word.english}'
                if mistake:
                    mistake.incorrect_count += 1
                    mistake.correct_count = 0
                    mistake.last_incorrect = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                else:
                    mistake = UserWordMistake(
                        user_id=session['user_id'],
                        word_id=word_id,
                        wordbook_id=id,
                        unit=unit,
                        mode='B',
                        incorrect_count=1,
                        correct_count=0,
                        last_incorrect=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                    db.session.add(mistake)
            progress.last_attempted = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            words = Word.query.filter_by(wordbook_id=id, unit=unit).count()
            if progress.correct_count_b >= words and progress.incorrect_count_b == 0:
                progress.is_completed_b = 1
            db.session.commit()
            logger.info(f'Answer submitted for word {word_id}: {"correct" if correct else "incorrect"}')
            return jsonify({'correct': correct, 'message': message}), 200
        except Exception as e:
            logger.error(f'Error submitting answer: {str(e)}')
            db.session.rollback()
            return jsonify({'error': '服务器错误，请稍后重试'}), 500

@app.route('/review/<int:wordbook_id>', methods=['GET'])
@login_required
def review(wordbook_id):
    logger.debug(f'Received request to /review/{wordbook_id}')
    with app.app_context():
        wordbook = WordBook.query.get_or_404(wordbook_id)
        units = db.session.query(
            UserWordMistake.unit,
            db.func.count(UserWordMistake.id).label('mistake_count')
        ).filter_by(
            user_id=session['user_id'], wordbook_id=wordbook_id, mode='B'
        ).group_by(UserWordMistake.unit).all()
        units_data = [{'unit': unit, 'mistake_count': mistake_count} for unit, mistake_count in units]
        return render_template('review.html', wordbook=wordbook, units=units_data)

@app.route('/wordbook/<int:id>/review_b/<unit>', methods=['GET'])
@login_required
def review_mode_b(id, unit):
    logger.debug(f'Received request to /wordbook/{id}/review_b/{unit}')
    with app.app_context():
        wordbook = WordBook.query.get_or_404(id)
        mistakes = UserWordMistake.query.filter_by(
            user_id=session['user_id'], wordbook_id=id, unit=unit, mode='B'
        ).join(Word, UserWordMistake.word_id == Word.id).order_by(UserWordMistake.last_incorrect.desc()).all()
        if not mistakes:
            logger.warning(f'No mistakes found for wordbook {id}, unit {unit}')
            return jsonify({'error': '该单元没有错题'}), 404
        words_data = [{
            'id': m.word_id,
            'chinese': m.word.chinese,
            'english': m.word.english,
            'full_blank': generate_full_blank_word(m.word.english),
            'wordbook_id': id,
            'unit': unit
        } for m in mistakes]
        return render_template('review_mode_b.html', wordbook=wordbook, unit=unit, words=words_data)

@app.route('/wordbook/<int:id>/review_b/<unit>/submit', methods=['POST'])
@login_required
def review_b_submit(id, unit):
    logger.debug(f'Received request to /wordbook/{id}/review_b/{unit}/submit')
    data = request.form
    logger.debug(f'Form data: {data}')
    word_id = data.get('word_id')
    answer = data.get('answer', '').strip().lower()
    if not word_id or not answer:
        logger.warning('Word ID or answer missing')
        return jsonify({'error': '单词ID或答案不能为空'}), 400
    with app.app_context():
        try:
            word = Word.query.get_or_404(word_id)
            if word.wordbook_id != id or word.unit != unit:
                logger.warning(f'Invalid word ID {word_id} for wordbook {id}, unit {unit}')
                return jsonify({'error': '无效的单词ID'}), 400
            correct = answer == word.english.lower()
            progress = UserWordProgress.query.filter_by(
                user_id=session['user_id'], wordbook_id=id, unit=unit
            ).first()
            if not progress:
                progress = UserWordProgress(
                    user_id=session['user_id'],
                    wordbook_id=id,
                    unit=unit,
                    is_completed_a=0,
                    is_completed_b=0,
                    last_attempted=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    correct_count_a=0,
                    incorrect_count_a=0,
                    correct_count_b=0,
                    incorrect_count_b=0,
                    created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                db.session.add(progress)
            mistake = UserWordMistake.query.filter_by(
                user_id=session['user_id'], word_id=word_id, mode='B'
            ).first()
            if correct:
                progress.correct_count_b += 1
                message = '正确'
                if mistake:
                    mistake.correct_count += 1
                    if mistake.correct_count >= 2:
                        db.session.delete(mistake)
                        message = '正确，此单词已熟练掌握，已从错题本移除'
            else:
                progress.incorrect_count_b += 1
                message = f'错误，正确答案是 {word.english}'
                if mistake:
                    mistake.incorrect_count += 1
                    mistake.correct_count = 0
                    mistake.last_incorrect = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                else:
                    mistake = UserWordMistake(
                        user_id=session['user_id'],
                        word_id=word_id,
                        wordbook_id=id,
                        unit=unit,
                        mode='B',
                        incorrect_count=1,
                        correct_count=0,
                        last_incorrect=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                    db.session.add(mistake)
            progress.last_attempted = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            words = Word.query.filter_by(wordbook_id=id, unit=unit).count()
            if progress.correct_count_b >= words and progress.incorrect_count_b == 0:
                progress.is_completed_b = 1
            db.session.commit()
            logger.info(f'Answer submitted for word {word_id}: {"correct" if correct else "incorrect"}')
            return jsonify({'correct': correct, 'message': message}), 200
        except Exception as e:
            logger.error(f'Error submitting answer: {str(e)}')
            db.session.rollback()
            return jsonify({'error': '服务器错误，请稍后重试'}), 500

@app.route('/admin/user_progress', methods=['GET'])
@login_required
@admin_required
def admin_user_progress():
    logger.debug('Received request to /admin/user_progress')
    with app.app_context():
        users = User.query.all()
        wordbooks = WordBook.query.all()
        user_progress_data = []
        for user in users:
            user_data = {
                'username': user.username,
                'progress': []
            }
            for wordbook in wordbooks:
                units = db.session.query(Word.unit).filter_by(wordbook_id=wordbook.id).distinct().all()
                for unit in units:
                    unit = unit[0]
                    progress = UserWordProgress.query.filter_by(
                        user_id=user.id, wordbook_id=wordbook.id, unit=unit
                    ).first()
                    user_data['progress'].append({
                        'wordbook_title': wordbook.title,
                        'unit': unit,
                        'is_completed_a': progress.is_completed_a if progress else 0,
                        'is_completed_b': progress.is_completed_b if progress else 0,
                        'correct_count_a': progress.correct_count_a if progress else 0,
                        'incorrect_count_a': progress.incorrect_count_a if progress else 0,
                        'correct_count_b': progress.correct_count_b if progress else 0,
                        'incorrect_count_b': progress.incorrect_count_b if progress else 0,
                        'last_attempted': progress.last_attempted if progress else '未尝试'
                    })
            user_progress_data.append(user_data)
        return render_template('admin_user_progress.html', users=user_progress_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
