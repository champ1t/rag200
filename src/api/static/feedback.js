// Feedback Demo JavaScript

const API_BASE = 'http://localhost:8000';

let selectedRating = null;

// DOM Elements
const likeBtn = document.getElementById('likeBtn');
const dislikeBtn = document.getElementById('dislikeBtn');
const commentBox = document.getElementById('commentBox');
const submitBtn = document.getElementById('submitBtn');
const message = document.getElementById('message');

// Sample query data (in real app, this would come from query response)
const queryData = {
    query_id: generateQueryId(),
    session_id: 'demo-session-' + Date.now(),
    query: document.getElementById('queryText').textContent,
    answer: document.getElementById('answerText').textContent,
    route: 'contact'
};

// Event Listeners
likeBtn.addEventListener('click', () => selectRating('like'));
dislikeBtn.addEventListener('click', () => selectRating('dislike'));
submitBtn.addEventListener('click', submitFeedback);

// Initialize
loadStats();

// Functions
function selectRating(rating) {
    selectedRating = rating;

    // Update button states
    likeBtn.classList.remove('selected');
    dislikeBtn.classList.remove('selected');

    if (rating === 'like') {
        likeBtn.classList.add('selected');
    } else {
        dislikeBtn.classList.add('selected');
    }

    // Enable submit button
    submitBtn.disabled = false;
}

async function submitFeedback() {
    if (!selectedRating) {
        showMessage('กรุณาเลือก 👍 หรือ 👎', 'error');
        return;
    }

    const comment = commentBox.value.trim();

    const feedbackData = {
        ...queryData,
        rating: selectedRating,
        comment: comment
    };

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = 'กำลังส่ง...';

        const response = await fetch(`${API_BASE}/feedback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(feedbackData)
        });

        const result = await response.json();

        if (result.success) {
            showMessage('✅ ขอบคุณสำหรับ Feedback!', 'success');

            // Disable form after submit
            likeBtn.disabled = true;
            dislikeBtn.disabled = true;
            commentBox.disabled = true;

            // Reload stats
            setTimeout(loadStats, 500);
        } else {
            showMessage('❌ ' + result.message, 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = 'ส่ง Feedback';
        }
    } catch (error) {
        showMessage('❌ เกิดข้อผิดพลาด: ' + error.message, 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = 'ส่ง Feedback';
    }
}

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/feedback/stats`);
        const stats = await response.json();

        document.getElementById('totalFeedback').textContent = stats.total || 0;
        document.getElementById('likeRate').textContent = (stats.like_rate || 0) + '%';
        document.getElementById('likesCount').textContent = stats.likes || 0;
        document.getElementById('dislikesCount').textContent = stats.dislikes || 0;
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

function showMessage(text, type) {
    message.textContent = text;
    message.className = 'message ' + type;
    message.style.display = 'block';

    // Auto-hide after 5 seconds
    setTimeout(() => {
        message.style.display = 'none';
    }, 5000);
}

function generateQueryId() {
    return 'demo-' + Math.random().toString(36).substring(2, 15);
}
