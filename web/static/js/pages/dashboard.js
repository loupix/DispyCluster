// dashboard.js
(function() {
    let initialized = false;

    function updateFromOverview(overview) {
        console.log('[DASHBOARD.JS] updateFromOverview', overview);
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
        console.log('[DASHBOARD.JS] updateNodesList', overview);
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
        console.log('[DASHBOARD.JS] updateTops', nodes);
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
        console.log('[DASHBOARD.JS] updateAlerts', alerts);
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
        console.log('[DASHBOARD.JS] onEnterDashboard : listeners setup');
        document.addEventListener('app:cluster_metrics', (event) => {
            console.log('[DASHBOARD.JS] EVENT app:cluster_metrics', event.detail);
            updateFromOverview(event.detail);
            updateNodesList(event.detail);
        });
        document.addEventListener('app:alerts_update', (event) => {
            console.log('[DASHBOARD.JS] EVENT app:alerts_update', event.detail);
            updateAlerts(event.detail);
        });
        // Afficher direct les dernières valeurs si dispo
        if(window.App && window.App.state.lastClusterMetrics) {
            console.log('[DASHBOARD.JS] FIRST DATA IMMEDIATE', window.App.state.lastClusterMetrics);
            updateFromOverview(window.App.state.lastClusterMetrics);
            updateNodesList(window.App.state.lastClusterMetrics);
        }
        if(window.App && window.App.state.lastAlerts)
            updateAlerts(window.App.state.lastAlerts);
    }
    document.addEventListener('page:enter', (event) => {
        if(event.detail.page === 'dashboard') {
            console.log('[DASHBOARD.JS] page:enter dashboard!');
            onEnterDashboard();
        }
    });
    if (window.location.pathname === '/' || window.location.pathname === '/dashboard') {
        document.dispatchEvent(new CustomEvent('page:enter', { detail: { page: 'dashboard', path: window.location.pathname } }));
    }
})();
