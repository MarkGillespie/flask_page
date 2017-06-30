function getBackground() {
    var background_data = g_backgrounds[Math.floor(Math.random() * g_backgrounds.length)];
    var background = "url(\"" + background_data["url"] +"\")";

    var image = new Image();
    image.onload = function () {
        document.body.style.backgroundImage = "url(\"" +background_data["url"] +"\")";
        document.getElementById("background").className += ' fadeOut';
    }
    image.src = background_data["url"];    
}