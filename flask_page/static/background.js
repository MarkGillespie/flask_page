function getBackground(){
    var background_data = g_backgrounds[Math.floor(Math.random() * g_backgrounds.length)];
    var background = "url(\"" +background_data["url"] +"\")";
    document.body.style.backgroundImage = background;
}