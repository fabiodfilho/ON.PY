document.addEventListener('DOMContentLoaded', () => {
    const execForm = document.getElementById('execFormPeriodos');
    const toggleTokenBtn = document.getElementById('toggleToken');
    const apiTokenInput = document.getElementById('api_token');
    const logConsole = document.getElementById('logConsole');
    const btnClearLogs = document.getElementById('btnClearLogs');
    const btnRun = document.getElementById('btnRun');
    const btnRunLabel = document.getElementById('btnRunLabel');
    const statusBadge = document.getElementById('statusBadge');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressTrack = progressBar?.parentElement;
    let totalCourses = 0;
    let processedCourses = 0;
    let totalKnown = false;
    let abortController = null;
    let isRunning = false;

    toggleTokenBtn?.addEventListener('click', () => {
        const type = apiTokenInput.getAttribute('type') === 'password' ? 'text' : 'password';
        apiTokenInput.setAttribute('type', type);
    });

    function resetProgress() {
        totalCourses = 0;
        processedCourses = 0;
        totalKnown = false;
        progressBar.classList.remove('animate-pulse');
        progressBar.style.width = '0%';
        progressText.textContent = 'Aguardando execução';
        progressTrack?.setAttribute('aria-valuenow', '0');
    }

    function updateProgress() {
        if (!totalKnown) {
            progressBar.classList.add('animate-pulse');
            progressBar.style.width = '100%';
            progressText.textContent = 'Preparando...';
            return;
        }

        const percentage = Math.min(100, Math.round((processedCourses / totalCourses) * 100));
        progressBar.classList.remove('animate-pulse');
        progressBar.style.width = `${percentage}%`;
        progressText.textContent = `${processedCourses} / ${totalCourses} cursos (${percentage}%)`;
        progressTrack?.setAttribute('aria-valuenow', String(percentage));
    }

    btnClearLogs?.addEventListener('click', () => {
        logConsole.innerHTML = '<p class="text-slate-500">// Console de logs limpo.</p>';
        resetProgress();
    });

    btnRun?.addEventListener('click', (e) => {
        if (!isRunning) return;

        e.preventDefault();
        abortController?.abort();
    });

    function appendLog(msg, type = 'info') {
        const p = document.createElement('p');
        if (type === 'error') p.className = 'text-rose-400';
        else if (type === 'success') p.className = 'text-emerald-400 font-bold';
        else p.className = 'text-slate-300';
        
        p.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
        logConsole.appendChild(p);
        logConsole.scrollTop = logConsole.scrollHeight;
    }

    function setStatus(text, colorClass) {
        statusBadge.innerHTML = `<span class="w-2 h-2 rounded-full ${colorClass}"></span> ${text}`;
    }

    execForm?.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(execForm);
        const data = Object.fromEntries(formData.entries());

        logConsole.innerHTML = '';
        resetProgress();
        isRunning = true;
        abortController = new AbortController();
        btnRunLabel.textContent = 'Cancelar operação';
        btnRun.classList.remove('bg-brand-600', 'hover:bg-brand-700');
        btnRun.classList.add('bg-rose-600', 'hover:bg-rose-700');
        setStatus('Processando atualização...', 'bg-amber-400 animate-pulse');
        appendLog('Iniciando comunicação com a API do Canvas...');

        try {
            const response = await fetch('/api/shortcuts/periodos/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
                signal: abortController.signal
            });

            if (!response.ok) {
                const errJson = await response.json().catch(() => ({}));
                throw new Error(errJson.error || `Erro HTTP ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const item = JSON.parse(line);
                        if (item.type !== 'done') {
                            appendLog(item.message, item.type);

                            const totalMatch = item.message.match(/Total de (\d+) curso\(s\) único\(s\) para atualizar/);
                            if (totalMatch) {
                                totalCourses = Number(totalMatch[1]);
                                totalKnown = true;
                            }

                            if (item.message.match(/^(?:Curso ID|Falha no curso ID|Erro de conexão no curso ID)\b/)) {
                                processedCourses += 1;
                            }

                            updateProgress();
                        } else {
                            processedCourses = totalCourses;
                            updateProgress();
                        }
                    } catch (err) {
                        appendLog(line, 'info');
                    }
                }
            }

            setStatus('Concluído!', 'bg-emerald-500');
            processedCourses = totalCourses;
            updateProgress();
            appendLog('Processo finalizado.', 'success');

        } catch (err) {
            if (abortController?.signal.aborted || err.name === 'AbortError') {
                appendLog('Operação cancelada pelo usuário.', 'info');
                setStatus('Cancelado', 'bg-slate-500');
            } else {
                appendLog(`FALHA: ${err.message}`, 'error');
                setStatus('Erro na execução', 'bg-rose-500');
            }
        } finally {
            isRunning = false;
            abortController = null;
            btnRunLabel.textContent = 'Atualizar Períodos';
            btnRun.classList.remove('bg-rose-600', 'hover:bg-rose-700');
            btnRun.classList.add('bg-brand-600', 'hover:bg-brand-700');
        }
    });
});