window.addEventListener("pageshow", () => {
    document.body.classList.remove("page-exit");
});

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("execForm");
    const btnRun = document.getElementById("btnRun");
    const consoleEl = document.getElementById("logConsole");
    const statusBadge = document.getElementById("statusBadge");
    const downloadContainer = document.getElementById("downloadContainer");
    const downloadBtn = document.getElementById("downloadBtn");
    const apiTokenInput = document.getElementById("api_token");
    const subcontasInput = document.getElementById("subcontas");

    const toggleBtn = document.getElementById("toggleToken");
    if (toggleBtn) {
        toggleBtn.addEventListener("click", () => {
            apiTokenInput.type =
                apiTokenInput.type === "password" ? "text" : "password";
        });
    }

    const btnClearLogs = document.getElementById("btnClearLogs");
    if (btnClearLogs) {
        btnClearLogs.addEventListener("click", () => {
            consoleEl.innerHTML =
                '<p class="text-slate-500">// Logs limpos.</p>';
        });
    }

    function addLog(msg, type = "info") {
        const time = new Date().toLocaleTimeString();
        const p = document.createElement("p");
        const timeSpan = document.createElement("span");

        if (type === "error") p.className = "text-rose-400 font-semibold";
        else if (type === "success") p.className = "text-emerald-300 font-bold";
        else if (type === "warning") p.className = "text-amber-300 font-semibold";
        else p.className = "text-slate-300";

        timeSpan.className = "text-slate-500";
        timeSpan.textContent = `[${time}] `;
        p.append(timeSpan, document.createTextNode(msg));
        consoleEl.appendChild(p);
        consoleEl.scrollTop = consoleEl.scrollHeight;
    }

    function validarFormulario(token, subcontasRaw) {
        const erros = [];

        if (!token || token.trim().length === 0) {
            erros.push("O Token de API do Canvas é obrigatório.");
        } else if (token.trim().length < 10) {
            erros.push("O Token informado é curto demais para ser um token válido.");
        }

        if (!subcontasRaw || subcontasRaw.trim().length === 0) {
            erros.push("Informe ao menos um ID de subconta.");
            return { valido: false, erros, subcontasLimpas: [] };
        }

        const itens = subcontasRaw
            .split(/[\n\r,\s]+/)
            .map((item) => item.trim())
            .filter(Boolean);

        if (itens.length === 0) {
            erros.push("Nenhum ID de subconta foi identificado no texto.");
            return { valido: false, erros, subcontasLimpas: [] };
        }

        const invalidos = [];
        const validos = [];

        itens.forEach((item) => {
            if (/^\d+$/.test(item)) validos.push(item);
            else invalidos.push(item);
        });

        if (invalidos.length > 0) {
            const listaInvalidos = invalidos
                .map((item) => `"${item}"`)
                .join(", ");
            erros.push(
                `IDs de subconta inválidos identificados: ${listaInvalidos}. ` +
                "Os IDs devem conter estritamente números inteiros."
            );
        }

        return {
            valido: erros.length === 0,
            erros,
            subcontasLimpas: validos,
        };
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const token = apiTokenInput.value.trim();
        const validacao = validarFormulario(token, subcontasInput.value);

        if (!validacao.valido) {
            consoleEl.innerHTML = "";
            statusBadge.innerHTML =
                '<span class="w-2 h-2 rounded-full bg-rose-500"></span> Dados Inválidos';
            addLog("Erro de validação nos dados inseridos:", "error");
            validacao.erros.forEach((erro) => addLog(`• ${erro}`, "error"));
            return;
        }

        btnRun.disabled = true;
        downloadContainer.classList.add("hidden");
        statusBadge.innerHTML =
            '<span class="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span> Processando...';
        consoleEl.innerHTML = "";
        addLog(
            `Iniciando extração para ${validacao.subcontasLimpas.length} ` +
            "subconta(s) válida(s)..."
        );

        const formData = new FormData();
        formData.append("api_token", token);
        formData.append("subcontas", validacao.subcontasLimpas.join(","));

        try {
            const response = await fetch("/api/shortcuts/ofertas/executar", {
                method: "POST",
                body: formData,
            });

            if (!response.ok) {
                addLog("Erro na resposta do servidor.", "error");
                statusBadge.innerHTML =
                    '<span class="w-2 h-2 rounded-full bg-rose-500"></span> Erro';
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let pendingLine = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                pendingLine += decoder.decode(value, { stream: true });
                const lines = pendingLine.split("\n");
                pendingLine = lines.pop();
                lines.forEach(processLogLine);
            }

            pendingLine += decoder.decode();
            if (pendingLine) processLogLine(pendingLine);
            statusBadge.innerHTML =
                '<span class="w-2 h-2 rounded-full bg-emerald-500"></span> Concluído';
        } catch (error) {
            addLog(`Falha na comunicação: ${error.message}`, "error");
            statusBadge.innerHTML =
                '<span class="w-2 h-2 rounded-full bg-rose-500"></span> Erro';
        } finally {
            btnRun.disabled = false;
        }
    });

    function processLogLine(line) {
        if (line.startsWith("LOG:")) {
            addLog(line.replace("LOG:", ""), "info");
        } else if (line.startsWith("SUCCESS:")) {
            addLog(line.replace("SUCCESS:", ""), "success");
        } else if (line.startsWith("ERROR:")) {
            addLog(line.replace("ERROR:", ""), "error");
        } else if (line.startsWith("DOWNLOAD:")) {
            const filename = line.replace("DOWNLOAD:", "").trim();
            if (downloadBtn) {
                downloadBtn.href =
                    `/api/shortcuts/ofertas/download/${filename}`;
            }
            downloadContainer.classList.remove("hidden");
        }
    }

    document.body.classList.remove("page-exit");
    document.querySelectorAll('a[href^="/"]').forEach((anchor) => {
        anchor.addEventListener("click", function (event) {
            const targetUrl = this.getAttribute("href");
            if (!targetUrl || targetUrl === "#" || this.target === "_blank") {
                return;
            }
            event.preventDefault();
            document.body.classList.add("page-exit");
            setTimeout(() => {
                window.location.href = targetUrl;
            }, 200);
        });
    });
});
