// nodes.js
(function() {
    let initialized = false;
    let nodes = [];
    let cpuChart = null;
    let memoryChart = null;
    let tempChart = null;
    let lastChartsUpdateTs = 0;
    let mon = null;

    function updateNodesList() {
        console.log('[NODES.JS] updateNodesList', nodes);
        const container = document.getElementById('nodes-list');
        const countElement = document.getElementById('nodes-count');
        if (!container || !countElement) return; // Sécurité DOM
        countElement.textContent = `${nodes.length} nœud${nodes.length > 1 ? 's' : ''}`;
        if (nodes.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 col-span-full">
                    <i class="fas fa-server text-gray-300 text-4xl mb-4"></i>
                    <p class="text-gray-500">Aucun nœud disponible</p>
                </div>
            `;
            return;
        }
        container.innerHTML = nodes.map(node => {
            const cpu = Number(node.cpu_usage || 0);
            const mem = Number(node.memory_usage || 0);
            const temp = Number(node.temperature || 0);
            const disk = Number(node.disk_usage || 0);
            const up = (node.status === 'ready' || node.is_healthy);
            return `
            <div class="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
                <div class="flex items-center justify-between mb-4">
                    <div class="flex items-center space-x-3">
                        <div class="w-3 h-3 rounded-full ${up ? 'bg-green-500' : 'bg-red-500'}"></div>
                        <h3 class="text-lg font-semibold text-gray-900">${node.node}</h3>
                        <span class="px-2 py-1 rounded-full text-xs font-medium ${up ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">${up ? 'En ligne' : 'Hors ligne'}</span>
                    </div>
                    <div class="text-sm text-gray-500">MAJ: ${new Date().toLocaleTimeString()}</div>
                </div>
                <div class="space-y-3">
                    <div>
                        <div class="flex justify-between text-sm text-gray-600"><span>CPU</span><span>${cpu.toFixed(1)}%</span></div>
                        <div class="w-full h-2 bg-gray-100 rounded"><div class="h-2 rounded ${cpu<60?'bg-yellow-400':cpu<85?'bg-orange-500':'bg-red-600'}" style="width:${Math.min(cpu,100)}%"></div></div>
                    </div>
                    <div>
                        <div class="flex justify-between text-sm text-gray-600"><span>Mémoire</span><span>${mem.toFixed(1)}%</span></div>
                        <div class="w-full h-2 bg-gray-100 rounded"><div class="h-2 rounded ${mem<60?'bg-purple-500':mem<85?'bg-purple-600':'bg-purple-800'}" style="width:${Math.min(mem,100)}%"></div></div>
                    </div>
                    <div>
                        <div class="flex justify-between text-sm text-gray-600"><span>Disque</span><span>${disk.toFixed(1)}%</span></div>
                        <div class="w-full h-2 bg-gray-100 rounded"><div class="h-2 rounded ${disk<70?'bg-blue-500':disk<90?'bg-blue-600':'bg-blue-800'}" style="width:${Math.min(disk,100)}%"></div></div>
                    </div>
                    <div>
                        <div class="flex justify-between text-sm text-gray-600"><span>Température</span><span>${temp.toFixed(1)}°C</span></div>
                        <div class="w-full h-2 bg-gray-100 rounded"><div class="h-2 rounded ${temp<55?'bg-green-500':temp<70?'bg-yellow-500':'bg-red-600'}" style="width:${Math.min(temp,100)}%"></div></div>
                    </div>
                </div>
            </div>`;
        }).join('');
    }

    function updateOverviewMetrics() {
        console.log('[NODES.JS] updateOverviewMetrics');
        // Vérif DOM
        const onlineEl = document.getElementById('nodes-online');
        const avgCpuEl = document.getElementById('avg-cpu');
        const avgMemEl = document.getElementById('avg-memory');
        const avgTempEl = document.getElementById('avg-temp');
        if (!onlineEl || !avgCpuEl || !avgMemEl || !avgTempEl) return;
        const online = nodes.filter(n => (n.status === 'ready' || n.is_healthy));
        const avg = (arr) => arr.length ? (arr.reduce((a,b)=>a+b,0) / arr.length) : 0;
        const avgCpu = avg(online.map(n => n.cpu_usage || 0));
        const avgMem = avg(online.map(n => n.memory_usage || 0));
        const avgTemp = avg(online.map(n => n.temperature || 0));
        onlineEl.textContent = online.length.toString();
        avgCpuEl.textContent = avgCpu ? `${avgCpu.toFixed(1)}%` : '-';
        avgMemEl.textContent = avgMem ? `${avgMem.toFixed(1)}%` : '-';
        avgTempEl.textContent = avgTemp ? `${avgTemp.toFixed(1)}°C` : '-';
    }

    function updateCharts() {
        console.log('[NODES.JS] updateCharts');
        const cpuCanvas = document.getElementById('cpu-chart');
        const memCanvas = document.getElementById('memory-chart');
        const tempCanvas = document.getElementById('temp-chart');
        if (!cpuCanvas || !memCanvas || !tempCanvas) return;
        const now = Date.now();
        if (now - lastChartsUpdateTs < 1200) return;
        lastChartsUpdateTs = now;
        const onlineNodes = nodes.filter(n => (n.status === 'ready' || n.is_healthy));
        const labels = onlineNodes.map(n => n.node);
        const cpuData = onlineNodes.map(n => n.cpu_usage || 0);
        const memData = onlineNodes.map(n => n.memory_usage || 0);
        const tempData = onlineNodes.map(n => n.temperature || 0);
        const commonOptions = {
            responsive: true,
            animation: { duration: 0 },
            scales: { y: { beginAtZero: true, suggestedMax: 100 } },
            plugins: { legend: { display: false } }
        };
        if (!cpuChart) {
            cpuChart = new Chart(cpuCanvas.getContext('2d'), {
                type: 'bar',
                data: { labels, datasets: [{ label: 'CPU', data: cpuData, backgroundColor: 'rgba(251,191,36,0.8)' }] },
                options: commonOptions
            });
        } else {
            cpuChart.data.labels = labels;
            cpuChart.data.datasets[0].data = cpuData;
            cpuChart.update('none');
        }
        if (!memoryChart) {
            memoryChart = new Chart(memCanvas.getContext('2d'), {
                type: 'bar',
                data: { labels, datasets: [{ label: 'Mémoire', data: memData, backgroundColor: 'rgba(147,51,234,0.8)' }] },
                options: commonOptions
            });
        } else {
            memoryChart.data.labels = labels;
            memoryChart.data.datasets[0].data = memData;
            memoryChart.update('none');
        }
        if (!tempChart) {
            tempChart = new Chart(tempCanvas.getContext('2d'), {
                type: 'bar',
                data: { labels, datasets: [{ label: 'Température', data: tempData, backgroundColor: 'rgba(239,68,68,0.8)' }] },
                options: {...commonOptions, scales: { y: { beginAtZero: true } } }
            });
        } else {
            tempChart.data.labels = labels;
            tempChart.data.datasets[0].data = tempData;
            tempChart.update('none');
        }
    }

    function cleanupCharts() {
        if (cpuChart) { cpuChart.destroy(); cpuChart = null; }
        if (memoryChart) { memoryChart.destroy(); memoryChart = null; }
        if (tempChart) { tempChart.destroy(); tempChart = null; }
    }

    function onNodesPage() {
        if (initialized) return;
        initialized = true;
        console.log('[NODES.JS] onNodesPage - listeners WS branchés');
        // Branche le WS seulement ici (évite les fuites listeners et multiples WS)
        mon = window.App && window.App.sockets && window.App.sockets.monitoring
            ? window.App.sockets.monitoring
            : io('/monitoring');
        mon.on('cluster_metrics', handleClusterMetrics);
        mon.on('connect', () => {
            console.log('[NODES.JS] SOCKET MONITORING CONNECTED');
            mon.emit('request_nodes_status', {});
        });
        // Pour éviter des soucis lors du retour, gère une cleanup si tu veux (à voir sur page:leave)
        // Ecoute update globale cluster_metrics côté app.js aussi
        document.addEventListener('app:cluster_metrics', (evt) => {
            console.log('[NODES.JS] EVENT app:cluster_metrics', evt.detail);
            handleClusterMetrics(evt.detail);
        });
    }
    
    function handleClusterMetrics(data) {
        console.log('[NODES.JS] handleClusterMetrics', data);
        const mapped = data && data.nodes ? Object.entries(data.nodes).map(([node, metrics]) => ({
            node,
            cpu_usage: metrics.cpu_usage || 0,
            memory_usage: metrics.memory_usage || 0,
            disk_usage: (metrics.disk_usage !== undefined) ? metrics.disk_usage : (metrics.disk_total ? (100 - (100 * (metrics.disk_available || 0) / metrics.disk_total)) : 0),
            temperature: metrics.temperature || 0,
            is_healthy: metrics.is_healthy,
            status: (metrics.cpu_usage || 0) > 0 ? 'ready' : 'unknown'
        })) : [];
        nodes = mapped;
        updateNodesList();
        updateOverviewMetrics();
        updateCharts();
    }

    document.addEventListener('page:enter', (event) => {
        if (event.detail.page === 'nodes') {
            console.log('[NODES.JS] page:enter nodes!');
            onNodesPage();
        }
    });
    if (window.location.pathname === '/nodes') {
        document.dispatchEvent(new CustomEvent('page:enter', { detail: { page: 'nodes', path: window.location.pathname } }));
    }
    // Tu pourrais envisager un page:leave pour destroy les charts si besoin.
})();
