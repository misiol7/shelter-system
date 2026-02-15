const app = document.getElementById("app");

let token = localStorage.getItem("admin_token");
let dogs = [];
let ws = null;
let reconnectTimer = null;
let wsState = "OFFLINE";
let adminMode = false;

// ============================
// HELPERS
// ============================

function wsBadge() {
  return `<small style="font-size:12px">
    WS: <span style="color:${wsState==="ONLINE"?"green":"red"}">
    ${wsState}
    </span></small>`;
}

function color(d){
  if(!d.available) return "gray";
  if(d.status!=="WALKING") return "blue";
  if(d.daily_minutes >= 90) return "red";
  if(d.daily_minutes >= 60) return "orange";
  return "green";
}

// ============================
// DATA
// ============================

async function loadDogs(){
  const r = await fetch("/api/dogs");
  dogs = await r.json();

  if(adminMode) renderAdmin();
  else renderBoard();
}

// ============================
// WALK ACTIONS
// ============================

async function startWalk(id){
  await fetch(`/api/walk/start?dog_id=${id}`,{method:"POST"});
}

async function stopWalk(id){
  await fetch(`/api/walk/stop?dog_id=${id}`,{method:"POST"});
}

// ============================
// BOARD VIEW
// ============================

function renderBoard(){
  app.innerHTML = `
    <div class="header">
      <h2>🐾 Ewidencja spacerów ${wsBadge()}</h2>
      <button class="btn" onclick="showLogin()">Admin</button>
    </div>
    <div cla
