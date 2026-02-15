const app = document.getElementById("app");

let token = localStorage.getItem("admin_token");
let dogs = [];

// -----------------------------
// API
// -----------------------------
async function loadDogs() {
  const r = await fetch("/api/dogs");
  dogs = await r.json();
  renderBoard();
}

async function startWalk(id){
  await fetch(`/api/walk/start?dog_id=${id}`,{method:"POST"});
}

async function stopWalk(id){
  await fetch(`/api/walk/stop?dog_id=${id}`,{method:"POST"});
}

// -----------------------------
// RENDER
// -----------------------------
function color(d){
  if(!d.available) return "gray";
  if(d.status!=="WALKING") return "blue";
  if(d.daily_minutes >= 90) return "red";
  if(d.daily_minutes >= 60) return "orange";
  return "green";
}

function renderBoard(){
  app.innerHTML = `
    <div class="header">
      <h2>🐾 Ewidencja spacerów</h2>
      <button class="btn" onclick="showLogin()">Admin</button>
    </div>
    <div class="grid" id="grid"></div>
  `;

  const g = document.getElementById("grid");

  dogs.forEach(d=>{
    const c = document.createElement("div");
    c.className = `card ${color(d)}`;
    c.innerHTML = `
      <h3>${d.name}</h3>
      <p>Status: ${d.status}</p>
      <p>Dziś: ${d.daily_minutes} min</p>
      ${d.available ? `
      <button class="btn" onclick="startWalk(${d.id})">START</button>
      <button class="btn" onclick="stopWalk(${d.id})">STOP</button>
      ` : `<p>Niedostępny</p>`}
    `;
    g.appendChild(c);
  });
}

// -----------------------------
// ADMIN LOGIN (placeholder)
// -----------------------------
function showLogin(){
  alert("Panel admin działa — logowanie wróci w następnej wersji.");
}

// -----------------------------
// WEBSOCKET AUTO RELOAD
// -----------------------------
function connectWS(){
  const ws = new WebSocket(
    `${location.protocol==="https:"?"wss":"ws"}://${location.host}/ws`
  );

  ws.onmessage = () => loadDogs();

  ws.onclose = () => {
    setTimeout(connectWS, 3000);
  };
}

connectWS();
loadDogs();
