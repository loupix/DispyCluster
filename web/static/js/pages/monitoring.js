// monitoring.js
(function() {
    let initialized = false;
    let cpuChart = null;
    let memoryChart = null;
    let diskChart = null;
    let tempChart = null;
    let cpuMultiChart = null;

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
        try{ if(cpuMultiChart){ cpuMultiChart.destroy(); cpuMultiChart=null; } }catch(_e){}
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

    // Mapping métrique -> clé TS
    function metricToTsKey(metric){
        if(metric === 'cpu') return 'ts:cpu.usage';
        if(metric === 'memory') return 'ts:memory.usage';
        if(metric === 'disk') return 'ts:disk.usage';
        if(metric === 'temperature') return 'ts:temperature';
        return `ts:${metric}`;
    }

    // Bucket par plage (ms)
    function pickBucketMs(hours){
        // 1h -> 1m, 6h -> 5m, 24h -> 10m, 168h -> 60m
        if(hours <= 1) return 60000;
        if(hours <= 6) return 300000;
        if(hours <= 24) return 600000;
        return 3600000;
    }

    function getSelectedHours(metric){
        const id = metric === 'cpu' ? 'cpu-time-range'
            : metric === 'memory' ? 'memory-time-range'
            : metric === 'disk' ? 'disk-time-range'
            : 'temp-time-range';
        const el = document.getElementById(id);
        const v = el ? parseInt(el.value, 10) : 24;
        return isNaN(v) ? 24 : v;
    }

    // Chargement historique via /api/ts/range
    async function fetchAndDrawHistory(metric, signal) {
        const hours = getSelectedHours(metric);
        const now = Date.now();
        const frm = now - (hours * 60 * 60 * 1000);
        const bucket = pickBucketMs(hours);
        const key = metricToTsKey(metric);
        const params = new URLSearchParams({
            key,
            frm: String(frm),
            to: String(now),
            agg: 'avg',
            bucket_ms: String(bucket)
        });
        const apiUrl = `/api/ts/range?${params.toString()}`;

        let canvasId = metric+'-chart';
        let loadingId = metric+'-chart-loading';
        let yLabel = '';
        switch(metric){
            case 'cpu':
                yLabel = 'CPU (%)';
                break;
            case 'memory':
                yLabel = 'Mémoire (%)';
                break;
            case 'disk':
                yLabel = 'Disque (%)';
                break;
            case 'temperature':
                yLabel = 'Température (°C)';
                break;
        }
        const canvas = document.getElementById(canvasId);
        const loading = document.getElementById(loadingId);
        if(loading) loading.style.display = '';
        if(canvas) canvas.style.display = 'none';
        try {
            window.App.logger.debug(`[MONITORING.JS] fetch TS ${metric} depuis ${apiUrl}`);
            const resp = await fetch(apiUrl, { signal });
            const json = await resp.json();
            const points = Array.isArray(json.points) ? json.points : [];
            const labels = points.map(([ts,_v])=>{
                try{ return new Date(ts).toISOString().slice(0,16).replace('T',' ');}catch(_e){ return ''; }
            });
            const values = points.map(([_ts,v])=> (v === null || v === undefined) ? null : Number(v));
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

    // Handlers de sélection de période
    window.updateCpuChart = function(){
        const ac = new AbortController();
        abortControllers.push(ac);
        fetchAndDrawHistory('cpu', ac.signal).catch(()=>{});
    }
    window.updateMemoryChart = function(){
        const ac = new AbortController();
        abortControllers.push(ac);
        fetchAndDrawHistory('memory', ac.signal).catch(()=>{});
    }
    window.updateDiskChart = function(){
        const ac = new AbortController();
        abortControllers.push(ac);
        fetchAndDrawHistory('disk', ac.signal).catch(()=>{});
    }
    window.updateTempChart = function(){
        const ac = new AbortController();
        abortControllers.push(ac);
        fetchAndDrawHistory('temperature', ac.signal).catch(()=>{});
    }

    // CPU multi-séries via /api/ts/mrange
    function getSelectedHoursMulti(){
        const el = document.getElementById('cpu-multi-time-range');
        const v = el ? parseInt(el.value, 10) : 24;
        return isNaN(v) ? 24 : v;
    }

    async function fetchAndDrawCpuMulti(signal){
        const hours = getSelectedHoursMulti();
        const now = Date.now();
        const frm = now - (hours * 60 * 60 * 1000);
        const bucket = pickBucketMs(hours);
        const params = new URLSearchParams({
            frm: String(frm),
            to: String(now),
            agg: 'avg',
            bucket_ms: String(bucket)
        });
        // filtre principal: metric=cpu.usage (labels ajoutés côté TS)
        // NOTE: on laisse le backend renvoyer toutes les séries (par hôte)
        params.append('filters', 'metric=cpu.usage');

        const apiUrl = `/api/ts/mrange?${params.toString()}`;
        const canvas = document.getElementById('cpu-multi-chart');
        const loading = document.getElementById('cpu-multi-chart-loading');
        if(loading) loading.style.display = '';
        if(canvas) canvas.style.display = 'none';
        try{
            window.App.logger.debug(`[MONITORING.JS] fetch TS MRANGE cpu depuis ${apiUrl}`);
            const resp = await fetch(apiUrl, { signal });
            const json = await resp.json();
            const series = Array.isArray(json.series) ? json.series : [];

            // Construire des labels communs à partir de la première série
            let labels = [];
            if(series.length > 0){
                const pts0 = series[0].points || [];
                labels = pts0.map(([ts,_])=>{
                    try{ return new Date(ts).toISOString().slice(0,16).replace('T',' ');}catch(_e){ return ''; }
                });
            }

            // Build datasets par série (host différent)
            const palette = ['#fbbf24','#3b82f6','#10b981','#ef4444','#8b5cf6','#06b6d4','#f59e0b','#84cc16'];
            const datasets = series.map((s,idx)=>{
                const label = s.labels && s.labels.host ? s.labels.host : s.key || `serie_${idx+1}`;
                const values = (s.points||[]).map(([_ts,v])=> (v===null||v===undefined)?null:Number(v));
                return {
                    label,
                    data: values,
                    borderColor: palette[idx % palette.length],
                    backgroundColor: 'rgba(0,0,0,0.04)',
                    pointRadius: 0,
                    tension: 0.2,
                    fill: false
                };
            });

            if(loading) loading.style.display = 'none';
            if(canvas) canvas.style.display = '';
            if(!cpuMultiChart && canvas){
                ensureCanvasFree(canvas);
                cpuMultiChart = new Chart(canvas.getContext('2d'), {
                    type: 'line',
                    data: { labels, datasets },
                    options: {
                        responsive:true,
                        animation:false,
                        plugins:{ legend:{ display:true, position:'bottom' } },
                        scales:{
                            x:{ ticks:{ maxTicksLimit:8, autoSkip:true } },
                            y:{ beginAtZero:true, suggestedMax: 100 }
                        }
                    }
                });
            } else if(cpuMultiChart){
                cpuMultiChart.data.labels = labels;
                cpuMultiChart.data.datasets = datasets;
                cpuMultiChart.update('none');
            }
        }catch(e){
            if (e?.name === 'AbortError') return;
            window.App.logger.error('[MONITORING.JS] fetchAndDrawCpuMulti error', e);
        }
    }

    window.updateCpuMultiChart = function(){
        const ac = new AbortController();
        abortControllers.push(ac);
        fetchAndDrawCpuMulti(ac.signal).catch(()=>{});
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
