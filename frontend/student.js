// Elements
const authScreen = document.getElementById("auth-screen");
const chatScreen = document.getElementById("chat-screen");
const studentSelect = document.getElementById("student-select");
const customNameGroup = document.getElementById("custom-name-group");
const customNameInput = document.getElementById("student-custom-name");
const startBtn = document.getElementById("start-btn");
const switchProfileBtn = document.getElementById("switch-profile-btn");
const studentAvatar = document.getElementById("student-avatar");
const displayName = document.getElementById("display-name");
const currentTopicTag = document.getElementById("current-topic-tag");
const chatHistory = document.getElementById("chat-history");
const recordBtn = document.getElementById("record-btn");
const voiceStatus = document.getElementById("voice-status");
const textInput = document.getElementById("text-input");
const sendBtn = document.getElementById("send-btn");

let currentStudent = "";
let activeSubject = ""; // Active subject filter
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let spacePressed = false;

// Handle profile select changes
studentSelect.addEventListener("change", () => {
    if (studentSelect.value === "custom") {
        customNameGroup.style.display = "block";
    } else {
        customNameGroup.style.display = "none";
    }
});

// Start Session
startBtn.addEventListener("click", async () => {
    let name = studentSelect.value;
    if (name === "custom") {
        name = customNameInput.value.trim();
    }
    
    if (!name) {
        alert("Please select or enter a name to start.");
        return;
    }
    
    currentStudent = name;
    activeSubject = ""; // Reset active subject selection
    
    // UI Updates
    studentAvatar.textContent = name.charAt(0).toUpperCase();
    displayName.textContent = name;
    
    authScreen.style.display = "none";
    chatScreen.style.display = "flex";
    
    currentTopicTag.textContent = "Selecting Subject...";
    
    // Welcome student and ask what subject they want to learn
    chatHistory.innerHTML = `
        <div class="message assistant" id="subject-selection-msg">
            <h3>Baymax</h3>
            <p>Hello ${currentStudent}! I am Baymax, your classroom learning companion. <strong>What do you want to learn today?</strong></p>
            <p style="font-size: 0.875rem; color: var(--text-secondary); margin-top: 0.5rem;">Select from the available subjects below, or type/say a subject name!</p>
            <div style="margin-top: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem;" id="subject-chips">
                <span style="font-size: 0.875rem; color: var(--text-secondary); font-style: italic;">Loading subjects...</span>
            </div>
        </div>
    `;
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    // Fetch available subjects from the backend
    try {
        const res = await fetch("/api/subjects");
        if (res.ok) {
            const subjects = await res.json();
            const container = document.getElementById("subject-chips");
            if (subjects && subjects.length > 0) {
                container.innerHTML = subjects.map(sub => `
                    <button class="btn" style="width: auto; padding: 0.4rem 0.8rem; background: linear-gradient(135deg, var(--accent-purple), #6d28d9); font-size: 0.875rem; box-shadow: none;" onclick="setStudentSubject('${sub.replace(/'/g, "\\'")}')">${sub}</button>
                `).join('');
            } else {
                container.innerHTML = `<span style="font-size: 0.875rem; color: var(--text-secondary); font-style: italic;">No subjects uploaded yet. Type a subject name below to start!</span>`;
            }
        }
    } catch (err) {
        console.error("Error loading subjects:", err);
    }
});

// Setup active subject
window.setStudentSubject = function(subjectName) {
    if (activeSubject) return; // Already selected
    
    activeSubject = subjectName.trim();
    // Capitalize first letter of subject
    activeSubject = activeSubject.charAt(0).toUpperCase() + activeSubject.slice(1);
    
    currentTopicTag.textContent = activeSubject;
    
    // UI clean-up: Remove selection chips container
    const chipsContainer = document.getElementById("subject-chips");
    if (chipsContainer) {
        chipsContainer.innerHTML = `<span style="font-size: 0.875rem; color: var(--accent-cyan); font-weight: 600;">Learning Target: ${activeSubject}</span>`;
    }
    
    addUserMessage(`I want to learn ${activeSubject}`);
    
    // Baymax responds confirming choice
    showLoadingIndicator();
    setTimeout(() => {
        removeLoadingIndicator();
        addAssistantMessage(`Excellent choice! Let's learn about **${activeSubject}**. Ask me any questions, and I will search our classroom materials to help you!`);
    }, 800);
};

// Switch profile
switchProfileBtn.addEventListener("click", () => {
    chatScreen.style.display = "none";
    authScreen.style.display = "block";
    activeSubject = "";
    // Reset state
    chatHistory.innerHTML = `
        <div class="message assistant">
            <h3>Baymax</h3>
            <p>Hello! I am Baymax, your personal learning companion. I am here to help you understand your class materials. You can hold down the microphone button (or press and hold the <strong>Spacebar</strong>) to ask me a question, or type below!</p>
        </div>
    `;
});

// Helper to format simple markdown (bold, bullets) safely
function formatMarkdown(text) {
    if (!text) return "";
    
    // Escape HTML to prevent injection
    let escaped = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
        
    // Replace markdown bold (**word**) with <strong>word</strong>
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Replace bullet points starting with '*' followed by a space/tab, preserving leading indentation
    escaped = escaped.split('\n').map(line => {
        let trimmed = line.trim();
        if (trimmed.startsWith('*') && (trimmed[1] === ' ' || trimmed[1] === '\t')) {
            let match = line.match(/^(\s*)\*/);
            let indent = match ? match[1] : '';
            let indentHtml = indent.replace(/ /g, '&nbsp;').replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;');
            let content = trimmed.substring(1).trim();
            return indentHtml + `• ${content}`;
        }
        return line;
    }).join('\n');
    
    // Replace newlines with <br>
    return escaped.replace(/\n/g, '<br>');
}

// Helper: Append assistant message
function addAssistantMessage(text, sources = [], topic = "", grounded = null, groundingRationale = "", relevantContext = "") {
    const msgDiv = document.createElement("div");
    msgDiv.className = "message assistant";
    
    let html = `<h3>Baymax</h3><p>${formatMarkdown(text)}</p>`;
    
    // If we have sources, add them
    if (sources && sources.length > 0) {
        html += `<div class="sources-list">`;
        const uniqueSources = [...new Set(sources.map(s => s.metadata.source))];
        uniqueSources.forEach(src => {
            html += `<span class="source-tag"><i data-lucide="book-open" style="width:12px;height:12px;display:inline-block;vertical-align:middle;margin-right:3px;"></i> ${src}</span>`;
        });
        html += `</div>`;
    }

    // Add grounding badge if grounding information is provided
    if (grounded !== null) {
        html += `<div class="grounding-badge-container">`;
        if (grounded) {
            html += `
                <span class="grounding-badge grounded">
                    <i data-lucide="shield-check"></i> Grounded in Class Materials
                    <span class="grounding-tooltip">
                        <strong>Grounding Verification Rationale:</strong><br>
                        ${escapeHtml(groundingRationale || 'Verified and entailed by class materials.')}
                        ${relevantContext ? `<br><br><strong>Extracted Context:</strong><br><em>"${escapeHtml(relevantContext)}"</em>` : ''}
                    </span>
                </span>
            `;
        } else {
            html += `
                <span class="grounding-badge general-knowledge">
                    <i data-lucide="info"></i> General Knowledge
                    <span class="grounding-tooltip">
                        <strong>Verification Details:</strong><br>
                        ${escapeHtml(groundingRationale || 'Not found in class materials. Explaining generally.')}
                    </span>
                </span>
            `;
        }
        html += `</div>`;
    }
    
    msgDiv.innerHTML = html;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    // Only update topic tag if it matches our active subject or is generated
    if (topic && topic !== "General" && topic !== "None" && !activeSubject) {
        currentTopicTag.textContent = topic;
    }
    
    lucide.createIcons();
}

// Simple HTML escaping helper to prevent XSS in tooltips
function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function addSystemMessage(text) {
    const msgDiv = document.createElement("div");
    msgDiv.className = "message assistant";
    msgDiv.innerHTML = `<h3>System Notification</h3><p>${text}</p>`;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Helper: Append user message
function addUserMessage(text) {
    const msgDiv = document.createElement("div");
    msgDiv.className = "message user";
    msgDiv.innerHTML = `<p>${text}</p>`;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Send typed text question
async function sendTextMessage() {
    const text = textInput.value.trim();
    if (!text) return;
    
    // If subject has not been selected yet, treat input as the subject selection
    if (!activeSubject) {
        textInput.value = "";
        window.setStudentSubject(text);
        return;
    }
    
    addUserMessage(text);
    textInput.value = "";
    showLoadingIndicator();
    
    const formData = new FormData();
    formData.append("student_name", currentStudent);
    formData.append("question", text);
    formData.append("subject", activeSubject);
    
    await submitChatForm(formData);
}

sendBtn.addEventListener("click", sendTextMessage);
textInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        sendTextMessage();
    }
});

// Show temporary loading indicator
let loadingDiv = null;
function showLoadingIndicator() {
    removeLoadingIndicator();
    loadingDiv = document.createElement("div");
    loadingDiv.className = "message assistant";
    loadingDiv.innerHTML = `
        <h3>Baymax</h3>
        <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    chatHistory.appendChild(loadingDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function removeLoadingIndicator() {
    if (loadingDiv && loadingDiv.parentNode) {
        loadingDiv.parentNode.removeChild(loadingDiv);
    }
    loadingDiv = null;
}

// Audio Recording API Interface
async function startAudioRecording() {
    if (isRecording) return;
    
    audioChunks = [];
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
            
            showLoadingIndicator();
            voiceStatus.textContent = "Processing speech and thinking...";
            
            const formData = new FormData();
            formData.append("student_name", currentStudent);
            formData.append("audio", audioBlob, "recording.webm");
            if (activeSubject) {
                formData.append("subject", activeSubject);
            }
            
            // If in subject selection phase, handle speech transcription separately
            try {
                const response = await fetch("/api/chat", {
                    method: "POST",
                    body: formData
                });
                
                removeLoadingIndicator();
                
                if (!response.ok) {
                    const err = await response.json();
                    addAssistantMessage(`Sorry, I encountered an error: ${err.detail || "Unknown error"}`);
                    return;
                }
                
                const data = await response.json();
                
                if (!activeSubject && data.question) {
                    // Set active subject to the voice transcript
                    window.setStudentSubject(data.question);
                    return;
                }
                
                if (data.question) {
                    addUserMessage(data.question);
                }
                addAssistantMessage(
                    data.response, 
                    data.retrieved_chunks || [], 
                    data.topic, 
                    data.grounded !== undefined ? data.grounded : null, 
                    data.grounding_rationale, 
                    data.relevant_context
                );
            } catch (err) {
                removeLoadingIndicator();
                console.error("Network error submitting audio:", err);
                addAssistantMessage("Sorry, I could not process your speech. Check your server connection.");
            }
            
            // Turn off microphone tracks
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start();
        isRecording = true;
        recordBtn.classList.add("recording");
        voiceStatus.textContent = "Listening... Release button/spacebar when done.";
    } catch (err) {
        console.error("Error accessing microphone:", err);
        voiceStatus.textContent = "Microphone error! Ensure permissions are granted.";
    }
}

function stopAudioRecording() {
    if (!isRecording) return;
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
    }
    isRecording = false;
    recordBtn.classList.remove("recording");
    voiceStatus.textContent = "Hold Spacebar or Click Mic to talk";
}

// Submit Chat Request to Server
async function submitChatForm(formData) {
    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            body: formData
        });
        
        removeLoadingIndicator();
        
        if (!response.ok) {
            const err = await response.json();
            addAssistantMessage(`Sorry, I encountered an error: ${err.detail || "Unknown error"}`);
            return;
        }
        
        const data = await response.json();
        
        if (data.question && !formData.has("audio")) {
            // Already added user message for text queries
        } else if (data.question && formData.has("audio")) {
            addUserMessage(data.question);
        }
        
        addAssistantMessage(
            data.response, 
            data.retrieved_chunks || [], 
            data.topic, 
            data.grounded !== undefined ? data.grounded : null, 
            data.grounding_rationale, 
            data.relevant_context
        );
    } catch (err) {
        removeLoadingIndicator();
        console.error("Network error submitting chat:", err);
        addAssistantMessage("Sorry, I could not connect to the tutor service. Please check if the server is running.");
    }
}

// Record Button Events
recordBtn.addEventListener("mousedown", startAudioRecording);
recordBtn.addEventListener("mouseup", stopAudioRecording);
recordBtn.addEventListener("mouseleave", stopAudioRecording);

// Touch support for tablets/mobile
recordBtn.addEventListener("touchstart", (e) => {
    e.preventDefault();
    startAudioRecording();
});
recordBtn.addEventListener("touchend", (e) => {
    e.preventDefault();
    stopAudioRecording();
});

// Spacebar Hold-to-Talk Event Listeners
document.addEventListener("keydown", (e) => {
    // Only record if spacebar is held down AND user is NOT active inside any input field
    const activeEl = document.activeElement;
    const isTyping = activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "SELECT" || activeEl.tagName === "TEXTAREA");
    
    if (e.code === "Space" && !isTyping) {
        e.preventDefault();
        if (!spacePressed) {
            spacePressed = true;
            startAudioRecording();
        }
    }
});

document.addEventListener("keyup", (e) => {
    if (e.code === "Space" && spacePressed) {
        e.preventDefault();
        spacePressed = false;
        stopAudioRecording();
    }
});
