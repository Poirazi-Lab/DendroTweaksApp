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
        console.log('clicked');
        this.classList.toggle('hidden');
    }
    });
}



window.addEventListener('resize', function() {
    console.log('Window width:', window.innerWidth);
    console.log('Client width:', document.documentElement.clientWidth);
});

function toggleMenu() {
    const leftMenu = document.querySelector('.left-menu');
    leftMenu.classList.toggle('collapsed');
}

window.addEventListener('resize', function() {
    const leftMenu = document.querySelector('.left-menu');
    if (window.innerWidth > 1500) {
        console.log('Window is greater than 1000px');
        leftMenu.classList.remove('collapsed');
    }
});



