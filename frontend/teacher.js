// Elements
const uploadZone = document.getElementById("upload-zone");
const fileInput = document.getElementById("file-input");
const uploadSubjectSelect = document.getElementById("upload-subject-select");
const customSubjectGroup = document.getElementById("custom-subject-group");
const uploadSubjectCustom = document.getElementById("upload-subject-custom");
const uploadStatus = document.getElementById("upload-status");
const documentList = document.getElementById("document-list");
const statActiveStudents = document.getElementById("stat-active-students");
const statMaterialsCount = document.getElementById("stat-materials-count");
const statStruggleCount = document.getElementById("stat-struggle-count");
const studentTableBody = document.getElementById("student-table-body");
const recentChatsFeed = document.getElementById("recent-chats-feed");

// Handle subject dropdown change
uploadSubjectSelect.addEventListener("change", () => {
    if (uploadSubjectSelect.value === "custom") {
        customSubjectGroup.style.display = "block";
    } else {
        customSubjectGroup.style.display = "none";
    }
});

// Fetch subjects and update the dropdown list
async function refreshSubjectDropdown() {
    try {
        const response = await fetch("/api/subjects");
        if (!response.ok) throw new Error("Failed to fetch subjects");
        const subjects = await response.json();
        
        const currentValue = uploadSubjectSelect.value;
        
        // Reset options but keep General and Custom
        let html = `
            <option value="General">General</option>
        `;
        
        // Add existing subjects
        subjects.forEach(sub => {
            if (sub !== "General") {
                html += `<option value="${sub}">${sub}</option>`;
            }
        });
        
        html += `
            <option value="custom">Create New Subject...</option>
        `;
        
        uploadSubjectSelect.innerHTML = html;
        
        // Try to restore previous selection if it still exists
        if ([...uploadSubjectSelect.options].some(o => o.value === currentValue)) {
            uploadSubjectSelect.value = currentValue;
        } else {
            uploadSubjectSelect.value = "General";
            customSubjectGroup.style.display = "none";
        }
    } catch (err) {
        console.error("Error refreshing subject dropdown:", err);
    }
}

// Fetch dashboard data from API
async function fetchDashboardData() {
    try {
        const response = await fetch("/api/dashboard");
        if (!response.ok) throw new Error("Failed to fetch dashboard data");
        const data = await response.json();
        
        updateDashboardUI(data);
    } catch (err) {
        console.error("Error loading dashboard data:", err);
    }
}

// Update dashboard UI elements
function updateDashboardUI(data) {
    // 1. Update stats
    statActiveStudents.textContent = data.active_students_count;
    statMaterialsCount.textContent = data.documents.length;
    
    // Count total unique topics of struggle across class
    let uniqueStruggles = new Set();
    data.students.forEach(s => {
        if (s.weak_topics && s.weak_topics.length > 0) {
            s.weak_topics.forEach(t => uniqueStruggles.add(t));
        }
    });
    statStruggleCount.textContent = uniqueStruggles.size;
    
    // Calculate grounding rate from recent chats
    let groundedCount = 0;
    let chatsWithGrounding = 0;
    data.recent_chats.forEach(chat => {
        if (chat.grounded !== undefined && chat.grounded !== null) {
            chatsWithGrounding++;
            if (chat.grounded === 1 || chat.grounded === true) {
                groundedCount++;
            }
        }
    });
    const groundingRate = chatsWithGrounding > 0 ? Math.round((groundedCount / chatsWithGrounding) * 100) : 100;
    const statGroundedRate = document.getElementById("stat-grounded-rate");
    if (statGroundedRate) {
        statGroundedRate.textContent = `${groundingRate}%`;
    }

    // 2. Render document list
    if (data.documents.length === 0) {
        documentList.innerHTML = `<div style="font-size: 0.875rem; color: var(--text-secondary); text-align: center; padding: 2rem 0;">No documents uploaded yet.</div>`;
    } else {
        documentList.innerHTML = data.documents.map(doc => `
            <div class="document-item">
                <div class="doc-info" title="${doc.filename}">${doc.filename}</div>
                <span class="subject-badge">${doc.subject}</span>
            </div>
        `).join('');
    }

    // 3. Render student tracking table
    if (data.students.length === 0) {
        studentTableBody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; color: var(--text-secondary);">No student profiles found.</td>
            </tr>
        `;
    } else {
        studentTableBody.innerHTML = data.students.map(s => {
            // Format weakness flags
            let weaknessHtml = "";
            if (s.weak_topics && s.weak_topics.length > 0) {
                weaknessHtml = s.weak_topics.map(t => `<span class="weakness-badge">${t}</span>`).join('');
            } else {
                weaknessHtml = `<span class="no-weakness"><i data-lucide="check-circle" style="width:14px;height:14px;"></i> On Track</span>`;
            }

            // Format active time
            const lastActive = s.updated_at ? formatRelativeTime(s.updated_at) : "Never";
            const topic = s.current_topic && s.current_topic !== "None" ? `<span class="topic-badge">${s.current_topic}</span>` : `<span style="color: var(--text-secondary);">Inactive</span>`;
            const question = s.last_question && s.last_question !== "None" ? s.last_question : `<span style="color: var(--text-secondary); font-style: italic;">No questions yet</span>`;

            return `
                <tr>
                    <td style="font-weight: 600; display: flex; align-items: center; gap: 0.5rem; border: none;">
                        <div class="avatar" style="width:1.75rem; height:1.75rem; font-size:0.75rem;">${s.name.charAt(0).toUpperCase()}</div>
                        ${s.name}
                    </td>
                    <td>${topic}</td>
                    <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${question}</td>
                    <td>${weaknessHtml}</td>
                    <td>${lastActive}</td>
                </tr>
            `;
        }).join('');
    }

    // 4. Render recent activity feed
    if (data.recent_chats.length === 0) {
        recentChatsFeed.innerHTML = `<div style="font-size: 0.875rem; color: var(--text-secondary); text-align: center; padding: 2rem 0;">No student interactions logged yet.</div>`;
    } else {
        recentChatsFeed.innerHTML = data.recent_chats.map(chat => {
            let groundingBadge = "";
            if (chat.grounded !== undefined && chat.grounded !== null) {
                if (chat.grounded === 1 || chat.grounded === true) {
                    groundingBadge = `<span class="chat-card-grounding grounded" title="${escapeHtml(chat.grounding_rationale || 'Verified grounded')}"><i data-lucide="shield-check" style="width:10px;height:10px;display:inline-block;vertical-align:middle;margin-right:2px;"></i> Grounded</span>`;
                } else {
                    groundingBadge = `<span class="chat-card-grounding general-knowledge" title="${escapeHtml(chat.grounding_rationale || 'Not in documents')}"><i data-lucide="info" style="width:10px;height:10px;display:inline-block;vertical-align:middle;margin-right:2px;"></i> General</span>`;
                }
            }
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

            return `
                <div class="chat-card">
                    <div class="chat-card-header">
                        <div>
                            <span class="chat-card-student">${chat.student_name}</span>
                            ${groundingBadge}
                        </div>
                        <span>${formatRelativeTime(chat.timestamp)}</span>
                    </div>
                    <div class="chat-card-q"><strong>Q:</strong> ${chat.question}</div>
                    <div class="chat-card-a"><strong>A:</strong> ${formatMarkdown(chat.response)}</div>
                </div>
            `;
        }).join('');
    }

    // Helper for basic string escaping in html attributes
    function escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Update icons for dynamic content
    lucide.createIcons();
}

// Relative time formatter helper
function formatRelativeTime(dbTimeStr) {
    let cleanTimeStr = dbTimeStr.replace(" ", "T");
    if (!cleanTimeStr.includes("Z") && !cleanTimeStr.includes("+")) {
        cleanTimeStr += "Z";
    }
    
    const dbDate = new Date(cleanTimeStr);
    const now = new Date();
    const diffMs = now - dbDate;
    const diffSec = Math.floor(diffMs / 1000);
    
    if (diffSec < 5) return "Just now";
    if (diffSec < 60) return `${diffSec}s ago`;
    
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour}h ago`;
    
    return dbDate.toLocaleDateString();
}

// File Upload Handlers
uploadZone.addEventListener("click", () => fileInput.click());

// Drag-and-drop support
uploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadZone.classList.add("dragover");
});

uploadZone.addEventListener("dragleave", () => {
    uploadZone.classList.remove("dragover");
});

uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    
    if (e.dataTransfer.files.length > 0) {
        handleFileUpload(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
        handleFileUpload(fileInput.files[0]);
    }
});

async function handleFileUpload(file) {
    let subject = uploadSubjectSelect.value;
    if (subject === "custom") {
        subject = uploadSubjectCustom.value.trim();
    }
    
    if (!subject) {
        subject = "General";
    }
    
    const formData = new FormData();
    formData.append("file", file);
    formData.append("subject", subject);
    
    uploadStatus.style.color = "var(--text-secondary)";
    uploadStatus.innerHTML = `<span style="display:inline-block;animation:spin 1s infinite linear;margin-right:5px;"><i data-lucide="loader" style="width:12px;height:12px;"></i></span> Ingesting and embedding file...`;
    lucide.createIcons();
    
    try {
        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Failed to upload file");
        }
        
        const data = await response.json();
        
        uploadStatus.style.color = "var(--accent-emerald)";
        uploadStatus.innerHTML = `<i data-lucide="check" style="width:14px;height:14px;display:inline-block;vertical-align:middle;margin-right:3px;"></i> Ingested successfully (${data.chunks_created} pages)`;
        
        uploadSubjectCustom.value = "";
        uploadSubjectSelect.value = "General";
        customSubjectGroup.style.display = "none";
        fileInput.value = "";
        
        // Refresh subjects and dashboard immediately
        await refreshSubjectDropdown();
        await fetchDashboardData();
    } catch (err) {
        console.error("Upload error:", err);
        uploadStatus.style.color = "var(--accent-red)";
        uploadStatus.innerHTML = `<i data-lucide="alert-triangle" style="width:14px;height:14px;display:inline-block;vertical-align:middle;margin-right:3px;"></i> Error: ${err.message}`;
    }
    
    lucide.createIcons();
    setTimeout(() => {
        uploadStatus.innerHTML = "";
    }, 5000);
}

// Add spinning keyframe dynamically to head for loader
const styleSheet = document.createElement("style");
styleSheet.innerText = `
@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
`;
document.head.appendChild(styleSheet);

// Initial Load & Dynamic Polling
async function initDashboard() {
    await refreshSubjectDropdown();
    await fetchDashboardData();
}

initDashboard();
setInterval(fetchDashboardData, 4000); // Poll dashboard data every 4 seconds
