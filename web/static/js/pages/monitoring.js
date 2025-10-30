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

    function onEnterMonitoring() {
        if (initialized) return;
        initialized = true;
        console.log('[MONITORING.JS] onEnterMonitoring : listeners setup');

        // 1) Écoute WS pour MAJ tuiles immédiatement (léger)
        document.addEventListener('app:cluster_metrics', (event) => {
            console.log('[MONITORING.JS] EVENT app:cluster_metrics', event.detail);
            updateClusterHeader(event.detail);
            // 2) Planifier le chargement historique après le premier WS
            if(!historyLoaded && !historyLoading && !historyScheduled){
                historyScheduled = true;
                setTimeout(() => {
                    startHistoryLoadSequential();
                }, 250); // petit délai pour laisser respirer le thread UI
            }
        });

        document.addEventListener('app:alerts_update', (event) => {
            console.log('[MONITORING.JS] EVENT app:alerts_update', event.detail);
            updateAlerts(event.detail);
        });

        // Si on a déjà des data en cache (rare mais possible), affiche les tuiles et planifie
        if(window.App && window.App.state.lastClusterMetrics) {
            updateClusterHeader(window.App.state.lastClusterMetrics);
            if(!historyLoaded && !historyLoading && !historyScheduled){
                historyScheduled = true;
                setTimeout(() => startHistoryLoadSequential(), 150);
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

    // Démarre un chargement historique SEQUENTIEL (évite 4 XHR simultanés)
    async function startHistoryLoadSequential(){
        historyLoading = true;
        try{
            const queue = ['cpu','memory','disk','temperature'];
            for(const metric of queue){
                await fetchAndDrawHistory(metric);
                // petite pause pour fluidité UI
                await new Promise(res=>setTimeout(res, 120));
            }
            historyLoaded = true;
        }catch(e){
            console.error('[MONITORING.JS] startHistoryLoadSequential error', e);
        }finally{
            historyLoading = false;
        }
    }

    // Chargement historique (évolution moyenne)
    async function fetchAndDrawHistory(metric) {
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
            console.log(`[MONITORING.JS] fetch historique ${metric} depuis ${apiUrl}`);
            const resp = await fetch(apiUrl);
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
            console.error(`[MONITORING.JS] fetchAndDrawHistory error ${metric}`, e)
        }
    }

    function updateAlerts(alerts) {
        // À compléter selon besoins (ex : afficher dans un bloc id="alerts-content").
    }

    document.addEventListener('page:enter', (event) => {
        if(event.detail.page === 'monitoring') {
            console.log('[MONITORING.JS] page:enter monitoring!');
            onEnterMonitoring();
            // NE PAS lancer tout de suite les XHR, on attend le premier WS puis on planifie
        }
    });

    if(window.location.pathname === '/monitoring'){
        document.dispatchEvent(new CustomEvent('page:enter', { detail: { page: 'monitoring', path: window.location.pathname } }));
    }
})();
