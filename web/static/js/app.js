// Logger simple et configurable
window.App = window.App || {};
if (!window.App.logger) {
    window.App.logger = (function() {
        const enabled = localStorage.getItem('dc:logger:enabled') === 'true';
        const levels = { DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3 };
        let currentLevel = levels.DEBUG;
        
        function shouldLog(level) {
            if (!enabled) return false;
            return level >= currentLevel;
        }
        
        return {
            enable() { localStorage.setItem('dc:logger:enabled', 'true'); },
            disable() { localStorage.setItem('dc:logger:enabled', 'false'); },
            setLevel(level) { currentLevel = levels[level] ?? levels.DEBUG; },
            debug(...args) { if (shouldLog(levels.DEBUG)) console.log('[DEBUG]', ...args); },
            info(...args) { if (shouldLog(levels.INFO)) console.log('[INFO]', ...args); },
            warn(...args) { if (shouldLog(levels.WARN)) console.warn('[WARN]', ...args); },
            error(...args) { if (shouldLog(levels.ERROR)) console.error('[ERROR]', ...args); }
        };
    })();
}

// Espace global App et cache persistant encapsulé (évite redéclarations)
window.App.cache = window.App.cache || (function(){
    const keys = {
        cluster: 'dc:lastClusterMetrics',
        health: 'dc:lastHealth',
        alerts: 'dc:lastAlerts'
    };
    const TTL = 60000; // 60s : assez frais pour le premier rendu
    function save(key, payload){
        try{ localStorage.setItem(key, JSON.stringify({ t: Date.now(), v: payload })); }catch(_e){}
    }
    function load(key){
        try{
            const raw = localStorage.getItem(key);
            if(!raw) return null;
            const obj = JSON.parse(raw);
            if(!obj || typeof obj.t !== 'number') return null;
            if(Date.now() - obj.t > TTL) return null;
            return obj.v;
        }catch(_e){ return null; }
    }
    return { keys, TTL, save, load };
})();

// App global singleton: sockets + state partagé
if (!window.App.initSockets) {
    Object.assign(window.App, {
        state: window.App.state || {
            lastClusterMetrics: null,
            lastHealth: null,
            lastAlerts: null,
        },
        sockets: window.App.sockets || {
            root: null,
            monitoring: null,
            health: null,
        },
        initSockets() {
        try {
            // 0) Hydrate depuis cache pour affichage immédiat
            if (!this.state.lastClusterMetrics) {
                const cached = window.App.cache.load(window.App.cache.keys.cluster);
                if (cached) {
                    this.state.lastClusterMetrics = cached;
                    document.dispatchEvent(new CustomEvent('app:cluster_metrics', { detail: cached }));
                }
            }
            if (!this.state.lastHealth) {
                const cachedH = window.App.cache.load(window.App.cache.keys.health);
                if (cachedH) {
                    this.state.lastHealth = cachedH;
                    document.dispatchEvent(new CustomEvent('app:health_update', { detail: cachedH }));
                }
            }
            if (!this.state.lastAlerts) {
                const cachedA = window.App.cache.load(window.App.cache.keys.alerts);
                if (cachedA) {
                    this.state.lastAlerts = cachedA;
                    document.dispatchEvent(new CustomEvent('app:alerts_update', { detail: cachedA }));
                }
            }

            if (!this.sockets.root) {
                this.sockets.root = io({
                    transports: ['websocket', 'polling'],
                    reconnection: true,
                    reconnectionDelay: 1000,
                    reconnectionDelayMax: 5000,
                    reconnectionAttempts: Infinity
                });
                this.sockets.root.on('connect', () => window.App.logger.debug('[App.js] SOCKET ROOT CONNECT'));
                this.sockets.root.on('redis_cluster_metrics', (data) => {
                    window.App.logger.debug('[App.js] EVENT redis_cluster_metrics RECU', data);
                    this.state.lastClusterMetrics = data;
                    window.App.cache.save(window.App.cache.keys.cluster, data);
                    document.dispatchEvent(new CustomEvent('app:cluster_metrics', { detail: data }));
                });
                this.sockets.root.on('cluster_metrics', (data) => {
                    window.App.logger.debug('[App.js] EVENT cluster_metrics RECU', data);
                    this.state.lastClusterMetrics = data;
                    window.App.cache.save(window.App.cache.keys.cluster, data);
                    document.dispatchEvent(new CustomEvent('app:cluster_metrics', { detail: data }));
                });
            }
            if (!this.sockets.monitoring) {
                this.sockets.monitoring = io('/monitoring');
                this.sockets.monitoring.on('connect', () => window.App.logger.debug('[App.js] SOCKET MONITORING CONNECT'));
                this.sockets.monitoring.on('cluster_metrics', (data) => {
                    window.App.logger.debug('[App.js] EVENT cluster_metrics (monitoring) RECU', data);
                    this.state.lastClusterMetrics = data;
                    window.App.cache.save(window.App.cache.keys.cluster, data);
                    document.dispatchEvent(new CustomEvent('app:cluster_metrics', { detail: data }));
                });
                this.sockets.monitoring.on('alerts_update', (data) => {
                    window.App.logger.debug('[App.js] EVENT alerts_update (monitoring) RECU', data);
                    this.state.lastAlerts = data;
                    window.App.cache.save(window.App.cache.keys.alerts, data);
                    document.dispatchEvent(new CustomEvent('app:alerts_update', { detail: data }));
                });
            }
            if (!this.sockets.health) {
                this.sockets.health = io('/health');
                this.sockets.health.on('connect', () => window.App.logger.debug('[App.js] SOCKET HEALTH CONNECT'));
                this.sockets.health.on('health_update', (data) => {
                    window.App.logger.debug('[App.js] EVENT health_update RECU', data);
                    this.state.lastHealth = data;
                    window.App.cache.save(window.App.cache.keys.health, data);
                    document.dispatchEvent(new CustomEvent('app:health_update', { detail: data }));
                });
            }
        } catch (e) {
            window.App.logger.error('[App.js] Init sockets error', e);
        }
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    window.App.logger.debug('[App.js] DOMContentLoaded => initSockets');
    window.App.initSockets();
});