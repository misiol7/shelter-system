const app=document.getElementById("app");

let token=localStorage.getItem("admin_token");
let dogs=[];
let ws=null;
let reconnectTimer=null;
let wsState="OFFLINE";
let adminMode=false;

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
  const r=await fetch("/api/dogs");
  dogs=await r.json();
  adminMode ? renderAdmin() : renderBoard();
}

async function startWalk(id){
  await fetch(`/api/walk/start?dog_id=${id}`,{method:"POST"});
}
async function stopWalk(id){
  await fetch(`/api/walk/stop?dog_id=${id}`,{method:"POST"});
}

function renderBoard(){
  app.innerHTML=`
    <div class="header">
      <h2>🐾 Ewidencja spacerów ${wsBadge()}</h2>
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
      <p>Dzisiaj: ${d.daily_minutes} min</p>
      ${d.available ? `
      <button class="btn" onclick="startWalk(${d.id})">START</button>
      <button class="btn" onclick="stopWalk(${d.id})">STOP</button>
      ` : `<p>Niedostępny</p>`}
    `;
    g.appendChild(c);
  });
}

function showLogin(){
  app.innerHTML=`
    <div class="panel">
      <h2>Logowanie admina</h2>
      <input id="u" value="admin" placeholder="login"/>
      <input id="p" type="password" value="admin123" placeholder="hasło"/>
      <button class="btn" onclick="login()">Login</button>
      <button class="btn" onclick="backToBoard()">Powrót</button>
    </div>
  `;
}

async function login(){
  const u=document.getElementById("u").value;
  const p=document.getElementById("p").value;
  const r=await fetch(`/api/admin/login?username=${encodeURIComponent(u)}&password=${encodeURIComponent(p)}`,{method:"POST"});
  if(r.status!==200){alert("Błędne dane");return;}
  const data=await r.json();
  token=data.token;
  localStorage.setItem("admin_token",token);
  adminMode=true;
  loadDogs();
}

function backToBoard(){
  adminMode=false;
  renderBoard();
}

function renderAdmin(){
  app.innerHTML=`
    <div class="header">
      <h2>Admin — psy</h2>
      <div>
        <button class="btn" onclick="adminMode=false;loadDogs()">Tablica</button>
        <button class="btn" onclick="logout()">Wyloguj</button>
      </div>
    </div>
    <div class="panel">
      <input id="newdog" placeholder="imię psa"/>
      <button class="btn" onclick="addDog()">Dodaj psa</button>
    </div>
    <div class="grid" id="grid"></div>
  `;
  const g=document.getElementById("grid");
  dogs.forEach(d=>{
    const c=document.createElement("div");
    c.className="card blue";
    c.innerHTML=`
      <h3>${d.name}</h3>
      <p>Status: ${d.status}</p>
      <p>Dostępny: ${d.available ? "TAK":"NIE"}</p>
      <button class="btn" onclick="toggleAvail(${d.id}, ${!d.available})">
      ${d.available ? "Zablokuj" : "Udostępnij"}
      </button>
    `;
    g.appendChild(c);
  });
}

async function addDog(){
  const n=document.getElementById("newdog").value;
  if(!n) return;
  await fetch(`/api/admin/dogs?name=${encodeURIComponent(n)}`,{
    method:"POST",
    headers:{Authorization:`Bearer ${token}`}
  });
  document.getElementById("newdog").value="";
  loadDogs();
}

async function toggleAvail(id,val){
  await fetch(`/api/admin/dogs/${id}/availability?available=${val}`,{
    method:"POST",
    headers:{Authorization:`Bearer ${token}`}
  });
  loadDogs();
}

function logout(){
  localStorage.removeItem("admin_token");
  token=null;
  adminMode=false;
  renderBoard();
}

function connectWS(){
  ws=new WebSocket(`${location.protocol==="https:"?"wss":"ws"}://${location.host}/ws`);
  ws.onopen=()=>{wsState="ONLINE"; adminMode?renderAdmin():renderBoard();};
  ws.onmessage = async () => {
  const r = await fetch("/api/dogs");
  dogs = await r.json();

  if (!adminMode) {
    renderBoard();
  } else {
    renderAdmin(); // tylko aktualizacja listy, bez resetu inputa
  }
};

  ws.onclose=()=>{wsState="OFFLINE"; adminMode?renderAdmin():renderBoard(); reconnect();};
  ws.onerror=()=>ws.close();
}
function reconnect(){
  if(reconnectTimer) return;
  reconnectTimer=setTimeout(()=>{
    reconnectTimer=null;
    connectWS();
  },3000);
}

connectWS();
loadDogs();
