// Router minimal basé sur htmx: conserve sockets et déclenche page:enter
(function(){
    if (!window.htmx) return;

    // Après un swap htmx, déclencher un événement pour réinitialiser la page
    document.body.addEventListener('htmx:afterSwap', function(evt){
        // On ne cible que le conteneur principal
        const target = evt.detail && evt.detail.target;
        if (target && target.id === 'app-content') {
            document.dispatchEvent(new Event('page:enter'));
        }
    });

    // Optionnel: annuler scroll jump
    document.body.addEventListener('htmx:afterSettle', function(){
        // Placeholder pour futurs hooks
    });
})();


