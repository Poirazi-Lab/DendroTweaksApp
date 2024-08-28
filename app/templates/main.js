window.onload = function() {
    console.log("The page has been loaded.");
}


document.getElementById('toggle-button').addEventListener('click', function() {
    console.log('toggle');
    document.querySelector('.left-menu').classList.toggle('hidden');
});
