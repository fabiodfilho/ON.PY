document.addEventListener('DOMContentLoaded', () => {
    const execForm = document.getElementById('execFormInativar');
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
    let abortController = null;
    let isRunning = false;

    function resetProgress() {
        totalCourses = 0;
        processedCourses = 0;
        progressBar.classList.remove('animate-pulse');
        progressBar.style.width = '0%';
        progressText.textContent = 'Aguardando execução';
        progressTrack?.setAttribute('aria-valuenow', '0');
    }

    function setPreparingProgress() {
        progressBar.classList.add('animate-pulse');
        progressBar.style.width = '100%';
        progressText.textContent = 'Preparando...';
    }

    function updateProgress() {
        if (totalCourses <= 0) {
            setPreparingProgress();
            return;
        }
        const percentage = Math.min(100, Math.round((processedCourses / totalCourses) * 100));
        progressBar.classList.remove('animate-pulse');
        progressBar.style.width = `${percentage}%`;
        progressText.textContent = `${processedCourses} / ${totalCourses} cursos (${percentage}%)`;
        progressTrack?.setAttribute('aria-valuenow', String(percentage));
    }

    toggleTokenBtn?.addEventListener('click', () => {
        const type = apiTokenInput.getAttribute('type') === 'password' ? 'text' : 'password';
        apiTokenInput.setAttribute('type', type);
    });

    btnClearLogs?.addEventListener('click', () => {
        logConsole.innerHTML = '<p class="text-slate-500">// Console de logs limpo.</p>';
        resetProgress();
    });

    function appendLog(msg, type = 'info') {
        const p = document.createElement('p');
        if (type === 'error') p.className = 'text-rose-400 font-semibold';
        else if (type === 'success') p.className = 'text-emerald-400 font-bold';
        else p.className = 'text-slate-300';
        
        p.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
        logConsole.appendChild(p);
        logConsole.scrollTop = logConsole.scrollHeight;
    }

    function setStatus(text, colorClass) {
        statusBadge.innerHTML = `<span class="w-2 h-2 rounded-full ${colorClass}"></span> ${text}`;
    }

    btnRun?.addEventListener('click', (e) => {
        if (!isRunning) return;
        e.preventDefault();
        abortController?.abort();
    });

    execForm?.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(execForm);
        const data = Object.fromEntries(formData.entries());

        logConsole.innerHTML = '';
        isRunning = true;
        abortController = new AbortController();
        btnRunLabel.textContent = 'Cancelar operação';
        btnRun.classList.remove('bg-rose-600', 'hover:bg-rose-700');
        btnRun.classList.add('bg-slate-600', 'hover:bg-slate-700');
        resetProgress();
        setPreparingProgress();
        setStatus('Inativando e despublicando...', 'bg-amber-400 animate-pulse');
        appendLog('Iniciando comunicação com a API do Canvas...');

        try {
            const response = await fetch('/api/shortcuts/inativar/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
                signal: abortController.signal,
                cache: 'no-store'
            });

            if (!response.ok) {
                const errJson = await response.json().catch(() => ({}));
                throw new Error(errJson.error || `Erro HTTP ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let hasError = false;
            let receivedDone = false;

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
                        if (item.type === 'error') {
                            hasError = true;
                            appendLog(item.message, 'error');
                        } else if (item.type === 'done') {
                            receivedDone = true;
                            processedCourses = totalCourses;
                            updateProgress();
                        } else {
                            appendLog(item.message, item.type);

                            const courseCountMatch = item.message.match(/Iniciando processo para (\d+) curso\(s\)\./);
                            if (courseCountMatch) {
                                totalCourses = Number(courseCountMatch[1]);
                                updateProgress();
                            }

                            const courseFinishedMatch = item.message.match(/Curso (\d+) despublicado com sucesso!/);
                            if (courseFinishedMatch) {
                                processedCourses += 1;
                                updateProgress();
                            }
                        }
                    } catch (err) {
                        appendLog(line, 'info');
                    }
                }
            }

            if (buffer.trim()) {
                try {
                    const item = JSON.parse(buffer);
                    if (item.type === 'error') {
                        hasError = true;
                        appendLog(item.message, 'error');
                    } else if (item.type === 'done') {
                        receivedDone = true;
                        processedCourses = totalCourses;
                        updateProgress();
                    } else {
                        appendLog(item.message, item.type);

                        const courseCountMatch = item.message.match(/Iniciando processo para (\d+) curso\(s\)\./);
                        if (courseCountMatch) {
                            totalCourses = Number(courseCountMatch[1]);
                            updateProgress();
                        }

                        const courseFinishedMatch = item.message.match(/Curso (\d+) despublicado com sucesso!/);
                        if (courseFinishedMatch) {
                            processedCourses += 1;
                            updateProgress();
                        }
                    }
                } catch (err) {
                    appendLog(buffer, 'info');
                }
            }

            if (!receivedDone || hasError) {
                setStatus('Erro na execução', 'bg-rose-500');
                appendLog(
                    !receivedDone
                        ? 'A execução foi interrompida antes da conclusão.'
                        : 'Processo finalizado com erros.',
                    'error'
                );
            } else {
                setStatus('Concluído!', 'bg-emerald-500');
                appendLog('Processo finalizado com sucesso.', 'success');
            }

        } catch (err) {
            if (abortController?.signal.aborted || err.name === 'AbortError') {
                appendLog('Operação cancelada pelo usuário.', 'info');
                setStatus('Operação cancelada', 'bg-slate-500');
            } else {
                appendLog(`FALHA: ${err.message}`, 'error');
                setStatus('Erro na execução', 'bg-rose-500');
            }
        } finally {
            isRunning = false;
            abortController = null;
            btnRunLabel.textContent = 'Inativar & Despublicar';
            btnRun.classList.remove('bg-slate-600', 'hover:bg-slate-700');
            btnRun.classList.add('bg-rose-600', 'hover:bg-rose-700');
        }
    });
});