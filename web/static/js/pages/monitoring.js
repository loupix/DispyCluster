// monitoring.js
(function() {
    let initialized = false;
    let cpuChart = null;
    let memoryChart = null;
    let diskChart = null;
    let tempChart = null;

    // Flags pour contrôler le flux et éviter l'interférence WS/XHR
    let historyLoading = false;
    let historyLoaded = false;
    let historyScheduled = false;
    let cancelled = false;
    let abortControllers = [];

    function ensureCanvasFree(canvas){
        if(!canvas) return;
        try{
            const existing = Chart.getChart(canvas);
            if(existing) existing.destroy();
        }catch(_e){}
    }

    function cleanupCharts(){
        try{ if(cpuChart){ cpuChart.destroy(); cpuChart=null; } }catch(_e){}
        try{ if(memoryChart){ memoryChart.destroy(); memoryChart=null; } }catch(_e){}
        try{ if(diskChart){ diskChart.destroy(); diskChart=null; } }catch(_e){}
        try{ if(tempChart){ tempChart.destroy(); tempChart=null; } }catch(_e){}
    }

    function onEnterMonitoring() {
        if (initialized) return;
        initialized = true;
        window.App.logger.debug('[MONITORING.JS] onEnterMonitoring : listeners setup');
        cancelled = false;

        // 1) Écoute WS pour MAJ tuiles immédiatement (léger)
        document.addEventListener('app:cluster_metrics', (event) => {
            window.App.logger.debug('[MONITORING.JS] EVENT app:cluster_metrics', event.detail);
            updateClusterHeader(event.detail);
            // 2) Planifier le chargement historique après le premier WS
            if(!historyLoaded && !historyLoading && !historyScheduled){
                historyScheduled = true;
                scheduleNonBlocking(() => startHistoryLoadSequential());
            }
        });

        document.addEventListener('app:alerts_update', (event) => {
            window.App.logger.debug('[MONITORING.JS] EVENT app:alerts_update', event.detail);
            updateAlerts(event.detail);
        });

        // Rendu immédiat depuis state ou cache
        let firstCluster = null;
        if (window.App && window.App.state && window.App.state.lastClusterMetrics) {
            firstCluster = window.App.state.lastClusterMetrics;
        } else if (window.App && window.App.cache) {
            firstCluster = window.App.cache.load(window.App.cache.keys.cluster);
        }
        if(firstCluster){
            updateClusterHeader(firstCluster);
            if(!historyLoaded && !historyLoading && !historyScheduled){
                historyScheduled = true;
                scheduleNonBlocking(() => startHistoryLoadSequential());
            }
        }
    }

    // MAJ des tuiles uniquement (pas les charts, pour éviter le thrash)
    function updateClusterHeader(data) {
        if(!data || !data.cluster_stats) return;
        const nodesOnline = document.getElementById('online-nodes');
        const avgCpu = document.getElementById('avg-cpu');
        const avgMem = document.getElementById('avg-memory');
        const avgTemp = document.getElementById('avg-temperature');
        if(nodesOnline) nodesOnline.textContent = data.cluster_stats.online_nodes ?? '-';
        if(avgCpu && data.cluster_stats.avg_cpu !== undefined) avgCpu.textContent = data.cluster_stats.avg_cpu.toFixed(1) + '%';
        if(avgMem && data.cluster_stats.avg_memory !== undefined) avgMem.textContent = data.cluster_stats.avg_memory.toFixed(1) + '%';
        if(avgTemp && data.cluster_stats.avg_temperature !== undefined) avgTemp.textContent = data.cluster_stats.avg_temperature.toFixed(1) + '°C';
    }

    // Démarre un chargement historique non-bloquant et annulable
    function startHistoryLoadSequential(){
        historyLoading = true;
        const queue = ['cpu','memory','disk','temperature'];
        let idx = 0;
        const step = () => {
            if (cancelled) { finishHistory(); return; }
            if (idx >= queue.length) { historyLoaded = true; finishHistory(); return; }
            const metric = queue[idx++];
            const ac = new AbortController();
            abortControllers.push(ac);
            fetchAndDrawHistory(metric, ac.signal)
                .catch((e)=>{
                    if (e?.name !== 'AbortError') window.App.logger.error('[MONITORING.JS] fetch metric error', metric, e);
                })
                .finally(() => {
                    // enchaîne la prochaine étape au repos du thread
                    scheduleNonBlocking(step);
                });
        };
        scheduleNonBlocking(step);
    }
    function finishHistory(){
        historyLoading = false;
        // purge les controllers consommés
        abortControllers = abortControllers.filter(c => !c.signal.aborted);
    }
    function cancelHistory(){
        cancelled = true;
        historyScheduled = false;
        historyLoading = false;
        try{ abortControllers.forEach(c=>{ try{ c.abort(); }catch(_e){} }); }catch(_e){}
        abortControllers = [];
    }
    function scheduleNonBlocking(fn){
        if (window.requestIdleCallback) {
            try { return window.requestIdleCallback(fn, { timeout: 300 }); } catch(_e){}
        }
        setTimeout(fn, 0);
    }

    // Chargement historique (évolution moyenne)
    async function fetchAndDrawHistory(metric, signal) {
        let apiUrl = `/api/graphs/${metric}-history?hours=24&interval_minutes=10`;
        let canvasId = metric+'-chart';
        let loadingId = metric+'-chart-loading';
        let yLabel = '';
        let dataKey = '';
        switch(metric){
            case 'cpu':
                yLabel = 'CPU (%)';
                dataKey = 'avg_cpu';
                break;
            case 'memory':
                yLabel = 'Mémoire (%)';
                dataKey = 'avg_memory';
                break;
            case 'disk':
                yLabel = 'Disque (%)';
                dataKey = 'avg_disk';
                break;
            case 'temperature':
                yLabel = 'Température (°C)';
                dataKey = 'avg_temperature';
                break;
        }
        const canvas = document.getElementById(canvasId);
        const loading = document.getElementById(loadingId);
        if(loading) loading.style.display = '';
        if(canvas) canvas.style.display = 'none';
        try {
            window.App.logger.debug(`[MONITORING.JS] fetch historique ${metric} depuis ${apiUrl}`);
            const resp = await fetch(apiUrl, { signal });
            const json = await resp.json();
            const history = Array.isArray(json.data) ? json.data : [];
            const labels = history.map(pt=>pt.timestamp.slice(0,16).replace('T',' '));
            const values = history.map(pt=>pt[dataKey] ?? null);
            if(loading) loading.style.display = 'none';
            if(canvas) canvas.style.display = '';
            let chartObj = null;
            if(metric === 'cpu') chartObj = cpuChart;
            if(metric === 'memory') chartObj = memoryChart;
            if(metric === 'disk') chartObj = diskChart;
            if(metric === 'temperature') chartObj = tempChart;
            if(!chartObj && canvas){
                ensureCanvasFree(canvas);
                chartObj = new Chart(canvas.getContext('2d'), {
                    type: 'line',
                    data: {
                        labels,
                        datasets: [{
                            label: yLabel,
                            data: values,
                            borderColor: metric==='temperature'?'#ef4444':metric==='memory'?'#9333ea':metric==='cpu'?'#fbbf24':'#3b82f6',
                            backgroundColor: 'rgba(0,0,0,0.04)',
                            pointRadius: 0,
                            tension: 0.2,
                            fill: true
                        }]
                    },
                    options: {
                        responsive:true,
                        animation:false,
                        plugins:{legend:{display:false}},
                        scales:{
                            x:{ticks:{maxTicksLimit:8,autoSkip:true}},
                            y:{beginAtZero:true,suggestedMax: metric==='temperature'?100:100}
                        }
                    }
                });
                if(metric==='cpu') cpuChart=chartObj;
                if(metric==='memory') memoryChart=chartObj;
                if(metric==='disk') diskChart=chartObj;
                if(metric==='temperature') tempChart=chartObj;
            } else if(chartObj){
                chartObj.data.labels = labels;
                chartObj.data.datasets[0].data = values;
                chartObj.update('none');
            }
        } catch(e){
            if (e?.name === 'AbortError') return; // navigation ou annulation
            window.App.logger.error(`[MONITORING.JS] fetchAndDrawHistory error ${metric}`, e);
        }
    }

    function updateAlerts(alerts) {
        // À compléter selon besoins (ex : afficher dans un bloc id="alerts-content").
    }

    document.addEventListener('page:enter', (event) => {
        if(event.detail.page === 'monitoring') {
            window.App.logger.debug('[MONITORING.JS] page:enter monitoring!');
            onEnterMonitoring();
            // NE PAS lancer tout de suite les XHR, on attend le premier WS puis on planifie
        }
    });
    // Si on quitte la page monitoring, annule toutes les requêtes et nettoie l'état
    document.addEventListener('page:enter', (event) => {
        if (event.detail.page !== 'monitoring') {
            cancelHistory();
            cleanupCharts();
        }
    });

    if(window.location.pathname === '/monitoring'){
        document.dispatchEvent(new CustomEvent('page:enter', { detail: { page: 'monitoring', path: window.location.pathname } }));
    }
})();
