const app=document.getElementById("app");

let dogs=[];
let wsState="OFFLINE";
let adminMode=false;
let typingLock=false;
let token=localStorage.getItem("admin_token");

// =========================

async function fetchDogs(){
  const r=await fetch("/api/dogs");
  dogs=await r.json();
}

function color(d){
  if(!d.available) return "gray";
  if(d.status!=="WALKING") return "blue";
  if(d.daily_minutes>=90) return "red";
  if(d.daily_minutes>=60) return "orange";
  return "green";
}

function liveMinutes(d){
  if(!d.walk_started) return d.daily_minutes;
  const start=new Date(d.walk_started);
  return d.daily_minutes + Math.floor((Date.now()-start)/60000);
}

// =========================
// TABLICA
// =========================

function renderBoard(){
  app.innerHTML=`
    <div class="header">
      <h2>🐾 Ewidencja spacerów (WS:${wsState})</h2>
      <button class="btn" onclick="showLogin()">Admin</button>
    </div>
    <div class="grid" id="grid"></div>
  `;

  const g=document.getElementById("grid");

  dogs.forEach(d=>{
    const c=document.createElement("div");
    c.className=`card ${color(d)}`;

    c.innerHTML=`
      <h3>${d.name}</h3>
      <p>Status: ${d.status}</p>
      <p>Dzisiaj: <span id="timer-${d.id}">${liveMinutes(d)}</span> min</p>
      ${d.available?`
        <button class="btn" onclick="startWalk(${d.id})">START</button>
        <button class="btn" onclick="stopWalk(${d.id})">STOP</button>
      `:`<p>Niedostępny</p>`}
    `;

    g.appendChild(c);
  });
}

// LIVE TIMER
setInterval(()=>{
  dogs.forEach(d=>{
    if(d.walk_started){
      const el=document.getElementById(`timer-${d.id}`);
      if(el) el.innerText=liveMinutes(d);
    }
  });
},1000);

// =========================
// WALK
// =========================

async function startWalk(id){
  await fetch(`/api/walk/start?dog_id=${id}`,{method:"POST"});
}
async function stopWalk(id){
  await fetch(`/api/walk/stop?dog_id=${id}`,{method:"POST"});
}

// =========================
// WEBSOCKET + POLLING
// =========================

function connectWS(){
  const ws=new WebSocket(`${location.protocol==="https:"?"wss":"ws"}://${location.host}/ws`);

  ws.onopen=()=>wsState="ONLINE";

  ws.onmessage=async ()=>{
    await fetchDogs();
    if(!adminMode) renderBoard();
  };

  ws.onclose=()=>{
    wsState="OFFLINE";
    setTimeout(connectWS,3000);
  };
}

// fallback polling
setInterval(async ()=>{
  if(!adminMode){
    await fetchDogs();
    renderBoard();
  }
},5000);

// =========================
// START
// =========================

(async ()=>{
  await fetchDogs();
  renderBoard();
  connectWS();
})();
