async function submitForm(formId, url, redirectUrl) {
    const form = document.getElementById(formId);
    const messageDiv = document.getElementById('message');
    const submitButton = form.querySelector('button[type="submit"]');
    console.log(`Binding submit event to form: ${formId}`);
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        submitButton.disabled = true;
        messageDiv.textContent = '处理中...';
        console.log(`Submitting form ${formId} to ${url}`);
        const formData = new FormData(form);
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            console.log('Response:', data);
            if (response.ok) {
                messageDiv.textContent = data.message;
                setTimeout(() => {
                    window.location.href = redirectUrl;
                }, 1000);
            } else {
                messageDiv.textContent = data.error || '未知错误';
                submitButton.disabled = false;
            }
        } catch (error) {
            console.error('Fetch error:', error);
            messageDiv.textContent = '网络错误，请稍后重试';
            submitButton.disabled = false;
        }
    });
}

async function deleteWordbook(id) {
    if (!confirm('确定删除此单词书？')) return;
    const messageDiv = document.getElementById('message');
    try {
        const response = await fetch(`/wordbook/${id}/delete`, {
            method: 'POST'
        });
        const data = await response.json();
        console.log('Response:', data);
        if (response.ok) {
            messageDiv.textContent = data.message;
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            messageDiv.textContent = data.error || '删除失败';
        }
    } catch (error) {
        console.error('Fetch error:', error);
        messageDiv.textContent = '网络错误，请稍后重试';
    }
}

async function selectWordbook(id) {
    const messageDiv = document.getElementById('message');
    try {
        const response = await fetch(window.location.origin + `/wordbook/${id}/select`, {
            method: 'POST'
        });
        const data = await response.json();
        console.log('Response:', data);
        if (response.ok) {
            messageDiv.textContent = data.message;
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            messageDiv.textContent = data.error || '选择失败';
        }
    } catch (error) {
        console.error('Fetch error:', error);
        messageDiv.textContent = '网络错误，请稍后重试';
    }
}

function addWordCard() {
    const wordCards = document.getElementById('word-cards');
    const cards = wordCards.querySelectorAll('.word-card');
    const count = cards.length;
    let lastUnit = '';
    if (count > 0) {
        const lastCard = cards[count - 1];
        lastUnit = lastCard.querySelector('input[name$="[unit]"]').value || '';
    }
    const card = document.createElement('div');
    card.className = 'card word-card';
    card.innerHTML = `
        <label>单元</label>
        <input type="text" name="words[${count}][unit]" value="${lastUnit}" required maxlength="50">
        <label>英文</label>
        <input type="text" name="words[${count}][english]" required maxlength="50">
        <label>中文</label>
        <input type="text" name="words[${count}][chinese]" required maxlength="50">
        <button type="button" class="btn btn-danger" onclick="deleteWordCard(this)">删除</button>
    `;
    wordCards.appendChild(card);
}

function deleteWordCard(button, wordId = null) {
    if (wordId) {
        const form = document.getElementById('wordbook-edit-form');
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'delete_words';
        input.value = wordId;
        form.appendChild(input);
    }
    button.parentElement.remove();
}

function speakWord(word) {
    const utterance = new SpeechSynthesisUtterance(word);
    utterance.lang = 'en-US';
    window.speechSynthesis.speak(utterance);
}

// 语音播报反馈
function speakFeedback(message) {
    if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(message);
        utterance.lang = 'zh-CN';
        utterance.rate = 0.9;
        utterance.pitch = 1.2;
        speechSynthesis.speak(utterance);
    }
}

async function submitAnswer(wordId) {
    console.log('submitAnswer called with wordId:', wordId);
    console.log('words[currentIndex]:', words[currentIndex]);
    const answerInput = document.getElementById('answer');
    const answer = answerInput.value.trim();
    if (!answer) {
        document.getElementById('message').textContent = '答案不能为空';
        return;
    }
    const feedbackDiv = document.querySelector('.feedback');
    const submitButton = document.querySelector('.word-card button[onclick^="submitAnswer"]');
    if (!submitButton) {
        console.error('Submit button not found');
        document.getElementById('message').textContent = '提交按钮未找到，请刷新页面';
        return;
    }
    if (!feedbackDiv) {
        console.error('Feedback div not found');
        document.getElementById('message').textContent = '反馈区域未找到，请刷新页面';
        return;
    }
    if (!answerInput) {
        console.error('Answer input not found');
        document.getElementById('message').textContent = '输入框未找到，请刷新页面';
        return;
    }
    submitButton.disabled = true;
    answerInput.disabled = true;
    const formData = new FormData();
    formData.append('word_id', wordId);
    formData.append('answer', answer);
    const isModeA = window.location.pathname.includes('/practice_a/');
    const isReviewB = window.location.pathname.includes('/review_b/');
    const url = isReviewB
        ? `/wordbook/${words[currentIndex].wordbook_id}/review_b/${encodeURIComponent(words[currentIndex].unit)}/submit`
        : isModeA
            ? `/wordbook/${words[currentIndex].wordbook_id}/practice_a/${encodeURIComponent(words[currentIndex].unit)}/submit`
            : `/wordbook/${words[currentIndex].wordbook_id}/practice_b/${encodeURIComponent(words[currentIndex].unit)}/submit`;
    console.log('Fetch URL:', url);
    console.log('FormData:', Object.fromEntries(formData));
    try {
        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        console.log('Response:', data);
        if (response.ok) {
            feedbackDiv.textContent = data.message;
            feedbackDiv.style.color = data.correct ? '#28a745' : '#d33';
            
            // 语音播报结果
            if (data.correct) {
                speakFeedback('太棒了！答对了！');
            } else {
                speakFeedback('再试试看，加油！');
            }
            
            setTimeout(() => {
                currentIndex++;
                showWordCard(currentIndex);
            }, 1500);
        } else {
            feedbackDiv.textContent = data.error || '提交失败';
            feedbackDiv.style.color = '#d33';
            speakFeedback('请输入答案哦');
            submitButton.disabled = false;
            answerInput.disabled = false;
        }
    } catch (error) {
        console.error('Fetch error:', error);
        feedbackDiv.textContent = '网络错误，请稍后重试';
        feedbackDiv.style.color = '#d33';
        submitButton.disabled = false;
        answerInput.disabled = false;
    }
}

// 注册页面
if (document.getElementById('register-form')) {
    console.log('Register form detected');
    submitForm('register-form', '/register', '/login');
}

// 生成设备指纹
async function generateDeviceFingerprint() {
    try {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillText('设备指纹测试', 2, 2);
        
        const canvasData = canvas.toDataURL();
        const screenInfo = `${screen.width}x${screen.height}`;
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        const language = navigator.language;
        const platform = navigator.platform;
        
        const combinedString = `${canvasData}|${screenInfo}|${timezone}|${language}|${platform}`;
        
        // 检查是否支持Web Crypto API
        if (window.crypto && window.crypto.subtle) {
            // 使用Web Crypto API生成哈希
            const encoder = new TextEncoder();
            const data = encoder.encode(combinedString);
            const hashBuffer = await crypto.subtle.digest('SHA-256', data);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
            return hashHex;
        } else {
            // 简单的备用方案
            let hash = 0;
            for (let i = 0; i < combinedString.length; i++) {
                const char = combinedString.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash; // 转换为32位整数
            }
            return Math.abs(hash).toString(16);
        }
    } catch (error) {
        console.error('生成设备指纹失败:', error);
        // 返回一个基于时间的简单指纹
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
}

// 检查设备授权并自动登录
async function checkDeviceAuth() {
    try {
        const deviceFingerprint = await generateDeviceFingerprint();
        const response = await fetch(window.location.origin + '/check_device_auth', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                device_fingerprint: deviceFingerprint
            })
        });
        
        const data = await response.json();
        if (data.success && data.token) {
            // 自动登录成功
            window.location.href = '/';
        }
    } catch (error) {
        console.log('设备自动登录检查失败，需要手动登录');
    }
}

// 登录页面
if (document.getElementById('login-form')) {
    console.log('Login form detected');
    
    // 检查自动登录
    checkDeviceAuth();
    
    // 记住用户名功能
    const usernameInput = document.getElementById('username');
    const rememberCheckbox = document.getElementById('remember-me');
    
    // 加载保存的用户名
    const savedUsername = localStorage.getItem('savedUsername');
    if (savedUsername) {
        usernameInput.value = savedUsername;
        rememberCheckbox.checked = true;
    }
    
    // 修改登录事件处理
    const loginForm = document.getElementById('login-form');
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const username = usernameInput.value;
        const password = document.getElementById('password').value;
        
        try {
            const deviceFingerprint = await generateDeviceFingerprint();
            const response = await fetch(window.location.origin + '/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    password: password,
                    device_fingerprint: deviceFingerprint,
                    device_name: '儿子的iPad' // 可以自定义设备名称
                })
            });
            
            const data = await response.json();
            if (response.ok) {
                window.location.href = '/';
            } else {
                document.getElementById('message').textContent = data.error;
            }
        } catch (error) {
            console.error('Login error:', error);
            document.getElementById('message').textContent = '登录失败，请重试';
        }
    });
    
    // 保存用户名
    loginForm.addEventListener('submit', function() {
        if (rememberCheckbox.checked) {
            localStorage.setItem('savedUsername', usernameInput.value);
        } else {
            localStorage.removeItem('savedUsername');
        }
    });
}

// 完成练习按钮
const completeBtn = document.getElementById('complete-btn');
if (completeBtn) {
    completeBtn.addEventListener('click', async () => {
        console.log('Complete button clicked');
        const messageDiv = document.getElementById('message');
        if (!words || words.length === 0) {
            messageDiv.textContent = '没有单词信息，无法完成练习';
            return;
        }
        const wordbookId = words[0].wordbook_id;
        const unit = words[0].unit;
        const url = `/wordbook/${wordbookId}/practice_a/${encodeURIComponent(unit)}/complete`;
        
        completeBtn.disabled = true;
        messageDiv.textContent = '正在提交...';
        
        try {
            const response = await fetch(url, {
                method: 'POST'
            });
            const data = await response.json();
            console.log('Response:', data);
            if (response.ok) {
                messageDiv.textContent = data.message;
                setTimeout(() => {
                    window.location.href = data.redirect_url;
                }, 1500);
            } else {
                messageDiv.textContent = data.error || '操作失败';
                completeBtn.disabled = false;
            }
        } catch (error) {
            console.error('Fetch error:', error);
            messageDiv.textContent = '网络错误，请稍后重试';
            completeBtn.disabled = false;
        }
    });
}
