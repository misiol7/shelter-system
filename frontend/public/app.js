const app=document.getElementById("app");
let dogs=[];
let ws=null;
let reconnectTimer=null;
let wsState="OFFLINE";

function wsBadge(){
  return `<small class="status">WS: <span style="color:${wsState==="ONLINE"?"green":"red"}">${wsState}</span></small>`;
}
function color(d){
  if(!d.available) return "gray";
  if(d.status!=="WALKING") return "blue";
  if(d.daily_minutes>=90) return "red";
  if(d.daily_minutes>=60) return "orange";
  return "green";
}
async function loadDogs(){
  try{
    const r=await fetch("/api/dogs");
    dogs=await r.json();
    renderBoard();
  }catch(e){console.error(e);}
}
async function startWalk(id){await fetch(`/api/walk/start?dog_id=${id}`,{method:"POST"});}
async function stopWalk(id){await fetch(`/api/walk/stop?dog_id=${id}`,{method:"POST"});}

function renderBoard(){
  app.innerHTML=`<div class="header"><h2>🐾 Ewidencja spacerów ${wsBadge()}</h2><button class="btn" onclick="showAdmin()">Admin</button></div><div class="grid" id="grid"></div>`;
  const g=document.getElementById("grid");
  dogs.forEach(d=>{
    const c=document.createElement("div");
    c.className=`card ${color(d)}`;
    c.innerHTML=`<h3>${d.name}</h3><p>Status: ${d.status}</p><p>Dzisiaj: ${d.daily_minutes} min</p>${d.available?`<button class="btn" onclick="startWalk(${d.id})">START</button> <button class="btn" onclick="stopWalk(${d.id})">STOP</button>`:`<p>Niedostępny</p>`}`;
    g.appendChild(c);
  });
}
function showAdmin(){
  app.innerHTML=`<div class="panel"><h2>Admin</h2><p>Panel admina dostępny w pełnym buildzie. Ta wersja jest stabilną tablicą LIVE.</p><button class="btn" onclick="renderBoard()">← Powrót</button></div>`;
}

function connectWS(){
  ws=new WebSocket(`${location.protocol==="https:"?"wss":"ws"}://${location.host}/ws`);
  ws.onopen=()=>{wsState="ONLINE";renderBoard();};
  ws.onmessage=()=>loadDogs();
  ws.onclose=()=>{wsState="OFFLINE";renderBoard();scheduleReconnect();};
  ws.onerror=()=>ws.close();
}
function scheduleReconnect(){
  if(reconnectTimer) return;
  reconnectTimer=setTimeout(()=>{reconnectTimer=null;connectWS();},3000);
}

connectWS();
loadDogs();
