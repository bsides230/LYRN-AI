const v = document.getElementById('bgVideo');
const btn = document.getElementById('pauseVideo');
if (v && btn){
  btn.addEventListener('click', () => {
    if (v.paused){ v.play(); btn.textContent = 'Pause'; }
    else { v.pause(); btn.textContent = 'Play'; }
  });
}
