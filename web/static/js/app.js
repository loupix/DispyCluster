// Application JavaScript principale pour DispyCluster Web Interface

class DispyClusterApp {
    constructor() {
        this.config = {
            refreshInterval: 30000, // 30 secondes
            apiBaseUrl: '/api',
            wsUrl: 'ws://localhost:8085/ws'
        };
        
        this.state = {
            isConnected: false,
            lastUpdate: null,
            notifications: []
        };
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupWebSocket();
        this.startPeriodicRefresh();
        this.checkClusterStatus();
    }
    
    setupEventListeners() {
        // Gestion des notifications
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-dismiss="notification"]')) {
                this.dismissNotification(e.target.closest('.notification'));
            }
        });
        
        // Gestion du menu mobile
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-toggle="mobile-menu"]')) {
                this.toggleMobileMenu();
            }
        });
        
        // Fermer le menu mobile en cliquant à l'extérieur
        document.addEventListener('click', (e) => {
            const mobileMenu = document.getElementById('mobile-menu');
            if (mobileMenu && !mobileMenu.contains(e.target) && !e.target.matches('[data-toggle="mobile-menu"]')) {
                mobileMenu.classList.add('hidden');
            }
        });
    }
    
    setupWebSocket() {
        // WebSocket pour les mises à jour en temps réel
        try {
            this.ws = new WebSocket(this.config.wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connecté');
                this.state.isConnected = true;
            };
            
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket déconnecté');
                this.state.isConnected = false;
                // Tentative de reconnexion après 5 secondes
                setTimeout(() => this.setupWebSocket(), 5000);
            };
            
            this.ws.onerror = (error) => {
                console.error('Erreur WebSocket:', error);
            };
        } catch (error) {
            console.warn('WebSocket non disponible:', error);
        }
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'cluster_update':
                this.updateClusterStatus(data.payload);
                break;
            case 'job_update':
                this.updateJobStatus(data.payload);
                break;
            case 'node_update':
                this.updateNodeStatus(data.payload);
                break;
            case 'alert':
                this.showNotification(data.payload.message, data.payload.type);
                break;
        }
    }
    
    // API Helpers
    async apiRequest(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}${endpoint}`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`Erreur API ${endpoint}:`, error);
            throw error;
        }
    }
    
    // Gestion des notifications
    showNotification(message, type = 'info', duration = 5000) {
        const notification = this.createNotification(message, type);
        document.getElementById('notifications').appendChild(notification);
        
        // Animation d'entrée
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // Auto-suppression
        if (duration > 0) {
            setTimeout(() => {
                this.dismissNotification(notification);
            }, duration);
        }
        
        return notification;
    }
    
    createNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification fixed top-20 right-6 z-50 max-w-sm bg-white rounded-lg shadow-lg border-l-4 ${
            type === 'success' ? 'border-green-500' :
            type === 'error' ? 'border-red-500' :
            type === 'warning' ? 'border-yellow-500' :
            'border-blue-500'
        }`;
        
        notification.innerHTML = `
            <div class="p-4">
                <div class="flex items-start">
                    <div class="flex-shrink-0">
                        <i class="fas ${
                            type === 'success' ? 'fa-check-circle text-green-500' :
                            type === 'error' ? 'fa-times-circle text-red-500' :
                            type === 'warning' ? 'fa-exclamation-triangle text-yellow-500' :
                            'fa-info-circle text-blue-500'
                        }"></i>
                    </div>
                    <div class="ml-3 flex-1">
                        <p class="text-sm font-medium text-gray-900">${message}</p>
                    </div>
                    <div class="ml-4 flex-shrink-0">
                        <button data-dismiss="notification" class="text-gray-400 hover:text-gray-600">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        return notification;
    }
    
    dismissNotification(notification) {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }
    
    // Gestion du menu mobile
    toggleMobileMenu() {
        const menu = document.getElementById('mobile-menu');
        if (menu) {
            menu.classList.toggle('hidden');
        }
    }
    
    // Vérification du statut du cluster
    async checkClusterStatus() {
        try {
            const data = await this.apiRequest('/health');
            this.updateClusterStatusIndicator(data.status === 'healthy');
        } catch (error) {
            this.updateClusterStatusIndicator(false);
        }
    }
    
    updateClusterStatusIndicator(isHealthy) {
        const statusElement = document.getElementById('cluster-status');
        if (statusElement) {
            if (isHealthy) {
                statusElement.className = 'ml-2 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800';
                statusElement.innerHTML = '<i class="fas fa-circle mr-1"></i>En ligne';
            } else {
                statusElement.className = 'ml-2 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800';
                statusElement.innerHTML = '<i class="fas fa-circle mr-1"></i>Hors ligne';
            }
        }
    }
    
    // Mises à jour en temps réel
    updateClusterStatus(data) {
        // Mettre à jour l'interface selon les données reçues
        console.log('Mise à jour du cluster:', data);
    }
    
    updateJobStatus(data) {
        // Mettre à jour le statut des jobs
        console.log('Mise à jour du job:', data);
    }
    
    updateNodeStatus(data) {
        // Mettre à jour le statut des nœuds
        console.log('Mise à jour du nœud:', data);
    }
    
    // Rafraîchissement périodique
    startPeriodicRefresh() {
        setInterval(() => {
            this.checkClusterStatus();
            this.refreshCurrentPage();
        }, this.config.refreshInterval);
    }
    
    refreshCurrentPage() {
        // Rafraîchir la page actuelle selon le contexte
        const path = window.location.pathname;
        
        if (path === '/') {
            this.refreshDashboard();
        } else if (path === '/jobs') {
            this.refreshJobs();
        } else if (path === '/nodes') {
            this.refreshNodes();
        } else if (path === '/monitoring') {
            this.refreshMonitoring();
        }
    }
    
    // Méthodes de rafraîchissement par page
    refreshDashboard() {
        if (typeof loadDashboardData === 'function') {
            loadDashboardData();
        }
    }
    
    refreshJobs() {
        if (typeof loadJobs === 'function') {
            loadJobs();
        }
    }
    
    refreshNodes() {
        if (typeof loadNodes === 'function') {
            loadNodes();
        }
    }
    
    refreshMonitoring() {
        if (typeof loadMonitoringData === 'function') {
            loadMonitoringData();
        }
    }
    
    // Utilitaires
    formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
    
    formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    }
    
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('fr-FR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
    
    // Gestion des erreurs globales
    handleError(error, context = '') {
        console.error(`Erreur ${context}:`, error);
        this.showNotification(
            `Erreur ${context}: ${error.message || 'Erreur inconnue'}`,
            'error'
        );
    }
}

// Initialiser l'application
document.addEventListener('DOMContentLoaded', () => {
    window.app = new DispyClusterApp();
});

// Fonctions utilitaires globales
window.showNotification = (message, type = 'info') => {
    if (window.app) {
        window.app.showNotification(message, type);
    }
};

window.formatBytes = (bytes, decimals = 2) => {
    if (window.app) {
        return window.app.formatBytes(bytes, decimals);
    }
    return bytes;
};

window.formatDuration = (seconds) => {
    if (window.app) {
        return window.app.formatDuration(seconds);
    }
    return seconds;
};

window.formatDate = (dateString) => {
    if (window.app) {
        return window.app.formatDate(dateString);
    }
    return dateString;
};