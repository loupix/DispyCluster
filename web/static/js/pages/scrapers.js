// scrapers.js
(function() {
    let initialized = false;
    let currentJobId = null;
    let refreshInterval = null;

    async function loadStats() {
        try {
            const response = await fetch('/api/scrapers/stats');
            const stats = await response.json();
            
            if (stats.stats) {
                document.getElementById('stats-total').textContent = stats.stats.total_jobs || 0;
                document.getElementById('stats-active').textContent = stats.stats.active_jobs || 0;
                document.getElementById('stats-success-rate').textContent = 
                    (stats.stats.success_rate || 0).toFixed(1) + '%';
                document.getElementById('stats-queue').textContent = stats.queue_size || 0;
            }
        } catch (error) {
            window.App.logger.error('[SCRAPERS.JS] Erreur chargement stats:', error);
        }
    }

    async function loadScrapes(status = null) {
        try {
            const url = status 
                ? `/api/scrapers/history?status=${status}&limit=50`
                : '/api/scrapers/history?limit=50';
            
            const response = await fetch(url);
            const data = await response.json();
            
            const scrapes = data.history || [];
            document.getElementById('scrapes-count').textContent = `${scrapes.length} scraping${scrapes.length > 1 ? 's' : ''}`;
            
            const container = document.getElementById('scrapes-list');
            if (!container) return;
            
            if (scrapes.length === 0) {
                container.innerHTML = '<p class="text-gray-500 text-center py-8">Aucun scraping trouvé</p>';
                return;
            }
            
            container.innerHTML = scrapes.map(scrape => {
                const statusColors = {
                    'pending': 'bg-yellow-100 text-yellow-800',
                    'running': 'bg-blue-100 text-blue-800',
                    'completed': 'bg-green-100 text-green-800',
                    'failed': 'bg-red-100 text-red-800'
                };
                
                const statusIcons = {
                    'pending': 'fa-clock',
                    'running': 'fa-spinner fa-spin',
                    'completed': 'fa-check-circle',
                    'failed': 'fa-times-circle'
                };
                
                const statusLabels = {
                    'pending': 'En attente',
                    'running': 'En cours',
                    'completed': 'Terminé',
                    'failed': 'Échoué'
                };
                
                const status = scrape.status || 'pending';
                const progress = (scrape.progress || 0).toFixed(0);
                const createdAt = scrape.created_at 
                    ? new Date(scrape.created_at).toLocaleString('fr-FR')
                    : '-';
                
                return `
                    <div class="border border-gray-200 rounded-lg p-4 mb-4 hover:bg-gray-50 transition-colors">
                        <div class="flex items-center justify-between">
                            <div class="flex-1">
                                <div class="flex items-center space-x-3 mb-2">
                                    <span class="px-3 py-1 rounded-full text-xs font-medium ${statusColors[status] || statusColors.pending}">
                                        <i class="fas ${statusIcons[status] || statusIcons.pending} mr-1"></i>
                                        ${statusLabels[status] || status}
                                    </span>
                                    <span class="text-sm font-medium text-gray-900">${scrape.url || '-'}</span>
                                </div>
                                <div class="flex items-center space-x-4 text-sm text-gray-600">
                                    <span><i class="fas fa-calendar mr-1"></i>${createdAt}</span>
                                    ${scrape.max_pages ? `<span><i class="fas fa-file mr-1"></i>Max: ${scrape.max_pages} pages</span>` : ''}
                                    ${status === 'running' ? `<span><i class="fas fa-tasks mr-1"></i>${progress}%</span>` : ''}
                                    ${scrape.assigned_node ? `<span><i class="fas fa-server mr-1"></i>${scrape.assigned_node}</span>` : ''}
                                </div>
                            </div>
                            <div class="flex items-center space-x-2">
                                ${status === 'running' ? `
                                    <button onclick="cancelScrape('${scrape.job_id}')" 
                                            class="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded-lg">
                                        <i class="fas fa-stop mr-1"></i>Arrêter
                                    </button>
                                ` : ''}
                                <button onclick="showScrapeDetails('${scrape.job_id}')" 
                                        class="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded-lg">
                                    <i class="fas fa-eye mr-1"></i>Détails
                                </button>
                            </div>
                        </div>
                        ${status === 'running' ? `
                            <div class="mt-3">
                                <div class="w-full bg-gray-200 rounded-full h-2">
                                    <div class="bg-blue-600 h-2 rounded-full transition-all" style="width: ${progress}%"></div>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                `;
            }).join('');
            
        } catch (error) {
            window.App.logger.error('[SCRAPERS.JS] Erreur chargement scrapes:', error);
            const container = document.getElementById('scrapes-list');
            if (container) {
                container.innerHTML = '<p class="text-red-500 text-center py-8">Erreur lors du chargement</p>';
            }
        }
    }

    async function submitScrape(event) {
        event.preventDefault();
        
        const url = document.getElementById('scrape-url').value;
        const maxPages = parseInt(document.getElementById('scrape-max-pages').value) || 10;
        const timeout = parseInt(document.getElementById('scrape-timeout').value) || 10;
        const sameOrigin = document.getElementById('scrape-same-origin').checked;
        const priority = parseInt(document.getElementById('scrape-priority').value) || 1;
        
        try {
            const response = await fetch('/api/scrapers/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url,
                    max_pages: maxPages,
                    timeout_s: timeout,
                    same_origin_only: sameOrigin,
                    priority
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification('Scraping soumis avec succès', 'success');
                hideSubmitScrapeModal();
                document.getElementById('submit-scrape-form').reset();
                loadScrapes();
                loadStats();
            } else {
                showNotification(result.error || 'Erreur lors de la soumission', 'error');
            }
        } catch (error) {
            window.App.logger.error('[SCRAPERS.JS] Erreur soumission:', error);
            showNotification('Erreur de connexion', 'error');
        }
    }

    async function showScrapeDetails(jobId) {
        currentJobId = jobId;
        const modal = document.getElementById('scrape-details-modal');
        const content = document.getElementById('scrape-details-content');
        
        modal.classList.remove('hidden');
        content.innerHTML = '<div class="flex items-center justify-center py-12"><div class="loading"></div><span class="ml-3 text-gray-600">Chargement...</span></div>';
        
        try {
            const response = await fetch(`/api/scrapers/jobs/${jobId}/results`);
            const details = await response.json();
            
            if (details.error) {
                content.innerHTML = `<p class="text-red-500 text-center py-8">${details.error}</p>`;
                return;
            }
            
            const resultsByUrl = details.results_by_url || [];
            
            content.innerHTML = `
                <div class="space-y-6">
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="text-sm font-medium text-gray-700">URL</label>
                            <p class="text-gray-900 mt-1 break-all">${details.url || '-'}</p>
                        </div>
                        <div>
                            <label class="text-sm font-medium text-gray-700">Statut</label>
                            <p class="text-gray-900 mt-1">${details.status || '-'}</p>
                        </div>
                        <div>
                            <label class="text-sm font-medium text-gray-700">Pages max</label>
                            <p class="text-gray-900 mt-1">${details.max_pages || '-'}</p>
                        </div>
                        <div>
                            <label class="text-sm font-medium text-gray-700">URLs scrapées</label>
                            <p class="text-gray-900 mt-1">${details.total_urls_crawled || 0}</p>
                        </div>
                    </div>
                    
                    ${resultsByUrl.length > 0 ? `
                        <div>
                            <label class="text-sm font-medium text-gray-700 mb-2 block">Résultats par URL</label>
                            <div class="space-y-2 max-h-96 overflow-y-auto">
                                ${resultsByUrl.map(result => `
                                    <div class="border border-gray-200 rounded-lg p-4">
                                        <p class="font-medium text-gray-900 mb-2 break-all">${result.url}</p>
                                        ${result.emails && result.emails.length > 0 ? `
                                            <div class="mb-2">
                                                <span class="text-xs font-medium text-gray-600">Emails (${result.emails.length}):</span>
                                                <div class="mt-1 flex flex-wrap gap-1">
                                                    ${result.emails.map(email => `<span class="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">${email}</span>`).join('')}
                                                </div>
                                            </div>
                                        ` : ''}
                                        ${result.phones && result.phones.length > 0 ? `
                                            <div class="mb-2">
                                                <span class="text-xs font-medium text-gray-600">Téléphones (${result.phones.length}):</span>
                                                <div class="mt-1 flex flex-wrap gap-1">
                                                    ${result.phones.map(phone => `<span class="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">${phone}</span>`).join('')}
                                                </div>
                                            </div>
                                        ` : ''}
                                        ${result.error ? `
                                            <div class="mt-2">
                                                <span class="text-xs font-medium text-red-600">Erreur:</span>
                                                <p class="text-xs text-red-600 mt-1">${result.error}</p>
                                            </div>
                                        ` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : '<p class="text-gray-500 text-center py-4">Aucun résultat disponible</p>'}
                </div>
            `;
        } catch (error) {
            window.App.logger.error('[SCRAPERS.JS] Erreur détails:', error);
            content.innerHTML = '<p class="text-red-500 text-center py-8">Erreur lors du chargement</p>';
        }
    }

    async function cancelScrape(jobId) {
        if (!confirm('Voulez-vous vraiment annuler ce scraping ?')) return;
        
        try {
            const response = await fetch(`/api/scrapers/jobs/${jobId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification('Scraping annulé', 'success');
                loadScrapes();
                loadStats();
            } else {
                showNotification(result.error || 'Erreur lors de l\'annulation', 'error');
            }
        } catch (error) {
            window.App.logger.error('[SCRAPERS.JS] Erreur annulation:', error);
            showNotification('Erreur de connexion', 'error');
        }
    }

    function showSubmitScrapeModal() {
        document.getElementById('submit-scrape-modal').classList.remove('hidden');
    }

    function hideSubmitScrapeModal() {
        document.getElementById('submit-scrape-modal').classList.add('hidden');
    }

    function hideScrapeDetailsModal() {
        document.getElementById('scrape-details-modal').classList.add('hidden');
        currentJobId = null;
    }

    function filterScrapes() {
        const status = document.getElementById('status-filter').value;
        loadScrapes(status || null);
    }

    function refreshScrapes() {
        const status = document.getElementById('status-filter').value;
        loadScrapes(status || null);
        loadStats();
    }

    function onEnterScrapers() {
        if (initialized) return;
        initialized = true;
        
        window.App.logger.debug('[SCRAPERS.JS] onEnterScrapers : listeners setup');
        
        // Charger les données initiales
        loadStats();
        loadScrapes();
        
        // Écouter les événements WebSocket
        if (window.App && window.App.sockets && window.App.sockets.root) {
            window.App.sockets.root.on('scraper_job_submitted', (data) => {
                window.App.logger.debug('[SCRAPERS.JS] EVENT scraper_job_submitted', data);
                loadScrapes();
                loadStats();
                showNotification('Nouveau scraping soumis', 'info');
            });
            
            window.App.sockets.root.on('service_job_progress', (data) => {
                window.App.logger.debug('[SCRAPERS.JS] EVENT service_job_progress', data);
                if (data.data && data.data.service_name === 'scraper') {
                    loadScrapes();
                }
            });
            
            window.App.sockets.root.on('service_job_completed', (data) => {
                window.App.logger.debug('[SCRAPERS.JS] EVENT service_job_completed', data);
                if (data.data && data.data.service_name === 'scraper') {
                    loadScrapes();
                    loadStats();
                    showNotification('Scraping terminé', 'success');
                }
            });
            
            window.App.sockets.root.on('service_job_failed', (data) => {
                window.App.logger.debug('[SCRAPERS.JS] EVENT service_job_failed', data);
                if (data.data && data.data.service_name === 'scraper') {
                    loadScrapes();
                    loadStats();
                    showNotification('Scraping échoué', 'error');
                }
            });
        }
        
        // Rafraîchir périodiquement
        refreshInterval = setInterval(() => {
            loadStats();
            const status = document.getElementById('status-filter')?.value || null;
            loadScrapes(status);
        }, 5000);
    }

    function onLeaveScrapers() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
    }

    // Exposer les fonctions globales
    window.showSubmitScrapeModal = showSubmitScrapeModal;
    window.hideSubmitScrapeModal = hideSubmitScrapeModal;
    window.submitScrape = submitScrape;
    window.showScrapeDetails = showScrapeDetails;
    window.hideScrapeDetailsModal = hideScrapeDetailsModal;
    window.cancelScrape = cancelScrape;
    window.filterScrapes = filterScrapes;
    window.refreshScrapes = refreshScrapes;

    document.addEventListener('page:enter', (event) => {
        if (event.detail.page === 'scrapers') {
            window.App.logger.debug('[SCRAPERS.JS] page:enter scrapers!');
            onEnterScrapers();
        }
    });

    document.addEventListener('page:leave', (event) => {
        if (event.detail.page === 'scrapers') {
            onLeaveScrapers();
        }
    });

    if (window.location.pathname === '/scrapers') {
        document.dispatchEvent(new CustomEvent('page:enter', { 
            detail: { page: 'scrapers', path: window.location.pathname } 
        }));
    }
})();

