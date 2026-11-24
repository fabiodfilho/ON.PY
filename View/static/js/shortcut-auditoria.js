document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("execFormAuditoria");
    const apiTokenInput = document.getElementById("api_token");
    const subcontasInput = document.getElementById("subcontas");
    const toggleTokenBtn = document.getElementById("toggleToken");
    const btnRun = document.getElementById("btnRun");
    const btnDownloadReport = document.getElementById("btnDownloadReport");
    const btnClearLogs = document.getElementById("btnClearLogs");
    const logConsole = document.getElementById("logConsole");
    const statusBadge = document.getElementById("statusBadge");
    const progressBar = document.getElementById("progressBar");
    const progressText = document.getElementById("progressText");
    const progressTrack = progressBar?.parentElement;

    let lastReportBase64 = null;
    let lastReportFilename = "auditoria_unifacisa_multicontas.xlsx";
    let totalCourses = 0;
    let processedCourses = 0;
    let subaccountBase = 0;
    let subaccountCourses = 0;

    function resetProgress() {
        totalCourses = 0;
        processedCourses = 0;
        subaccountBase = 0;
        subaccountCourses = 0;
        progressBar.classList.remove("animate-pulse");
        progressBar.style.width = "0%";
        progressText.textContent = "Aguardando execução";
        progressTrack?.setAttribute("aria-valuenow", "0");
    }

    function updateProgress(percentage, text) {
        progressBar.classList.remove("animate-pulse");
        progressBar.style.width = `${percentage}%`;
        progressText.textContent = text;
        progressTrack?.setAttribute("aria-valuenow", String(percentage));
    }

    function setPreparingProgress() {
        progressBar.classList.add("animate-pulse");
        progressBar.style.width = "100%";
        progressText.textContent = "Preparando...";
    }

    toggleTokenBtn.addEventListener("click", () => {
        apiTokenInput.type = apiTokenInput.type === "password" ? "text" : "password";
    });

    btnClearLogs.addEventListener("click", () => {
        logConsole.innerHTML = '<p class="text-slate-500">// Console limpo.</p>';
        resetProgress();
    });

    function appendLog(message, type = "log") {
        const p = document.createElement("p");
        if (type === "error") {
            p.className = "text-rose-400 font-semibold";
        } else if (type === "success") {
            p.className = "text-sky-400 font-bold";
        } else {
            p.className = "text-emerald-400";
        }
        p.textContent = message;
        logConsole.appendChild(p);
        logConsole.scrollTop = logConsole.scrollHeight;
    }

    function setStatus(state, text) {
        const colors = {
            idle: "bg-slate-300",
            running: "bg-amber-400 animate-pulse",
            success: "bg-emerald-500",
            error: "bg-rose-500",
        };
        const textColors = {
            idle: "text-slate-400",
            running: "text-amber-600",
            success: "text-emerald-600",
            error: "text-rose-600",
        };
        statusBadge.className = `text-xs font-semibold flex items-center gap-2 ${textColors[state]}`;
        statusBadge.innerHTML = `<span class="w-2 h-2 rounded-full ${colors[state]}"></span> ${text}`;
    }

    function downloadExcel(base64Data, filename) {
        const byteCharacters = atob(base64Data);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const blob = new Blob([new Uint8Array(byteNumbers)], {
            type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        });

        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    }

    function processEvent(event) {
        if (event.type === "error") {
            appendLog(`[ERRO] ${event.message}`, "error");
            setStatus("error", "Falha na execução");
        } else if (event.type === "success") {
            appendLog(`[OK] ${event.message}`, "success");
            setStatus("success", "Auditoria concluída");
            updateProgress(100, "Auditoria concluída");

            if (event.report_base64) {
                lastReportBase64 = event.report_base64;
                lastReportFilename = event.filename || lastReportFilename;
                btnDownloadReport.classList.remove("hidden");
                downloadExcel(lastReportBase64, lastReportFilename);
            }
        } else {
            appendLog(event.message, "log");

            if (event.message.includes("INICIANDO AUDITORIA")) {
                subaccountBase = processedCourses;
            }

            const courseCountMatch = event.message.match(/✅ (\d+) cursos ativos encontrados/);
            if (courseCountMatch) {
                subaccountCourses = Number(courseCountMatch[1]);
                totalCourses += subaccountCourses;
                if (totalCourses > 0) {
                    updateProgress(0, `0 / ${totalCourses} cursos (0%)`);
                }
            }

            const auditMatch = event.message.match(/Auditando curso (\d+)\/(\d+)/);
            if (auditMatch && totalCourses > 0) {
                subaccountCourses = Number(auditMatch[2]);
                processedCourses = subaccountBase + Number(auditMatch[1]);
                const percentage = Math.min(100, Math.round((processedCourses / totalCourses) * 100));
                updateProgress(percentage, `${processedCourses} / ${totalCourses} cursos (${percentage}%)`);
            }

            if (event.message.includes("finalizada:")) {
                subaccountBase += subaccountCourses;
                processedCourses = subaccountBase;
                if (totalCourses > 0) {
                    const percentage = Math.min(100, Math.round((processedCourses / totalCourses) * 100));
                    updateProgress(percentage, `${processedCourses} / ${totalCourses} cursos (${percentage}%)`);
                }
            }
        }
    }

    btnDownloadReport.addEventListener("click", () => {
        if (lastReportBase64) {
            downloadExcel(lastReportBase64, lastReportFilename);
        }
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const apiToken = apiTokenInput.value.trim();
        const subcontas = subcontasInput.value.trim();

        if (!apiToken || !subcontas) return;

        btnRun.disabled = true;
        btnDownloadReport.classList.add("hidden");
        lastReportBase64 = null;
        logConsole.innerHTML = "";
        appendLog("Iniciando auditoria...", "log");
        resetProgress();
        setPreparingProgress();
        setStatus("running", "Executando auditoria...");

        try {
            const response = await fetch("/api/shortcuts/auditoria/execute", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ api_token: apiToken, subcontas }),
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.error || `Erro HTTP ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.trim()) continue;
                    const event = JSON.parse(line);
                    processEvent(event);
                }
            }

            buffer += decoder.decode();
            if (buffer.trim()) {
                try {
                    processEvent(JSON.parse(buffer));
                } catch (err) {
                    appendLog(`[ERRO] Resposta incompleta do servidor: ${err.message}`, "error");
                    setStatus("error", "Erro na resposta");
                }
            }
        } catch (err) {
            appendLog(`[ERRO] ${err.message}`, "error");
            setStatus("error", "Erro na requisição");
        } finally {
            btnRun.disabled = false;
        }
    });
});