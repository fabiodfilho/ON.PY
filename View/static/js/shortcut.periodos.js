document.addEventListener('DOMContentLoaded', () => {
    const execForm = document.getElementById('execFormPeriodos');
    const toggleTokenBtn = document.getElementById('toggleToken');
    const apiTokenInput = document.getElementById('api_token');
    const logConsole = document.getElementById('logConsole');
    const btnClearLogs = document.getElementById('btnClearLogs');
    const btnRun = document.getElementById('btnRun');
    const statusBadge = document.getElementById('statusBadge');

    toggleTokenBtn?.addEventListener('click', () => {
        const type = apiTokenInput.getAttribute('type') === 'password' ? 'text' : 'password';
        apiTokenInput.setAttribute('type', type);
    });

    btnClearLogs?.addEventListener('click', () => {
        logConsole.innerHTML = '<p class="text-slate-500">// Console de logs limpo.</p>';
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
        btnRun.disabled = true;
        setStatus('Processando atualização...', 'bg-amber-400 animate-pulse');
        appendLog('Iniciando comunicação com a API do Canvas...');

        try {
            const response = await fetch('/api/shortcuts/periodos/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
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
                        }
                    } catch (err) {
                        appendLog(line, 'info');
                    }
                }
            }

            setStatus('Concluído!', 'bg-emerald-500');
            appendLog('Processo finalizado.', 'success');

        } catch (err) {
            appendLog(`FALHA: ${err.message}`, 'error');
            setStatus('Erro na execução', 'bg-rose-500');
        } finally {
            btnRun.disabled = false;
        }
    });
});