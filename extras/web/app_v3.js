document.addEventListener("DOMContentLoaded", () => {
    console.log("🚀 Anti-Agent Web V3: Cargando...");
    const chatBox = document.getElementById("chat-box");
    const userInput = document.getElementById("user-input");
    const sendBtn = document.getElementById("send-btn");
    const statusIndicator = document.getElementById("status-indicator");
    const agentNameDisplay = document.getElementById("agent-name-display");
    const fileList = document.getElementById("file-list");
    const engramsCount = document.getElementById("engrams-count");
    const imageInput = document.getElementById("image-input");
    const uploadBtn = document.getElementById("upload-btn");
    const imagePreviewContainer = document.getElementById("image-preview-container");
    const imagePreview = document.getElementById("image-preview");
    const removeImgBtn = document.getElementById("remove-img-btn");
    const lecturaList = document.getElementById("lectura-list");
    const lecturaDropZone = document.getElementById("lectura-drop-zone");
    const lecturaFileInput = document.getElementById("lectura-file-input");
    const mentionSuggestions = document.getElementById("mention-suggestions");

    let allFiles = []; // Combined list of workspace and lectura files

    let currentBase64Image = null;
    let reasonerMode = false;

    // Handle Image Upload
    uploadBtn.addEventListener("click", () => imageInput.click());
    
    imageInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
                currentBase64Image = event.target.result;
                imagePreview.src = currentBase64Image;
                imagePreviewContainer.classList.remove("hidden");
            };
            reader.readAsDataURL(file);
        }
    });

    removeImgBtn.addEventListener("click", () => {
        currentBase64Image = null;
        imagePreview.src = "";
        imagePreviewContainer.classList.add("hidden");
        imageInput.value = "";
    });

    // Fetch initial status
    async function updateStatus() {
        try {
            const res = await fetch("/api/status?t=" + Date.now());
            const data = await res.json();
            
            agentNameDisplay.textContent = data.agent_name;
            
            if (data.connected) {
                statusIndicator.textContent = `Conectado: ${data.loaded_model}`;
                statusIndicator.className = "status online";
            } else {
                statusIndicator.textContent = "LM Studio Offline";
                statusIndicator.className = "status offline";
            }
            
            engramsCount.textContent = data.engrams_count;
            reasonerMode = data.reasoner_mode;
            
            // Actualizar indicador de Reasoner en la UI
            const reasonerBadge = document.getElementById("reasoner-badge");
            if (reasonerBadge) {
                reasonerBadge.className = reasonerMode ? "badge reasoner-on" : "badge reasoner-off";
                reasonerBadge.textContent = reasonerMode ? "Reasoner: ON" : "Reasoner: OFF";
            }

        } catch (e) {
            statusIndicator.textContent = "Servidor Local Caído";
            statusIndicator.className = "status offline";
        }
    }

    // --- Lectura Section ---
    async function updateLectura() {
        try {
            const res = await fetch("/api/lectura?t=" + Date.now());
            const data = await res.json();
            lecturaList.innerHTML = "";
            if (!data.files || data.files.length === 0) {
                lecturaList.innerHTML = '<li style="color:var(--text-secondary);font-size:12px;padding:8px">Sin documentos</li>';
            } else {
                data.files.forEach(f => {
                    if (!allFiles.includes(f)) allFiles.push(f);
                    const li = document.createElement("li");
                    li.className = "file-item lectura-item";
                    li.innerHTML = '<span>📖 ' + f + '</span>';
                    li.title = 'Clic para mencionar con @' + f + ' en el chat';
                    li.addEventListener("click", () => {
                        const current = userInput.value;
                        const mention = "@" + f + " ";
                        if (current.length > 0 && !current.endsWith(" ")) {
                            userInput.value = current + " " + mention;
                        } else {
                            userInput.value = current + mention;
                        }
                        userInput.focus();
                    });
                    lecturaList.appendChild(li);
                });
            }
        } catch (e) {
            console.warn("Error cargando lectura:", e);
        }
    }

    async function uploadToLectura(file) {
        const text = await file.text();
        await fetch("/api/upload-lectura", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({filename: file.name, content: text})
        });
        await updateLectura();
        addMessage("**Lectura:** `" + file.name + "` cargado. Mencionalo con @" + file.name + " en el chat para usarlo como referencia exclusiva.", "system");
    }

    lecturaDropZone.addEventListener("click", () => lecturaFileInput.click());
    lecturaFileInput.addEventListener("change", (e) => {
        if (e.target.files[0]) uploadToLectura(e.target.files[0]);
    });
    lecturaDropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        lecturaDropZone.classList.add("drag-over");
    });
    lecturaDropZone.addEventListener("dragleave", () => lecturaDropZone.classList.remove("drag-over"));
    lecturaDropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        lecturaDropZone.classList.remove("drag-over");
        const file = e.dataTransfer.files[0];
        if (file) uploadToLectura(file);
    });

    async function updateFiles() {
        try {
            const res = await fetch("/api/files?t=" + Date.now());
            const data = await res.json();
            fileList.innerHTML = "";
            if (data.files.length === 0) {
                fileList.innerHTML = "<li>No hay archivos</li>";
            } else {
                data.files.forEach(f => {
                    if (!allFiles.includes(f)) allFiles.push(f);
                    const li = document.createElement("li");
                    li.className = "file-item";
                    li.innerHTML = `<span>📄 ${f}</span>`;
                    li.addEventListener("click", async () => {
                        const contentRes = await fetch(`/api/file/${f}`);
                        const contentData = await contentRes.json();
                        addMessage(`**Vista Previa: ${f}**\n\n${contentData.content}`, "system");
                    });
                    fileList.appendChild(li);
                });
            }
        } catch (e) {
            fileList.innerHTML = "<li>Error al cargar</li>";
        }
    }

    function addMessage(text, sender, steps = [], sources = {}) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${sender}`;
        
        // Render Reasoning Steps if any
        if (steps && steps.length > 0) {
            const stepsContainer = document.createElement("div");
            stepsContainer.className = "agent-steps";
            
            steps.forEach(s => {
                const stepCard = document.createElement("div");
                stepCard.className = "step-card";
                
                let icon = "🔍";
                if (s.tool === "FETCH") icon = "📄";
                if (s.tool === "RUN") icon = "💻";
                if (s.tool === "WRITE") icon = "💾";
                if (s.tool === "ANALYZE") icon = "🔬";
                if (s.tool === "RESEARCH") icon = "🚀";

                stepCard.innerHTML = `
                    <div class="step-icon">${icon}</div>
                    <div class="step-info">
                        <div class="step-label">${s.tool}</div>
                        <div class="step-query">${s.query}</div>
                    </div>
                `;
                stepsContainer.appendChild(stepCard);
            });
            msgDiv.appendChild(stepsContainer);
        }

        // Detect Mermaid blocks
        if (typeof text === 'string' && text.includes("```mermaid")) {
            const parts = text.split("```mermaid");
            const intro = document.createElement("div");
            intro.innerHTML = DOMPurify.sanitize(marked.parse(parts[0]));
            msgDiv.appendChild(intro);
            
            const diagramCode = parts[1].split("```")[0];
            const mermaidDiv = document.createElement("div");
            mermaidDiv.className = "mermaid";
            mermaidDiv.textContent = diagramCode.trim();
            msgDiv.appendChild(mermaidDiv);
            
            const remainingText = parts[1].split("```")[1];
            if (remainingText) {
                const span = document.createElement("div");
                span.innerHTML = DOMPurify.sanitize(marked.parse(remainingText));
                msgDiv.appendChild(span);
            }
        } else {
            const contentDiv = document.createElement("div");
            contentDiv.className = "message-text";
            
            // 1. Parse Markdown to HTML
            let htmlContent = marked.parse(String(text));
            
            // 2. Format citations like [1], [2], [3]
            htmlContent = htmlContent.replace(/\[(\d+)\]/g, (match, num) => {
                const url = sources[num] || "#";
                return `<a href="${url}" target="_blank" class="citation" title="${url}">[${num}]</a>`;
            });
            
            // 3. Sanitize final HTML
            const safeHtml = DOMPurify.sanitize(htmlContent);
            contentDiv.innerHTML = safeHtml;
            msgDiv.appendChild(contentDiv);
        }

        chatBox.appendChild(msgDiv);
        
        // Render Mermaid if exists
        if (typeof text === 'string' && text.includes("```mermaid")) {
            mermaid.init(undefined, msgDiv.querySelectorAll(".mermaid"));
        }

        chatBox.scrollTop = chatBox.scrollHeight;
        return msgDiv;
    }

    async function pollJob(jobId, thinkingMsg) {
        try {
            const res = await fetch(`/api/job/${jobId}`);
            const data = await res.json();

            if (data.status === "completed") {
                // Remove thinking message
                if (thinkingMsg.parentNode) chatBox.removeChild(thinkingMsg);
                
                // Add real response with steps and sources
                addMessage(data.result.response, "agent", data.result.steps, data.result.sources);
                
                // Update UI
                updateStatus();
                updateFiles();
            } else if (data.status === "failed") {
                if (thinkingMsg.parentNode) chatBox.removeChild(thinkingMsg);
                addMessage(`Error en el agente: ${data.error}`, "system");
            } else {
                // Still processing, poll again in 2 seconds
                setTimeout(() => pollJob(jobId, thinkingMsg), 2000);
            }
        } catch (e) {
            console.error("Polling error:", e);
            setTimeout(() => pollJob(jobId, thinkingMsg), 5000); // Retry later
        }
    }

    // --- Autocomplete ---
    userInput.addEventListener("input", () => {
        const value = userInput.value;
        const lastAtIndex = value.lastIndexOf("@");
        
        // Show suggestions only if @ is the last word-start
        if (lastAtIndex !== -1 && (lastAtIndex === 0 || value[lastAtIndex - 1] === " ")) {
            const query = value.substring(lastAtIndex + 1).toLowerCase();
            const matches = allFiles.filter(f => f.toLowerCase().includes(query));
            
            if (matches.length > 0) {
                mentionSuggestions.innerHTML = "";
                matches.forEach(m => {
                    const div = document.createElement("div");
                    div.className = "suggestion-item";
                    div.innerHTML = `📖 <span>@${m}</span>`;
                    div.addEventListener("click", () => {
                        const before = value.substring(0, lastAtIndex);
                        const after = value.substring(userInput.selectionStart);
                        userInput.value = before + "@" + m + " " + after;
                        mentionSuggestions.classList.add("hidden");
                        userInput.focus();
                    });
                    mentionSuggestions.appendChild(div);
                });
                mentionSuggestions.classList.remove("hidden");
            } else {
                mentionSuggestions.classList.add("hidden");
            }
        } else {
            mentionSuggestions.classList.add("hidden");
        }
    });

    // Hide suggestions when clicking outside
    document.addEventListener("click", (e) => {
        if (!mentionSuggestions.contains(e.target) && e.target !== userInput) {
            mentionSuggestions.classList.add("hidden");
        }
    });

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text && !currentBase64Image) return;

        if (text === "/r") {
            try {
                const res = await fetch("/api/refresh");
                const data = await res.json();
                addMessage("Sistema refrescado con éxito.", "system");
                updateStatus();
                updateFiles();
                updateLectura();
                location.reload(true); // Recarga forzada para limpiar TODO
                return;
            } catch (e) {
                addMessage("Error al refrescar el sistema.", "system");
                return;
            }
        }

        addMessage(text || "Analiza esta imagen:", "user");
        userInput.value = "";
        
        const payload = { message: text };
        if (currentBase64Image) {
            payload.image = currentBase64Image;
            removeImgBtn.click(); // Limpiar después de enviar
        }

        const thinkingMsg = document.createElement("div");
        thinkingMsg.className = "message agent thinking";
        thinkingMsg.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
        chatBox.appendChild(thinkingMsg);
        chatBox.scrollTop = chatBox.scrollHeight;

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            if (data.job_id) {
                // Iniciar polling
                pollJob(data.job_id, thinkingMsg);
            } else {
                throw new Error("No se recibió Ticket de Trabajo.");
            }
            
        } catch (e) {
            if (thinkingMsg.parentNode) chatBox.removeChild(thinkingMsg);
            addMessage("Error de conexión con el servidor.", "system");
        }
    }

    sendBtn.addEventListener("click", sendMessage);
    userInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Init
    updateStatus();
    updateFiles();
    updateLectura();
    setInterval(updateStatus, 60000);
    setInterval(updateLectura, 120000); // Cada 2 minutos
});
