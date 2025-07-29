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
        const response = await fetch(`/wordbook/${id}/select`, {
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
            setTimeout(() => {
                currentIndex++;
                showWordCard(currentIndex);
            }, 1000);
        } else {
            feedbackDiv.textContent = data.error || '提交失败';
            feedbackDiv.style.color = '#d33';
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

// 登录页面
if (document.getElementById('login-form')) {
    console.log('Login form detected');
    submitForm('login-form', '/login', '/');
}