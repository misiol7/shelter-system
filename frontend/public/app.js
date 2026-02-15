const dogsEl=document.getElementById('dogs');const wsEl=document.getElementById('ws');
async function load(){const r=await fetch('/api/dogs');const dogs=await r.json();dogsEl.innerHTML='';
dogs.forEach(d=>{const div=document.createElement('div');div.className='card '+(d.status==='walking'?'walk':'cage');
div.innerHTML='<h3>'+d.name+'</h3><p>'+(d.status==='walking'?'Na spacerze':'W klatce')+'</p>';dogsEl.appendChild(div);});}
function connect(){const proto=location.protocol==='https:'?'wss':'ws';
const ws=new WebSocket(proto+'://'+location.host+'/ws');
ws.onopen=()=>wsEl.textContent='ONLINE';
ws.onclose=()=>{wsEl.textContent='OFFLINE';setTimeout(connect,2000);};
ws.onmessage=()=>load();}
load();connect();
