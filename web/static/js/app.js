console.log('[App.js] INIT App');
// App global singleton: sockets + state partagé
window.App = window.App || {
    state: {
        lastClusterMetrics: null,
        lastHealth: null,
        lastAlerts: null,
    },
    sockets: {
        root: null,
        monitoring: null,
        health: null,
    },
    initSockets() {
        try {
            if (!this.sockets.root) {
                this.sockets.root = io({
                    transports: ['websocket', 'polling'],
                    reconnection: true,
                    reconnectionDelay: 1000,
                    reconnectionDelayMax: 5000,
                    reconnectionAttempts: Infinity
                });
                this.sockets.root.on('connect', () => console.log('[App.js] SOCKET ROOT CONNECT'));
                this.sockets.root.on('redis_cluster_metrics', (data) => {
                    console.log('[App.js] EVENT redis_cluster_metrics RECU', data);
                    this.state.lastClusterMetrics = data;
                    document.dispatchEvent(new CustomEvent('app:cluster_metrics', { detail: data }));
                });
                // Ecouter aussi 'cluster_metrics' sur le root (global) pour tolérance backend
                this.sockets.root.on('cluster_metrics', (data) => {
                    console.log('[App.js] EVENT cluster_metrics RECU', data);
                    this.state.lastClusterMetrics = data;
                    document.dispatchEvent(new CustomEvent('app:cluster_metrics', { detail: data }));
                });
            }
            if (!this.sockets.monitoring) {
                this.sockets.monitoring = io('/monitoring');
                this.sockets.monitoring.on('connect', () => console.log('[App.js] SOCKET MONITORING CONNECT'));
                // Ecoute cluster_metrics sur monitoring
                this.sockets.monitoring.on('cluster_metrics', (data) => {
                    console.log('[App.js] EVENT cluster_metrics (monitoring) RECU', data);
                    this.state.lastClusterMetrics = data;
                    document.dispatchEvent(new CustomEvent('app:cluster_metrics', { detail: data }));
                });
                this.sockets.monitoring.on('alerts_update', (data) => {
                    console.log('[App.js] EVENT alerts_update (monitoring) RECU', data);
                    this.state.lastAlerts = data;
                    document.dispatchEvent(new CustomEvent('app:alerts_update', { detail: data }));
                });
            }
            if (!this.sockets.health) {
                this.sockets.health = io('/health');
                this.sockets.health.on('connect', () => console.log('[App.js] SOCKET HEALTH CONNECT'));
                this.sockets.health.on('health_update', (data) => {
                    console.log('[App.js] EVENT health_update RECU', data);
                    this.state.lastHealth = data;
                    document.dispatchEvent(new CustomEvent('app:health_update', { detail: data }));
                });
            }
        } catch (e) {
            console.error('[App.js] Init sockets error', e);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    console.log('[App.js] DOMContentLoaded => initSockets');
    window.App.initSockets();
});