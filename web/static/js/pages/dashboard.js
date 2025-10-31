// dashboard.js
(function() {
    let initialized = false;

    // --- TimeSeries helpers ---
    async function fetchTimeSeries(key, fromMs, toMs, agg, bucketMs) {
        const params = new URLSearchParams({ key: key, frm: String(fromMs), to: String(toMs) });
        if (agg) params.append('agg', agg);
        if (bucketMs) params.append('bucket_ms', String(bucketMs));
        const url = `/api/ts/range?${params.toString()}`;
        try {
            const res = await fetch(url);
            if (!res.ok) throw new Error(`TS fetch failed: ${res.status}`);
            return await res.json();
        } catch (e) {
            window.App && window.App.logger && window.App.logger.error('[DASHBOARD.JS] TS fetch error', e);
            return null;
        }
    }

    function updateTsCpu(points) {
        const avgEl = document.getElementById('ts-cpu-avg');
        const minEl = document.getElementById('ts-cpu-min');
        const maxEl = document.getElementById('ts-cpu-max');
        const lastEl = document.getElementById('ts-cpu-last');
        if (!avgEl || !minEl || !maxEl || !lastEl) return;

        if (!points || points.length === 0) {
            avgEl.textContent = '-';
            minEl.textContent = '-';
            maxEl.textContent = '-';
            lastEl.textContent = '-';
            return;
        }

        const values = points.map(p => Array.isArray(p) ? Number(p[1]) : Number(p.value || 0)).filter(v => !Number.isNaN(v));
        if (values.length === 0) {
            avgEl.textContent = '-';
            minEl.textContent = '-';
            maxEl.textContent = '-';
            lastEl.textContent = '-';
            return;
        }
        const sum = values.reduce((a,b) => a + b, 0);
        const avg = sum / values.length;
        const min = Math.min(...values);
        const max = Math.max(...values);
        const last = values[values.length - 1];

        avgEl.textContent = avg.toFixed(1) + '%';
        minEl.textContent = min.toFixed(1) + '%';
        maxEl.textContent = max.toFixed(1) + '%';
        lastEl.textContent = last.toFixed(1) + '%';
    }

    async function loadTsCpu() {
        const now = Date.now();
        const oneHourAgo = now - 3600000; // 1h
        // Agrégation 1 minute côté serveur pour limiter la charge
        const data = await fetchTimeSeries('ts:cpu.usage', oneHourAgo, now, 'avg', 60000);
        if (data && Array.isArray(data.points)) {
            updateTsCpu(data.points);
        } else {
            updateTsCpu([]);
        }
    }

    function updateTsMem(points) {
        const avgEl = document.getElementById('ts-mem-avg');
        const minEl = document.getElementById('ts-mem-min');
        const maxEl = document.getElementById('ts-mem-max');
        const lastEl = document.getElementById('ts-mem-last');
        if (!avgEl || !minEl || !maxEl || !lastEl) return;

        if (!points || points.length === 0) {
            avgEl.textContent = '-';
            minEl.textContent = '-';
            maxEl.textContent = '-';
            lastEl.textContent = '-';
            return;
        }

        const values = points.map(p => Array.isArray(p) ? Number(p[1]) : Number(p.value || 0)).filter(v => !Number.isNaN(v));
        if (values.length === 0) {
            avgEl.textContent = '-';
            minEl.textContent = '-';
            maxEl.textContent = '-';
            lastEl.textContent = '-';
            return;
        }
        const sum = values.reduce((a,b) => a + b, 0);
        const avg = sum / values.length;
        const min = Math.min(...values);
        const max = Math.max(...values);
        const last = values[values.length - 1];

        avgEl.textContent = avg.toFixed(1) + '%';
        minEl.textContent = min.toFixed(1) + '%';
        maxEl.textContent = max.toFixed(1) + '%';
        lastEl.textContent = last.toFixed(1) + '%';
    }

    async function loadTsMem() {
        const now = Date.now();
        const oneHourAgo = now - 3600000; // 1h
        const data = await fetchTimeSeries('ts:memory.usage', oneHourAgo, now, 'avg', 60000);
        if (data && Array.isArray(data.points)) {
            updateTsMem(data.points);
        } else {
            updateTsMem([]);
        }
    }

    function updateTsDisk(points) {
        const avgEl = document.getElementById('ts-disk-avg');
        const minEl = document.getElementById('ts-disk-min');
        const maxEl = document.getElementById('ts-disk-max');
        const lastEl = document.getElementById('ts-disk-last');
        if (!avgEl || !minEl || !maxEl || !lastEl) return;

        if (!points || points.length === 0) {
            avgEl.textContent = '-';
            minEl.textContent = '-';
            maxEl.textContent = '-';
            lastEl.textContent = '-';
            return;
        }

        const values = points.map(p => Array.isArray(p) ? Number(p[1]) : Number(p.value || 0)).filter(v => !Number.isNaN(v));
        if (values.length === 0) {
            avgEl.textContent = '-';
            minEl.textContent = '-';
            maxEl.textContent = '-';
            lastEl.textContent = '-';
            return;
        }
        const sum = values.reduce((a,b) => a + b, 0);
        const avg = sum / values.length;
        const min = Math.min(...values);
        const max = Math.max(...values);
        const last = values[values.length - 1];

        avgEl.textContent = avg.toFixed(1) + '%';
        minEl.textContent = min.toFixed(1) + '%';
        maxEl.textContent = max.toFixed(1) + '%';
        lastEl.textContent = last.toFixed(1) + '%';
    }

    async function loadTsDisk() {
        const now = Date.now();
        const oneHourAgo = now - 3600000;
        const data = await fetchTimeSeries('ts:disk.usage', oneHourAgo, now, 'avg', 60000);
        if (data && Array.isArray(data.points)) {
            updateTsDisk(data.points);
        } else {
            updateTsDisk([]);
        }
    }

    function updateTsTemp(points) {
        const avgEl = document.getElementById('ts-temp-avg');
        const minEl = document.getElementById('ts-temp-min');
        const maxEl = document.getElementById('ts-temp-max');
        const lastEl = document.getElementById('ts-temp-last');
        if (!avgEl || !minEl || !maxEl || !lastEl) return;

        if (!points || points.length === 0) {
            avgEl.textContent = '-';
            minEl.textContent = '-';
            maxEl.textContent = '-';
            lastEl.textContent = '-';
            return;
        }

        const values = points.map(p => Array.isArray(p) ? Number(p[1]) : Number(p.value || 0)).filter(v => !Number.isNaN(v));
        if (values.length === 0) {
            avgEl.textContent = '-';
            minEl.textContent = '-';
            maxEl.textContent = '-';
            lastEl.textContent = '-';
            return;
        }
        const sum = values.reduce((a,b) => a + b, 0);
        const avg = sum / values.length;
        const min = Math.min(...values);
        const max = Math.max(...values);
        const last = values[values.length - 1];

        avgEl.textContent = avg.toFixed(1) + '°C';
        minEl.textContent = min.toFixed(1) + '°C';
        maxEl.textContent = max.toFixed(1) + '°C';
        lastEl.textContent = last.toFixed(1) + '°C';
    }

    async function loadTsTemp() {
        const now = Date.now();
        const oneHourAgo = now - 3600000;
        const data = await fetchTimeSeries('ts:temperature', oneHourAgo, now, 'avg', 60000);
        if (data && Array.isArray(data.points)) {
            updateTsTemp(data.points);
        } else {
            updateTsTemp([]);
        }
    }

    function updateFromOverview(overview) {
        window.App.logger.debug('[DASHBOARD.JS] updateFromOverview', overview);
        if (!overview) return;
        const nodesOnline = document.getElementById('nodes-online');
        const nodesTotal = document.getElementById('nodes-total');
        const avgCpu = document.getElementById('avg-cpu');
        const avgMem = document.getElementById('avg-memory');
        if (nodesOnline && overview.cluster_stats?.online_nodes !== undefined) nodesOnline.textContent = overview.cluster_stats.online_nodes;
        if (nodesTotal && overview.cluster_stats?.total_nodes !== undefined) nodesTotal.textContent = overview.cluster_stats.total_nodes;
        if (avgCpu && overview.cluster_stats?.avg_cpu !== undefined) avgCpu.textContent = overview.cluster_stats.avg_cpu.toFixed(1) + '%';
        if (avgMem && overview.cluster_stats?.avg_memory !== undefined) avgMem.textContent = overview.cluster_stats.avg_memory.toFixed(1) + '%';
    }
    function updateNodesList(overview) {
        window.App.logger.debug('[DASHBOARD.JS] updateNodesList', overview);
        const container = document.getElementById('nodes-list');
        if (!container) return;
        let nodes = [];
        if (overview && overview.nodes) {
            nodes = Object.entries(overview.nodes).map(([node, metrics]) => ({
                node,
                cpu_usage: metrics.cpu_usage || 0,
                memory_usage: metrics.memory_usage || 0,
                status: (metrics.cpu_usage || 0) > 0 ? 'ready' : 'unknown',
                temperature: metrics.temperature || null,
            }));
        }
        if (nodes.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-center py-4">Aucun nœud disponible</p>';
            return;
        }
        container.innerHTML = nodes.slice(0, 5).map(node => `
            <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg mb-2">
                <div class="flex items-center">
                    <i class="fas fa-server text-gray-400 mr-3"></i>
                    <div>
                        <div class="font-medium">${node.node}</div>
                        <div class="text-sm text-gray-500">
                            CPU: ${node.cpu_usage?.toFixed(1) || 0}% | RAM: ${node.memory_usage?.toFixed(1) || 0}%
                        </div>
                    </div>
                </div>
                <span class="px-2 py-1 rounded-full text-xs font-medium ${
                    (node.status === 'ready') ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }">${(node.status === 'ready') ? 'En ligne' : 'Hors ligne'}</span>
            </div>
        `).join('');
        updateTops(nodes);
    }
    function updateTops(nodes) {
        window.App.logger.debug('[DASHBOARD.JS] updateTops', nodes);
        const topCpu = [...nodes].sort((a,b) => (b.cpu_usage||0) - (a.cpu_usage||0)).slice(0,3);
        const topCpuEl = document.getElementById('top-cpu');
        if (topCpuEl) topCpuEl.innerHTML = topCpu.length ? topCpu.map(n => `
            <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg mb-2">
                <div class="flex items-center">
                    <i class="fas fa-microchip text-yellow-500 mr-3"></i>
                    <div>
                        <div class="font-medium">${n.node}</div>
                        <div class="text-sm text-gray-500">CPU: ${(n.cpu_usage||0).toFixed(1)}%</div>
                    </div>
                </div>
                <span class="text-sm font-medium ${n.cpu_usage>80?'text-red-600':n.cpu_usage>60?'text-orange-600':'text-yellow-700'}">${(n.cpu_usage||0).toFixed(1)}%</span>
            </div>`).join('') : '<p class="text-gray-500 text-center py-4">Aucune donnée</p>';
        const topMem = [...nodes].sort((a,b) => (b.memory_usage||0) - (a.memory_usage||0)).slice(0,3);
        const topMemEl = document.getElementById('top-mem');
        if (topMemEl) topMemEl.innerHTML = topMem.length ? topMem.map(n => `
            <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg mb-2">
                <div class="flex items-center">
                    <i class="fas fa-memory text-purple-600 mr-3"></i>
                    <div>
                        <div class="font-medium">${n.node}</div>
                        <div class="text-sm text-gray-500">RAM: ${(n.memory_usage||0).toFixed(1)}%</div>
                    </div>
                </div>
                <span class="text-sm font-medium ${n.memory_usage>85?'text-red-600':n.memory_usage>60?'text-purple-700':'text-purple-600'}">${(n.memory_usage||0).toFixed(1)}%</span>
            </div>`).join('')  : '<p class="text-gray-500 text-center py-4">Aucune donnée</p>';
        const withTemp = nodes.filter(n => typeof n.temperature === 'number');
        const topTemp = withTemp.sort((a,b) => (b.temperature||0) - (a.temperature||0)).slice(0,3);
        const topTempEl = document.getElementById('top-temp');
        if (topTempEl) topTempEl.innerHTML = topTemp.length ? topTemp.map(n => `
            <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg mb-2">
                <div class="flex items-center">
                    <i class="fas fa-thermometer-half text-red-600 mr-3"></i>
                    <div>
                        <div class="font-medium">${n.node}</div>
                        <div class="text-sm text-gray-500">Temp: ${(n.temperature||0).toFixed(1)}°C</div>
                    </div>
                </div>
                <span class="text-sm font-medium ${n.temperature>70?'text-red-600':n.temperature>55?'text-yellow-600':'text-green-600'}">${(n.temperature||0).toFixed(1)}°C</span>
            </div>`).join('') : '<p class="text-gray-500 text-center py-4">Aucune donnée</p>';
    }
    function updateAlerts(alerts) {
        window.App.logger.debug('[DASHBOARD.JS] updateAlerts', alerts);
        const card = document.getElementById('alerts-card');
        const container = document.getElementById('alerts-content');
        if (!card || !container) return;
        if (!alerts?.active_alerts || alerts.active_alerts.length === 0) {
            card.style.display = 'none';
            container.innerHTML = '<p class="text-green-600 text-center py-4"><i class="fas fa-check-circle mr-2"></i>Aucune alerte active</p>';
            return;
        }
        card.style.display = '';
        container.innerHTML = alerts.active_alerts.slice(0,6).map(alert => `
            <div class="flex items-center p-3 bg-red-50 border-l-4 border-red-400 rounded-lg mb-2">
                <i class="fas fa-exclamation-triangle text-red-600 mr-3"></i>
                <div class="text-red-800">${alert.message || alert}</div>
            </div>
        `).join('');
    }
    function onEnterDashboard() {
        if (initialized) return;
        initialized = true;
        window.App.logger.debug('[DASHBOARD.JS] onEnterDashboard : listeners setup');
        document.addEventListener('app:cluster_metrics', (event) => {
            window.App.logger.debug('[DASHBOARD.JS] EVENT app:cluster_metrics', event.detail);
            updateFromOverview(event.detail);
            updateNodesList(event.detail);
        });
        document.addEventListener('app:alerts_update', (event) => {
            window.App.logger.debug('[DASHBOARD.JS] EVENT app:alerts_update', event.detail);
            updateAlerts(event.detail);
        });
        // Afficher direct les dernières valeurs si dispo (state ou cache)
        let firstCluster = null;
        if (window.App && window.App.state && window.App.state.lastClusterMetrics) {
            firstCluster = window.App.state.lastClusterMetrics;
        } else if (window.App && window.App.cache) {
            firstCluster = window.App.cache.load(window.App.cache.keys.cluster);
        }
        if(firstCluster){
            window.App.logger.debug('[DASHBOARD.JS] FIRST DATA IMMEDIATE', firstCluster);
            updateFromOverview(firstCluster);
            updateNodesList(firstCluster);
        }
        let firstAlerts = null;
        if (window.App && window.App.state && window.App.state.lastAlerts) {
            firstAlerts = window.App.state.lastAlerts;
        } else if (window.App && window.App.cache) {
            firstAlerts = window.App.cache.load(window.App.cache.keys.alerts);
        }
        if(firstAlerts){
            updateAlerts(firstAlerts);
        }

        // Charger la série CPU via l'API TS
        loadTsCpu();
        // Charger la série Mémoire via l'API TS
        loadTsMem();
        // Charger la série Disque via l'API TS
        loadTsDisk();
        // Charger la série Température via l'API TS
        loadTsTemp();
        // Rafraîchir toutes les 60s
        setInterval(loadTsCpu, 60000);
        setInterval(loadTsMem, 60000);
        setInterval(loadTsDisk, 60000);
        setInterval(loadTsTemp, 60000);
    }
    document.addEventListener('page:enter', (event) => {
        if(event.detail.page === 'dashboard') {
            window.App.logger.debug('[DASHBOARD.JS] page:enter dashboard!');
            onEnterDashboard();
        }
    });
    if (window.location.pathname === '/' || window.location.pathname === '/dashboard') {
        document.dispatchEvent(new CustomEvent('page:enter', { detail: { page: 'dashboard', path: window.location.pathname } }));
    }
})();
