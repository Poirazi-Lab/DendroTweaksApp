window.onload = function() {
    console.log("The page has been loaded.");
    console.log('Body min-width:', getComputedStyle(document.body).minWidth);
    console.log('App min-width:', getComputedStyle(document.querySelector('.app')).minWidth);

    document.getElementById('settings-button').addEventListener('click', function() {
        console.log('clicked');
        document.querySelector('.settings').classList.toggle('hidden');
    });
    
    document.querySelector('.settings').addEventListener('click', function(event) {
        if (event.target === this) {
            this.classList.toggle('hidden');
        }
    });

    document.getElementById('settings-close-button').addEventListener('click', function() {
        document.querySelector('.settings').classList.add('hidden');
    });
}


