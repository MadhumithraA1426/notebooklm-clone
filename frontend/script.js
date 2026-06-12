// Client State Variables
let sources = [];
let selectedSourceIds = new Set();
let activeTab = 'chat';
let chatHistory = [];
let generatedSummary = '';
let generatedQuiz = [];
let currentQuizIndex = 0;
let quizScore = 0;
let selectedOptionIndex = null;
let generatedMindmap = '';
let generatedAudio = null;

// API URL (same origin since app.py serves both backend and frontend)
const API_BASE = "";

// Initialize
document.addEventListener("DOMContentLoaded", () => {
    loadSources();
    setupDragAndDrop();
    setupFileInput();
    setupTextareaAutoHeight();
});

// -------------------------------------------------------------
// UI Utilities
// -------------------------------------------------------------
function showLoader(message) {
    document.getElementById("loaderMessage").innerText = message;
    document.getElementById("loaderOverlay").style.display = "flex";
}

function hideLoader() {
    document.getElementById("loaderOverlay").style.display = "none";
}

function showToast(message, isError = false) {
    // Basic browser alert fallback or custom UI
    alert((isError ? "Error: " : "") + message);
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function setupTextareaAutoHeight() {
    const textarea = document.getElementById("chatInput");
    textarea.addEventListener("input", function() {
        this.style.height = "auto";
        this.style.height = (this.scrollHeight) + "px";
    });
}

// -------------------------------------------------------------
// Drag & Drop / Upload Handlers
// -------------------------------------------------------------
function setupDragAndDrop() {
    const dropZone = document.getElementById("dropZone");
    
    dropZone.addEventListener("click", () => {
        document.getElementById("fileInput").click();
    });

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadFiles(files);
        }
    });
}

function setupFileInput() {
    const fileInput = document.getElementById("fileInput");
    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            uploadFiles(fileInput.files);
        }
    });
}

async function uploadFiles(fileList) {
    showLoader("Uploading files and generating vector embeddings...");
    
    for (let i = 0; i < fileList.length; i++) {
        const file = fileList[i];
        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch(`${API_BASE}/api/upload`, {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Upload failed");
            }
            
            const data = await response.json();
            // Automatically select uploaded source
            selectedSourceIds.add(data.id);
        } catch (error) {
            console.error("Upload error:", error);
            showToast(`Failed to upload ${file.name}: ${error.message}`, true);
        }
    }
    
    hideLoader();
    loadSources();
}

// -------------------------------------------------------------
// Sources List Handlers
// -------------------------------------------------------------
async function loadSources() {
    try {
        const response = await fetch(`${API_BASE}/api/sources`);
        if (!response.ok) throw new Error("Failed to load sources");
        sources = await response.json();
        renderSources();
        updateChatSourcesIndicator();
    } catch (error) {
        console.error(error);
        showToast("Error loading sources list", true);
    }
}

function renderSources() {
    const listContainer = document.getElementById("sourcesList");
    const countSpan = document.getElementById("sourceCount");
    const actionsDiv = document.getElementById("sourceActions");
    
    countSpan.innerText = sources.length;

    if (sources.length === 0) {
        listContainer.innerHTML = `
            <div class="empty-sources">
                <i class="fa-regular fa-file-lines empty-icon"></i>
                <p>No documents uploaded yet.</p>
            </div>
        `;
        actionsDiv.style.display = "none";
        return;
    }

    actionsDiv.style.display = "block";
    listContainer.innerHTML = "";

    sources.forEach(source => {
        const isSelected = selectedSourceIds.has(source.id);
        const card = document.createElement("div");
        card.className = `source-card ${isSelected ? 'selected' : ''}`;
        
        let iconClass = "fa-file-lines";
        if (source.file_type === "pdf") iconClass = "fa-file-pdf";
        else if (source.file_type === "docx") iconClass = "fa-file-word";
        else if (source.file_type === "md") iconClass = "fa-file-code";

        card.innerHTML = `
            <input type="checkbox" class="source-checkbox" ${isSelected ? 'checked' : ''} onchange="toggleSource('${source.id}')">
            <i class="fa-solid ${iconClass} source-icon"></i>
            <div class="source-details">
                <p class="source-name" title="${source.filename}">${source.filename}</p>
                <p class="source-meta">${formatBytes(source.size_bytes)} • ${source.chunks_count} chunks</p>
            </div>
            <button class="delete-source-btn" onclick="deleteSource('${source.id}', event)" title="Delete Document">
                <i class="fa-regular fa-trash-can"></i>
            </button>
        `;
        
        listContainer.appendChild(card);
    });
}

function toggleSource(sourceId) {
    if (selectedSourceIds.has(sourceId)) {
        selectedSourceIds.delete(sourceId);
    } else {
        selectedSourceIds.add(sourceId);
    }
    renderSources();
    updateChatSourcesIndicator();
}

function selectAllSources() {
    sources.forEach(s => selectedSourceIds.add(s.id));
    renderSources();
    updateChatSourcesIndicator();
}

function clearSourceSelection() {
    selectedSourceIds.clear();
    renderSources();
    updateChatSourcesIndicator();
}

async function deleteSource(sourceId, event) {
    event.stopPropagation(); // prevent card checkbox toggling
    if (!confirm("Are you sure you want to delete this source?")) return;
    
    showLoader("Deleting source...");
    try {
        const response = await fetch(`${API_BASE}/api/sources/${sourceId}`, {
            method: "DELETE"
        });
        if (!response.ok) throw new Error("Delete failed");
        
        selectedSourceIds.delete(sourceId);
        loadSources();
    } catch (error) {
        console.error(error);
        showToast("Failed to delete source", true);
    } finally {
        hideLoader();
    }
}

function updateChatSourcesIndicator() {
    const indicator = document.getElementById("chatSourcesIndicator");
    const sendBtn = document.getElementById("sendBtn");
    
    const count = selectedSourceIds.size;
    if (count === 0) {
        indicator.innerHTML = `<i class="fa-solid fa-circle-info"></i> <span>No sources selected. Check files in the sidebar to chat.</span>`;
        indicator.classList.remove("active");
        sendBtn.disabled = true;
    } else {
        const selectedNames = sources
            .filter(s => selectedSourceIds.has(s.id))
            .map(s => s.filename)
            .join(", ");
        indicator.innerHTML = `<i class="fa-solid fa-circle-check"></i> <span class="active">Active: ${count} selected (${selectedNames})</span>`;
        indicator.classList.add("active");
        sendBtn.disabled = false;
    }
}

// -------------------------------------------------------------
// Tab Switching
// -------------------------------------------------------------
function switchTab(tabId) {
    activeTab = tabId;
    
    // Update active tab button style
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.classList.remove("active");
        if (btn.innerText.toLowerCase().includes(tabId)) {
            btn.classList.add("active");
        } else if (tabId === 'audio' && btn.innerText.toLowerCase().includes('audio')) {
            btn.classList.add("active");
        }
    });

    // Show selected panel
    document.querySelectorAll(".tab-pane").forEach(pane => {
        pane.classList.remove("active");
    });
    document.getElementById(`tab-${tabId}`).classList.add("active");
}

// -------------------------------------------------------------
// Tab 1: Chat Logic
// -------------------------------------------------------------
function handleChatKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendChatMessage();
    }
}

function useSuggestion(text) {
    document.getElementById("chatInput").value = text;
    sendChatMessage();
}

async function sendChatMessage() {
    const input = document.getElementById("chatInput");
    const query = input.value.trim();
    if (!query || selectedSourceIds.size === 0) return;

    // Add user message to UI and history
    appendChatMessage("user", query);
    chatHistory.push({ role: "user", content: query });
    
    input.value = "";
    input.style.height = "auto";

    // Disable input while generating
    input.disabled = true;
    const sendBtn = document.getElementById("sendBtn");
    sendBtn.disabled = true;

    // Show temporary typing indicator
    const typingIndicator = appendTypingIndicator();

    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                messages: chatHistory,
                selected_source_ids: Array.from(selectedSourceIds)
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "RAG query failed");
        }

        const data = await response.json();
        typingIndicator.remove();
        
        appendChatMessage("assistant", data.answer);
        chatHistory.push({ role: "assistant", content: data.answer });
    } catch (error) {
        console.error(error);
        typingIndicator.remove();
        appendChatMessage("assistant", `An error occurred: ${error.message}. Please try again.`);
    } finally {
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
    }
}

function appendChatMessage(role, content) {
    const chatMessages = document.getElementById("chatMessages");
    
    // Remove welcome card if this is the first message
    const welcome = chatMessages.querySelector(".assistant-welcome");
    if (welcome) welcome.remove();

    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.innerHTML = role === "user" ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';

    const contentWrapper = document.createElement("div");
    contentWrapper.className = "msg-content-wrapper";

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.innerHTML = parseMarkdownSimple(content);

    contentWrapper.appendChild(bubble);
    
    // Parse citations inside the message
    const citations = extractCitations(content);
    if (citations.length > 0) {
        const citationsDiv = document.createElement("div");
        citationsDiv.className = "citations-wrapper";
        citations.forEach(cit => {
            const pill = document.createElement("span");
            pill.className = "citation-pill";
            pill.innerText = `Source: ${cit}`;
            citationsDiv.appendChild(pill);
        });
        contentWrapper.appendChild(citationsDiv);
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentWrapper);
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendTypingIndicator() {
    const chatMessages = document.getElementById("chatMessages");
    const indicator = document.createElement("div");
    indicator.className = "message assistant typing-indicator-msg";
    indicator.innerHTML = `
        <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="msg-content-wrapper">
            <div class="msg-bubble" style="display: flex; align-items: center; gap: 4px; padding: 12px 20px;">
                <span class="status-indicator online" style="width: 6px; height: 6px; animation: pulse 1s infinite alternate;"></span>
                <span>Generating response...</span>
            </div>
        </div>
    `;
    chatMessages.appendChild(indicator);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return indicator;
}

function parseMarkdownSimple(text) {
    // Render basic HTML tags safely
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Replace bold **text**
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    
    // Replace italics *text*
    html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");

    // Replace linebreaks
    html = html.replace(/\n/g, "<br>");

    // Replace inline code `code`
    html = html.replace(/`(.*?)`/g, "<code>$1</code>");

    // Replace markdown lists
    html = html.replace(/(?:^|<br>)-\s+(.*?)(?=<br>|$)/g, "<li>$1</li>");
    // Wrap <li> inside <ul>
    if (html.includes("<li>")) {
        // A simple wrap for lists
        html = html.replace(/(<li>.*?<\/li>)/g, "<ul>$1</ul>");
        // merge adjacent <ul>
        html = html.replace(/<\/ul><ul>/g, "");
    }

    return html;
}

function extractCitations(text) {
    // Find references like [Source: document.pdf] or [document.pdf]
    const citations = [];
    const pattern = /\[Source:\s*(.*?)\]/g;
    let match;
    while ((match = pattern.exec(text)) !== null) {
        citations.push(match[1]);
    }
    return citations;
}

// -------------------------------------------------------------
// Tab 2: Summary Logic
// -------------------------------------------------------------
async function generateSummaryAction() {
    if (selectedSourceIds.size === 0) {
        showToast("Please select at least one document first.", true);
        return;
    }
    
    showLoader("Analyzing document contents and compiling structured summary...");
    try {
        const response = await fetch(`${API_BASE}/api/summary`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                selected_source_ids: Array.from(selectedSourceIds)
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Summary generation failed");
        }

        const data = await response.json();
        generatedSummary = data.summary;
        
        renderSummary();
    } catch (error) {
        console.error(error);
        showToast(error.message, true);
    } finally {
        hideLoader();
    }
}

function renderSummary() {
    document.getElementById("summaryLanding").style.display = "none";
    
    const contentDiv = document.getElementById("summaryContent");
    const actionsDiv = document.getElementById("summaryActions");
    
    contentDiv.style.display = "block";
    actionsDiv.style.display = "block";
    
    contentDiv.innerHTML = parseMarkdownFull(generatedSummary);
}

function parseMarkdownFull(md) {
    // A more advanced markdown parser that handles tables and lists cleanly
    let html = md;
    
    // Header 1
    html = html.replace(/^#\s+(.*?)$/gm, "<h1>$1</h1>");
    // Header 2
    html = html.replace(/^##\s+(.*?)$/gm, "<h2>$1</h2>");
    // Header 3
    html = html.replace(/^###\s+(.*?)$/gm, "<h3>$1</h3>");
    
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    
    // Tables
    const lines = html.split("\n");
    let inTable = false;
    let tableHTML = "";
    
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        if (line.startsWith("|") && i + 1 < lines.length && lines[i+1].trim().startsWith("|") && lines[i+1].includes("-")) {
            inTable = true;
            tableHTML = "<table><thead>";
            // Header row
            const cols = line.split("|").slice(1, -1);
            tableHTML += "<tr>" + cols.map(c => `<th>${c.trim()}</th>`).join("") + "</tr></thead><tbody>";
            i += 1; // skip separator line
            continue;
        }
        
        if (inTable) {
            if (line.startsWith("|")) {
                const cols = line.split("|").slice(1, -1);
                tableHTML += "<tr>" + cols.map(c => `<td>${c.trim()}</td>`).join("") + "</tr>";
            } else {
                tableHTML += "</tbody></table>";
                lines[i] = tableHTML + "\n" + lines[i];
                inTable = false;
            }
        }
    }
    
    html = lines.join("\n");
    
    // List item lines
    html = html.replace(/^\-\s+(.*?)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*?<\/li>)/gs, "<ul>$1</ul>");
    html = html.replace(/<\/ul>\s*<ul>/g, "");
    
    // Numbered List items
    html = html.replace(/^\d+\.\s+(.*?)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*?<\/li>)/gs, "<ol>$1</ol>");
    html = html.replace(/<\/ol>\s*<ol>/g, "");
    
    // Paragraph spaces
    html = html.replace(/^(?!\s*<h|<ul>|<li>|<ol>|<table>|<tr>|<td>|<th>|<\/table>|<\/tbody>)(.*?)$/gm, "<p>$1</p>");
    
    // Clean up empty paragraphs
    html = html.replace(/<p><\/p>/g, "");
    html = html.replace(/<p>\s*<\/p>/g, "");
    
    return html;
}

// -------------------------------------------------------------
// Tab 3: Quiz Logic
// -------------------------------------------------------------
async function generateQuizAction() {
    if (selectedSourceIds.size === 0) {
        showToast("Please select at least one document first.", true);
        return;
    }
    
    showLoader("Analyzing context and creating personalized quiz...");
    try {
        const response = await fetch(`${API_BASE}/api/quiz`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                selected_source_ids: Array.from(selectedSourceIds)
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Quiz generation failed");
        }

        const data = await response.json();
        generatedQuiz = data.quiz;
        
        // Setup Quiz States
        currentQuizIndex = 0;
        quizScore = 0;
        selectedOptionIndex = null;
        
        startQuizPlay();
    } catch (error) {
        console.error(error);
        showToast(error.message, true);
    } finally {
        hideLoader();
    }
}

function startQuizPlay() {
    document.getElementById("quizLanding").style.display = "none";
    document.getElementById("quizFinishScreen").style.display = "none";
    document.getElementById("quizPlaySpace").style.display = "flex";
    
    renderQuizQuestion();
}

function renderQuizQuestion() {
    const question = generatedQuiz[currentQuizIndex];
    
    document.getElementById("currentQuestionNum").innerText = currentQuizIndex + 1;
    document.getElementById("totalQuestionsNum").innerText = generatedQuiz.length;
    document.getElementById("quizScore").innerText = quizScore;
    
    document.getElementById("quizQuestionText").innerText = question.question;
    
    const optionsContainer = document.getElementById("quizOptionsList");
    optionsContainer.innerHTML = "";
    
    const explanationBox = document.getElementById("quizExplanationBox");
    explanationBox.style.display = "none";
    
    // Reset next button
    const nextBtn = document.getElementById("quizNextBtn");
    nextBtn.innerText = currentQuizIndex === generatedQuiz.length - 1 ? "Finish Quiz" : "Next Question";
    
    selectedOptionIndex = null;
    
    question.options.forEach((opt, idx) => {
        const btn = document.createElement("button");
        btn.className = "quiz-option-btn";
        btn.innerText = opt;
        btn.onclick = () => selectQuizOption(idx);
        optionsContainer.appendChild(btn);
    });
    
    // Disable previous if first question
    document.getElementById("quizPrevBtn").disabled = currentQuizIndex === 0;
}

function selectQuizOption(optionIndex) {
    if (selectedOptionIndex !== null) return; // allow only one submission
    
    selectedOptionIndex = optionIndex;
    const question = generatedQuiz[currentQuizIndex];
    const optionsList = document.getElementById("quizOptionsList").children;
    const selectedText = question.options[optionIndex];
    const isCorrect = selectedText === question.answer;
    
    // Style options
    for (let i = 0; i < optionsList.length; i++) {
        const btn = optionsList[i];
        const text = btn.innerText;
        btn.disabled = true; // lock options
        
        if (text === question.answer) {
            btn.classList.add("correct");
        } else if (i === optionIndex) {
            btn.classList.add("incorrect");
        }
    }
    
    if (isCorrect) {
        quizScore += 1;
        document.getElementById("quizScore").innerText = quizScore;
    }
    
    // Render explanation
    const explanationText = document.getElementById("quizExplanationText");
    const explanationBox = document.getElementById("quizExplanationBox");
    
    explanationText.innerText = question.explanation;
    explanationBox.style.display = "block";
}

function prevQuestion() {
    if (currentQuizIndex > 0) {
        currentQuizIndex -= 1;
        renderQuizQuestion();
    }
}

function nextQuestion() {
    if (selectedOptionIndex === null) {
        showToast("Please choose an answer before moving forward.", true);
        return;
    }
    
    if (currentQuizIndex < generatedQuiz.length - 1) {
        currentQuizIndex += 1;
        renderQuizQuestion();
    } else {
        finishQuiz();
    }
}

function finishQuiz() {
    document.getElementById("quizPlaySpace").style.display = "none";
    
    const finishScreen = document.getElementById("quizFinishScreen");
    finishScreen.style.display = "block";
    
    document.getElementById("finalScore").innerText = quizScore;
    document.getElementById("finalTotal").innerText = generatedQuiz.length;
    
    const percentage = Math.round((quizScore / generatedQuiz.length) * 100);
    document.getElementById("scorePercentage").innerText = `${percentage}%`;
}

// -------------------------------------------------------------
// Tab 4: Mindmap Logic
// -------------------------------------------------------------
async function generateMindmapAction() {
    if (selectedSourceIds.size === 0) {
        showToast("Please select at least one document first.", true);
        return;
    }
    
    showLoader("Extracting core concept map and drawing visual tree...");
    try {
        const response = await fetch(`${API_BASE}/api/mindmap`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                selected_source_ids: Array.from(selectedSourceIds)
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Mind map generation failed");
        }

        const data = await response.json();
        generatedMindmap = data.mindmap;
        
        renderMindmap();
    } catch (error) {
        console.error(error);
        showToast(error.message, true);
    } finally {
        hideLoader();
    }
}

async function renderMindmap() {
    document.getElementById("mindmapLanding").style.display = "none";
    document.getElementById("mindmapActions").style.display = "block";
    
    const viewerDiv = document.getElementById("mindmapViewer");
    viewerDiv.style.display = "flex";
    
    const chartContainer = document.getElementById("mermaidContainer");
    chartContainer.removeAttribute("data-processed");
    chartContainer.innerHTML = generatedMindmap;
    
    try {
        // Compile using Mermaid
        await mermaid.run({
            nodes: [chartContainer]
        });
    } catch (err) {
        console.error("Mermaid compile failed:", err);
        // Fallback: print syntax
        chartContainer.innerHTML = `<pre style="color: #ffffff; text-align: left; overflow: auto; max-width: 100%;">${generatedMindmap}</pre>`;
    }
}

function downloadMindmapText() {
    navigator.clipboard.writeText(generatedMindmap);
    showToast("Mermaid diagram text copied to clipboard!");
}

// -------------------------------------------------------------
// Tab 5: Audio Overview Logic
// -------------------------------------------------------------
async function generateAudioAction() {
    if (selectedSourceIds.size === 0) {
        showToast("Please select at least one document first.", true);
        return;
    }
    
    showLoader("Writing dynamic script and synthesizing podcast audio (this may take a minute)...");
    try {
        const response = await fetch(`${API_BASE}/api/audio-overview`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                selected_source_ids: Array.from(selectedSourceIds)
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Audio overview failed");
        }

        generatedAudio = await response.json();
        setupAudioPlayer();
    } catch (error) {
        console.error(error);
        showToast(error.message, true);
    } finally {
        hideLoader();
    }
}

function setupAudioPlayer() {
    document.getElementById("audioLanding").style.display = "none";
    document.getElementById("audioWorkspace").style.display = "flex";
    
    const audio = document.getElementById("podcastAudio");
    audio.src = `${API_BASE}${generatedAudio.audio_url}`;
    
    // Download link setup
    const dlLink = document.getElementById("audioDownloadLink");
    dlLink.href = `${API_BASE}${generatedAudio.audio_url}`;
    
    // Seeker reset
    const seekBar = document.getElementById("audioSeekBar");
    seekBar.value = 0;
    
    // Render transcript
    const transcriptBox = document.getElementById("transcriptBox");
    transcriptBox.innerHTML = "";
    
    generatedAudio.script.forEach((turn, idx) => {
        const line = document.createElement("div");
        line.className = `transcript-line ${turn.speaker.toLowerCase()}`;
        line.id = `transcript-line-${idx}`;
        line.innerHTML = `
            <div class="transcript-speaker">${turn.speaker}</div>
            <div class="transcript-text">${turn.text}</div>
        `;
        transcriptBox.appendChild(line);
    });

    // Wire player event listeners
    audio.onloadedmetadata = () => {
        document.getElementById("durationTime").innerText = formatAudioTime(audio.duration);
    };

    audio.ontimeupdate = () => {
        // Update seeker
        if (audio.duration) {
            seekBar.value = (audio.currentTime / audio.duration) * 100;
        }
        document.getElementById("currentTime").innerText = formatAudioTime(audio.currentTime);
        
        // Highlight transcript turn based on progression
        if (audio.duration) {
            const activeIndex = Math.min(
                Math.floor((audio.currentTime / audio.duration) * generatedAudio.script.length),
                generatedAudio.script.length - 1
            );
            highlightTranscriptLine(activeIndex);
        }
    };
    
    audio.onended = () => {
        document.getElementById("playPauseBtn").innerHTML = '<i class="fa-solid fa-play"></i>';
    };
}

function toggleAudio() {
    const audio = document.getElementById("podcastAudio");
    const playPauseBtn = document.getElementById("playPauseBtn");
    
    if (audio.paused) {
        audio.play();
        playPauseBtn.innerHTML = '<i class="fa-solid fa-pause"></i>';
    } else {
        audio.pause();
        playPauseBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
    }
}

function adjustAudioTime(seconds) {
    const audio = document.getElementById("podcastAudio");
    audio.currentTime = Math.max(0, Math.min(audio.duration, audio.currentTime + seconds));
}

function seekAudio() {
    const audio = document.getElementById("podcastAudio");
    const seekBar = document.getElementById("audioSeekBar");
    if (audio.duration) {
        audio.currentTime = (seekBar.value / 100) * audio.duration;
    }
}

function changePlaybackSpeed() {
    const audio = document.getElementById("podcastAudio");
    const speed = document.getElementById("speedSelect").value;
    audio.playbackRate = parseFloat(speed);
}

function highlightTranscriptLine(index) {
    // Un-highlight previous
    document.querySelectorAll(".transcript-line").forEach(line => line.classList.remove("active"));
    
    const activeLine = document.getElementById(`transcript-line-${index}`);
    if (activeLine) {
        activeLine.classList.add("active");
        
        // Auto scroll transcript box to keep speaker in view
        const box = document.getElementById("transcriptBox");
        const boxHeight = box.clientHeight;
        const lineTop = activeLine.offsetTop;
        const lineSelectionHeight = activeLine.clientHeight;
        
        box.scrollTop = lineTop - (boxHeight / 2) + (lineSelectionHeight / 2);
    }
}

function formatAudioTime(secs) {
    const minutes = Math.floor(secs / 60);
    const seconds = Math.floor(secs % 60);
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// -------------------------------------------------------------
// Document Exports (PDF downloads)
// -------------------------------------------------------------
async function downloadDocument(type) {
    let title = "";
    let content = "";
    
    if (type === "summary") {
        title = "Document Summary Guide";
        content = generatedSummary;
    } else if (type === "quiz") {
        title = "Study Revision Quiz";
        // Format the quiz into clean markdown for PDF generation
        content = generatedQuiz.map((q, idx) => {
            return `## Question ${idx + 1}\n\n${q.question}\n\n` +
                   q.options.map((opt, oIdx) => `- ${opt} ${opt === q.answer ? "**(Correct)**" : ""}`).join("\n") +
                   `\n\n**Explanation:** ${q.explanation}\n\n`;
        }).join("\n---\n\n");
    }
    
    if (!content) {
        showToast("No content generated to download.", true);
        return;
    }
    
    showLoader("Compiling PDF document. Please wait...");
    try {
        const response = await fetch(`${API_BASE}/api/download`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: title,
                content: content,
                type: type
            })
        });

        if (!response.ok) {
            throw new Error("PDF rendering failed");
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${title.replace(/\s+/g, '_')}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error(error);
        showToast(error.message, true);
    } finally {
        hideLoader();
    }
}