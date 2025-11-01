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
        window.App.logger.debug('[MONITORING.JS] onEnterMonitoring appelé, initialized=', initialized);
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
        }
        
        // Initialiser les liens de sélection de période
        setupTimeRangeLinks();
        
        // Toujours charger l'historique, même sans WS
            if(!historyLoaded && !historyLoading && !historyScheduled){
                historyScheduled = true;
            scheduleNonBlocking(() => {
                startHistoryLoadSequential();
                // Charger aussi le multi-séries CPU après un délai
                setTimeout(() => {
                    window.App.logger.debug('[MONITORING.JS] Appel fetchAndDrawCpuMulti après startHistoryLoadSequential');
                    const ac = new AbortController();
                    abortControllers.push(ac);
                    fetchAndDrawCpuMulti(ac.signal).catch((err) => {
                        window.App.logger.error('[MONITORING.JS] Erreur fetchAndDrawCpuMulti:', err);
                    });
                    // Démarrer la mise à jour automatique après le premier chargement
                    startAutoUpdate();
                }, 500);
            });
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

    // Récupère les heures sélectionnées depuis les liens cliquables
    function getSelectedHours(metric){
        const prefix = metric === 'cpu' ? 'cpu-time-range-link'
            : metric === 'memory' ? 'memory-time-range-link'
            : metric === 'disk' ? 'disk-time-range-link'
            : metric === 'temperature' ? 'temp-time-range-link'
            : 'temp-time-range-link';
        const links = document.querySelectorAll(`.${prefix}`);
        for(const link of links){
            if(link.getAttribute('data-selected') === 'true'){
                return parseInt(link.getAttribute('data-hours'), 10) || 24;
            }
        }
        return 24; // par défaut
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

        // Mapping spécial pour température (HTML utilise temp-chart, pas temperature-chart)
        let canvasId = metric === 'temperature' ? 'temp-chart' : metric+'-chart';
        let loadingId = metric === 'temperature' ? 'temp-chart-loading' : metric+'-chart-loading';
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
            if(!resp.ok){
                window.App.logger.warn(`[MONITORING.JS] HTTP ${resp.status} pour ${metric}`);
            }
            const json = await resp.json();
            const points = Array.isArray(json.points) ? json.points : [];
            window.App.logger.debug(`[MONITORING.JS] ${metric} points:`, points.length);
            
            // Toujours masquer le loading
            if(loading) loading.style.display = 'none';
            if(canvas) canvas.style.display = '';
            
            // Si canvas n'existe pas, logger l'erreur
            if(!canvas){
                window.App.logger.error(`[MONITORING.JS] Canvas ${canvasId} introuvable pour ${metric}`);
                return;
            }
            
            // Si pas de données, créer quand même un graphique vide
            let labels = [];
            let values = [];
            if(points.length > 0){
                labels = points.map(([ts,_v])=>{
                    try{ 
                        const tsNum = typeof ts === 'number' ? ts : parseInt(ts);
                        return new Date(tsNum).toISOString().slice(0,16).replace('T',' ');
                    }catch(_e){ 
                        window.App.logger.warn(`[MONITORING.JS] Erreur parsing timestamp ${ts}`, _e);
                        return ''; 
                    }
                });
                values = points.map(([_ts,v])=> {
                    const val = (v === null || v === undefined) ? null : Number(v);
                    return isNaN(val) ? null : val;
                });
                window.App.logger.debug(`[MONITORING.JS] ${metric} parsed: ${labels.length} labels, ${values.filter(v => v !== null).length} valeurs`);
            } else {
                // Créer quelques labels vides pour avoir un graphique vide visible
                labels = ['Aucune donnée'];
                values = [null];
                window.App.logger.debug(`[MONITORING.JS] ${metric} sans données, graphique vide créé`);
            }
            
            let chartObj = null;
            if(metric === 'cpu') chartObj = cpuChart;
            if(metric === 'memory') chartObj = memoryChart;
            if(metric === 'disk') chartObj = diskChart;
            if(metric === 'temperature') chartObj = tempChart;
            
            window.App.logger.debug(`[MONITORING.JS] ${metric} chartObj exists:`, chartObj !== null, 'canvas:', canvas !== null);
            if(!chartObj && canvas){
                ensureCanvasFree(canvas);
                try {
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
                            maintainAspectRatio:false,
                        animation:false,
                        plugins:{legend:{display:false}},
                            layout: {
                                padding: window.innerWidth < 768 ? {
                                    bottom: 15,
                                    top: 5,
                                    left: 5,
                                    right: 5
                                } : {
                                    bottom: 20,
                                    top: 10,
                                    left: 10,
                                    right: 10
                                }
                            },
                        scales:{
                                x:{
                                    display:true,
                                    ticks:{
                                        maxTicksLimit: window.innerWidth < 768 ? 4 : 8,
                                        autoSkip:true,
                                        font:{size: window.innerWidth < 768 ? 9 : 11},
                                        maxRotation: window.innerWidth < 768 ? 45 : 0,
                                        minRotation: window.innerWidth < 768 ? 45 : 0
                                    },
                                    grid:{display:true,color:'rgba(0,0,0,0.1)'}
                                },
                                y:{
                                    display:true,
                                    beginAtZero:true,
                                    suggestedMax: metric==='temperature'?100:100,
                                    ticks:{
                                        font:{size: window.innerWidth < 768 ? 9 : 11},
                                        maxTicksLimit: window.innerWidth < 768 ? 5 : 10
                                    },
                                    grid:{display:true,color:'rgba(0,0,0,0.1)'}
                                }
                        }
                    }
                });
                    window.App.logger.debug(`[MONITORING.JS] Graphique ${metric} créé avec succès`);
                if(metric==='cpu') cpuChart=chartObj;
                if(metric==='memory') memoryChart=chartObj;
                if(metric==='disk') diskChart=chartObj;
                if(metric==='temperature') tempChart=chartObj;
                } catch(chartErr){
                    window.App.logger.error(`[MONITORING.JS] Erreur création Chart.js pour ${metric}:`, chartErr);
                    if(loading) loading.style.display = 'none';
                    if(canvas) canvas.style.display = '';
                }
            } else if(chartObj){
                chartObj.data.labels = labels;
                chartObj.data.datasets[0].data = values;
                chartObj.update('none');
            }
        } catch(e){
            if (e?.name === 'AbortError') return; // navigation ou annulation
            window.App.logger.error(`[MONITORING.JS] fetchAndDrawHistory error ${metric}`, e);
            // Masquer le loading même en cas d'erreur
            if(loading) loading.style.display = 'none';
            if(canvas) canvas.style.display = '';
            // Créer un graphique vide en cas d'erreur
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
                        labels: ['Erreur'],
                        datasets: [{
                            label: yLabel || 'Erreur',
                            data: [null],
                            borderColor: metric==='temperature'?'#ef4444':metric==='memory'?'#9333ea':metric==='cpu'?'#fbbf24':'#3b82f6',
                            backgroundColor: 'rgba(0,0,0,0.04)',
                            pointRadius: 0,
                            tension: 0.2,
                            fill: true
                        }]
                    },
                    options: {
                        responsive:true,
                        maintainAspectRatio:false,
                        animation:false,
                        plugins:{legend:{display:false}},
                        layout: {
                            padding: window.innerWidth < 768 ? {
                                bottom: 15,
                                top: 5,
                                left: 5,
                                right: 5
                            } : {
                                bottom: 20,
                                top: 10,
                                left: 10,
                                right: 10
                            }
                        },
                        scales:{
                            x:{
                                display:true,
                                ticks:{
                                    maxTicksLimit: window.innerWidth < 768 ? 4 : 8,
                                    autoSkip:true,
                                    font:{size: window.innerWidth < 768 ? 9 : 11},
                                    maxRotation: window.innerWidth < 768 ? 45 : 0,
                                    minRotation: window.innerWidth < 768 ? 45 : 0
                                },
                                grid:{display:true,color:'rgba(0,0,0,0.1)'}
                            },
                            y:{
                                display:true,
                                beginAtZero:true,
                                suggestedMax: metric==='temperature'?100:100,
                                ticks:{
                                    font:{size: window.innerWidth < 768 ? 9 : 11},
                                    maxTicksLimit: window.innerWidth < 768 ? 5 : 10
                                },
                                grid:{display:true,color:'rgba(0,0,0,0.1)'}
                            }
                        }
                    }
                });
                if(metric==='cpu') cpuChart=chartObj;
                if(metric==='memory') memoryChart=chartObj;
                if(metric==='disk') diskChart=chartObj;
                if(metric==='temperature') tempChart=chartObj;
            }
        }
    }

    // Handlers de sélection de période (via liens cliquables)
    function setupTimeRangeLinks(){
        // CPU
        document.querySelectorAll('.cpu-time-range-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const hours = parseInt(link.getAttribute('data-hours'), 10);
                updateTimeRangeLinks('cpu', hours);
                const ac = new AbortController();
                abortControllers.push(ac);
                fetchAndDrawHistory('cpu', ac.signal).catch(()=>{});
            });
        });
        // Memory
        document.querySelectorAll('.memory-time-range-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const hours = parseInt(link.getAttribute('data-hours'), 10);
                updateTimeRangeLinks('memory', hours);
                const ac = new AbortController();
                abortControllers.push(ac);
                fetchAndDrawHistory('memory', ac.signal).catch(()=>{});
            });
        });
        // Disk
        document.querySelectorAll('.disk-time-range-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const hours = parseInt(link.getAttribute('data-hours'), 10);
                updateTimeRangeLinks('disk', hours);
                const ac = new AbortController();
                abortControllers.push(ac);
                fetchAndDrawHistory('disk', ac.signal).catch(()=>{});
            });
        });
        // Temperature
        document.querySelectorAll('.temp-time-range-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const hours = parseInt(link.getAttribute('data-hours'), 10);
                updateTimeRangeLinks('temperature', hours);
                const ac = new AbortController();
                abortControllers.push(ac);
                fetchAndDrawHistory('temperature', ac.signal).catch(()=>{});
            });
        });
        // CPU Multi
        document.querySelectorAll('.cpu-multi-time-range-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const hours = parseInt(link.getAttribute('data-hours'), 10);
                updateTimeRangeLinks('cpu-multi', hours);
                const ac = new AbortController();
                abortControllers.push(ac);
                fetchAndDrawCpuMulti(ac.signal).catch(()=>{});
            });
        });
    }

    // Mise à jour automatique de tous les graphiques
    let autoUpdateInterval = null;
    function startAutoUpdate(){
        if(autoUpdateInterval) return; // déjà démarré
        // Mise à jour toutes les 60 secondes
        autoUpdateInterval = setInterval(() => {
            if(cancelled) return;
            window.App.logger.debug('[MONITORING.JS] Mise à jour automatique des graphiques');
            // Mettre à jour tous les graphiques
            const ac1 = new AbortController();
            abortControllers.push(ac1);
            fetchAndDrawHistory('cpu', ac1.signal).catch(()=>{});
            
            const ac2 = new AbortController();
            abortControllers.push(ac2);
            fetchAndDrawHistory('memory', ac2.signal).catch(()=>{});
            
            const ac3 = new AbortController();
            abortControllers.push(ac3);
            fetchAndDrawHistory('disk', ac3.signal).catch(()=>{});
            
            const ac4 = new AbortController();
            abortControllers.push(ac4);
            fetchAndDrawHistory('temperature', ac4.signal).catch(()=>{});
            
            const ac5 = new AbortController();
            abortControllers.push(ac5);
            fetchAndDrawCpuMulti(ac5.signal).catch(()=>{});
        }, 60000); // 60 secondes
    }

    function stopAutoUpdate(){
        if(autoUpdateInterval){
            clearInterval(autoUpdateInterval);
            autoUpdateInterval = null;
        }
    }

    // CPU multi-séries via /api/ts/mrange
    function getSelectedHoursMulti(){
        const links = document.querySelectorAll('.cpu-multi-time-range-link');
        for(const link of links){
            if(link.getAttribute('data-selected') === 'true'){
                return parseInt(link.getAttribute('data-hours'), 10) || 24;
            }
        }
        return 24; // par défaut
    }

    // Met à jour l'état visuel des liens de sélection de période
    function updateTimeRangeLinks(metric, selectedHours){
        const prefix = metric === 'cpu' ? 'cpu-time-range-link'
            : metric === 'memory' ? 'memory-time-range-link'
            : metric === 'disk' ? 'disk-time-range-link'
            : metric === 'temperature' ? 'temp-time-range-link'
            : metric === 'cpu-multi' ? 'cpu-multi-time-range-link'
            : 'temp-time-range-link';
        const links = document.querySelectorAll(`.${prefix}`);
        links.forEach(link => {
            const hours = parseInt(link.getAttribute('data-hours'), 10);
            if(hours === selectedHours){
                link.setAttribute('data-selected', 'true');
                link.classList.add('bg-blue-100', 'border-blue-300');
                link.classList.remove('bg-gray-100', 'border-gray-300');
            } else {
                link.setAttribute('data-selected', 'false');
                link.classList.remove('bg-blue-100', 'border-blue-300');
            }
        });
    }

    async function fetchAndDrawCpuMulti(signal){
        window.App.logger.debug('[MONITORING.JS] fetchAndDrawCpuMulti appelé');
        const hours = getSelectedHoursMulti();
        const now = Date.now();
        const frm = now - (hours * 60 * 60 * 1000);
        const bucket = pickBucketMs(hours);
        window.App.logger.debug(`[MONITORING.JS] MRANGE params: hours=${hours}, frm=${frm}, to=${now}, bucket=${bucket}`);
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
        window.App.logger.debug(`[MONITORING.JS] canvas cpu-multi-chart existe:`, canvas !== null, 'loading existe:', loading !== null);
        if(loading) loading.style.display = '';
        if(canvas) canvas.style.display = 'none';
        try{
            window.App.logger.debug(`[MONITORING.JS] fetch TS MRANGE cpu depuis ${apiUrl}`);
            const resp = await fetch(apiUrl, { signal });
            if(!resp.ok){
                window.App.logger.warn(`[MONITORING.JS] HTTP ${resp.status} pour MRANGE cpu`);
            }
            const json = await resp.json();
            window.App.logger.debug(`[MONITORING.JS] MRANGE response:`, json);
            const series = Array.isArray(json.series) ? json.series : [];
            window.App.logger.debug(`[MONITORING.JS] MRANGE trouvé ${series.length} séries`);
            if(json.error){
                window.App.logger.warn(`[MONITORING.JS] Erreur MRANGE:`, json.error);
            }

            // Toujours masquer le loading
            if(loading) loading.style.display = 'none';
            if(canvas) canvas.style.display = '';

            // Construire des labels communs à partir de la première série
            let labels = [];
            if(series.length > 0 && series[0].points && series[0].points.length > 0){
                const pts0 = series[0].points || [];
                labels = pts0.map(([ts,_])=>{
                    try{ return new Date(ts).toISOString().slice(0,16).replace('T',' ');}catch(_e){ return ''; }
                });
            } else {
                labels = ['Aucune donnée'];
            }

            // Build datasets par série (host différent)
            const palette = ['#fbbf24','#3b82f6','#10b981','#ef4444','#8b5cf6','#06b6d4','#f59e0b','#84cc16'];
            let datasets = [];
            if(series.length > 0){
                datasets = series.map((s,idx)=>{
                    window.App.logger.debug(`[MONITORING.JS] Série ${idx}: key=${s.key}, labels=`, s.labels, `points=${(s.points||[]).length}`);
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
            } else {
                window.App.logger.warn('[MONITORING.JS] Aucune série trouvée pour metric=cpu.usage avec MRANGE.');
                // Fallback: essayer de charger la série globale ts:cpu.usage en attendant
                try {
                    const globalKey = 'ts:cpu.usage';
                    const fallbackParams = new URLSearchParams({
                        key: globalKey,
                        frm: String(frm),
                        to: String(now),
                        agg: 'avg',
                        bucket_ms: String(bucket)
                    });
                    const fallbackResp = await fetch(`/api/ts/range?${fallbackParams.toString()}`, { signal });
                    if(fallbackResp.ok){
                        const fallbackJson = await fallbackResp.json();
                        const fallbackPoints = Array.isArray(fallbackJson.points) ? fallbackJson.points : [];
                        if(fallbackPoints.length > 0){
                            window.App.logger.debug(`[MONITORING.JS] Fallback: série globale trouvée avec ${fallbackPoints.length} points`);
                            const fallbackLabels = fallbackPoints.map(([ts,_])=>{
                                try{ return new Date(ts).toISOString().slice(0,16).replace('T',' ');}catch(_e){ return ''; }
                            });
                            const fallbackValues = fallbackPoints.map(([_ts,v])=> (v===null||v===undefined)?null:Number(v));
                            labels = fallbackLabels.length > 0 ? fallbackLabels : labels;
                            datasets = [{
                                label: 'CPU (global, séries par hôte en cours de création)',
                                data: fallbackValues,
                                borderColor: '#fbbf24',
                                backgroundColor: 'rgba(0,0,0,0.04)',
                                pointRadius: 0,
                                tension: 0.2,
                                fill: false
                            }];
                        } else {
                            throw new Error('Aucun point dans la série globale');
                        }
                    } else {
                        throw new Error(`HTTP ${fallbackResp.status}`);
                    }
                } catch(fallbackErr) {
                    window.App.logger.warn('[MONITORING.JS] Fallback échoué:', fallbackErr);
                    // Afficher un message informatif au lieu d'un graphique vide
                    datasets = [{
                        label: 'Aucune donnée (les séries par hôte seront créées lors de la prochaine collecte)',
                        data: [null],
                        borderColor: '#cccccc',
                        backgroundColor: 'rgba(0,0,0,0.04)',
                        pointRadius: 0,
                        tension: 0.2,
                        fill: false
                    }];
                }
            }

            if(!cpuMultiChart && canvas){
                ensureCanvasFree(canvas);
                cpuMultiChart = new Chart(canvas.getContext('2d'), {
                    type: 'line',
                    data: { labels, datasets },
                    options: {
                        responsive:true,
                        maintainAspectRatio:false,
                        animation:false,
                        plugins:{ legend:{ display:true, position:'bottom', labels:{font:{size: window.innerWidth < 768 ? 10 : 12}} } },
                        layout: {
                            padding: window.innerWidth < 768 ? {
                                bottom: 15,
                                top: 5,
                                left: 5,
                                right: 5
                            } : {
                                bottom: 20,
                                top: 10,
                                left: 10,
                                right: 10
                            }
                        },
                        scales:{
                            x:{
                                display:true,
                                ticks:{ 
                                    maxTicksLimit: window.innerWidth < 768 ? 4 : 8, 
                                    autoSkip:true, 
                                    font:{size: window.innerWidth < 768 ? 9 : 11},
                                    maxRotation: window.innerWidth < 768 ? 45 : 0,
                                    minRotation: window.innerWidth < 768 ? 45 : 0
                                },
                                grid:{display:true,color:'rgba(0,0,0,0.1)'}
                            },
                            y:{
                                display:true,
                                beginAtZero:true,
                                suggestedMax: 100,
                                ticks:{
                                    font:{size: window.innerWidth < 768 ? 9 : 11},
                                    maxTicksLimit: window.innerWidth < 768 ? 5 : 10
                                },
                                grid:{display:true,color:'rgba(0,0,0,0.1)'}
                            }
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
            // Masquer le loading même en cas d'erreur
            if(loading) loading.style.display = 'none';
            if(canvas) canvas.style.display = '';
            // Créer un graphique vide en cas d'erreur
            if(!cpuMultiChart && canvas){
                ensureCanvasFree(canvas);
                cpuMultiChart = new Chart(canvas.getContext('2d'), {
                    type: 'line',
                    data: { 
                        labels: ['Erreur'],
                        datasets: [{
                            label: 'Erreur',
                            data: [null],
                            borderColor: '#cccccc',
                            backgroundColor: 'rgba(0,0,0,0.04)',
                            pointRadius: 0,
                            tension: 0.2,
                            fill: false
                        }]
                    },
                    options: {
                        responsive:true,
                        maintainAspectRatio:false,
                        animation:false,
                        plugins:{ legend:{ display:true, position:'bottom', labels:{font:{size: window.innerWidth < 768 ? 10 : 12}} } },
                        layout: {
                            padding: window.innerWidth < 768 ? {
                                bottom: 15,
                                top: 5,
                                left: 5,
                                right: 5
                            } : {
                                bottom: 20,
                                top: 10,
                                left: 10,
                                right: 10
                            }
                        },
                        scales:{
                            x:{
                                display:true,
                                ticks:{ 
                                    maxTicksLimit: window.innerWidth < 768 ? 4 : 8, 
                                    autoSkip:true, 
                                    font:{size: window.innerWidth < 768 ? 9 : 11},
                                    maxRotation: window.innerWidth < 768 ? 45 : 0,
                                    minRotation: window.innerWidth < 768 ? 45 : 0
                                },
                                grid:{display:true,color:'rgba(0,0,0,0.1)'}
                            },
                            y:{
                                display:true,
                                beginAtZero:true,
                                suggestedMax: 100,
                                ticks:{
                                    font:{size: window.innerWidth < 768 ? 9 : 11},
                                    maxTicksLimit: window.innerWidth < 768 ? 5 : 10
                                },
                                grid:{display:true,color:'rgba(0,0,0,0.1)'}
                            }
                        }
                    }
                });
            }
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

    window.App.logger.debug('[MONITORING.JS] Script chargé, en attente de page:enter');
    document.addEventListener('page:enter', (event) => {
        window.App.logger.debug('[MONITORING.JS] page:enter reçu, detail=', event.detail);
        if(event.detail && event.detail.page === 'monitoring') {
            window.App.logger.debug('[MONITORING.JS] page:enter monitoring!');
            onEnterMonitoring();
            // NE PAS lancer tout de suite les XHR, on attend le premier WS puis on planifie
        } else {
            window.App.logger.debug('[MONITORING.JS] page:enter mais page !== monitoring, detail.page=', event.detail?.page);
        }
    });
    // Si on quitte la page monitoring, annule toutes les requêtes et nettoie l'état
    document.addEventListener('page:enter', (event) => {
        if (event.detail && event.detail.page !== 'monitoring') {
            cancelHistory();
            cleanupCharts();
            stopAutoUpdate();
        }
    });

    if(window.location.pathname === '/monitoring'){
        window.App.logger.debug('[MONITORING.JS] pathname === /monitoring, déclenchement page:enter');
        document.dispatchEvent(new CustomEvent('page:enter', { detail: { page: 'monitoring', path: window.location.pathname } }));
    } else {
        window.App.logger.debug('[MONITORING.JS] pathname !== /monitoring:', window.location.pathname);
    }

    // Redimensionner les graphiques quand la fenêtre change
    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            if(cpuChart) cpuChart.resize();
            if(memoryChart) memoryChart.resize();
            if(diskChart) diskChart.resize();
            if(tempChart) tempChart.resize();
            if(cpuMultiChart) cpuMultiChart.resize();
        }, 250);
    });
})();
