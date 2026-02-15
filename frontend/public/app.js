const app = document.getElementById("app");

let dogs = [];
let token = localStorage.getItem("admin_token");
let adminMode = false;
let typingLock = false;

let ws = null;
let reconnectTimer = null;
let wsState = "OFFLINE";

let boardInitialized = false;

// =========================
// HELPERS
// =========================

function cardColor(d) {
  if (!d.available) return "gray";
  if (d.status !== "WALKING") return "blue";
  if (d.daily_minutes >= 90) return "red";
  if (d.daily_minutes >= 60) return "orange";
  return "green";
}

async function fetchDogs() {
  const r = await fetch("/api/dogs");
  dogs = await r.json();
}

// =========================
// BOARD (ULTRA FAST)
// =========================

function createDogCard(d) {
  const c = document.createElement("div");
  c.id = `dog-${d.id}`;
  c.className = `card ${cardColor(d)}`;

  c.innerHTML = `
    <h3>${d.name}</h3>
    <p>Status: ${d.status}</p>
    <p>Dzisiaj: ${d.daily_minutes} min</p>
    ${d.available ? `
      <button class="btn" onclick="startWalk(${d.id})">START</button>
      <button class="btn" onclick="stopWalk(${d.id})">STOP</button>
    ` : `<p>Niedostępny</p>`}
  `;

  return c;
}

function updateDogCard(d) {
  const old = document.getElementById(`dog-${d.id}`);
  const newCard = createDogCard(d);

  if (old) old.replaceWith(newCard);
}

function renderBoard() {
  app.innerHTML = `
    <div class="header">
      <h2>🐾 Ewidencja spacerów (WS: ${wsState})</h2>
      <button class="btn" onclick="showLogin()">Admin</button>
    </div>
    <div class="grid" id="grid"></div>
  `;

  const g = document.getElementById("grid");

  dogs.forEach(d => g.appendChild(createDogCard(d)));

  boardInitialized = true;
}

// =========================
// WALK
// =========================

async function startWalk(id) {
  await fetch(`/api/walk/start?dog_id=${id}`, { method: "POST" });
}

async function stopWalk(id) {
  await fetch(`/api/walk/stop?dog_id=${id}`, { method: "POST" });
}

// =========================
// ADMIN LOGIN
// =========================

function showLogin() {
  app.innerHTML = `
    <div class="panel">
      <h2>Logowanie admina</h2>
      <input id="u" value="admin">
      <input id="p" type="password" value="admin123">
      <button class="btn" onclick="login()">Login</button>
      <button class="btn" onclick="goBoard()">Powrót</button>
    </div>
  `;
}

async function login() {
  const u = document.getElementById("u").value;
  const p = document.getElementById("p").value;

  const r = await fetch(
    `/api/admin/login?username=${encodeURIComponent(u)}&password=${encodeURIComponent(p)}`,
    { method: "POST" }
  );

  if (r.status !== 200) return alert("Błędne dane");

  token = (await r.json()).token;
  localStorage.setItem("admin_token", token);

  adminMode = true;
  renderAdmin();
}

// =========================
// ADMIN PANEL
// =========================

function renderAdmin() {
  app.innerHTML = `
    <div class="header">
      <h2>Admin (WS: ${wsState})</h2>
      <div>
        <button class="btn" onclick="goBoard()">Tablica</button>
        <button class="btn" onclick="logout()">Wyloguj</button>
      </div>
    </div>

    <div class="panel">
      <input id="newdog"
             placeholder="imię psa"
             onfocus="typingLock=true"
             onblur="typingLock=false">
      <button class="btn" onclick="addDog()">Dodaj psa</button>
    </div>

    <div class="grid" id="grid"></div>
  `;

  const g = document.getElementById("grid");

  dogs.forEach(d => {
    const c = document.createElement("div");
    c.className = "card blue";

    c.innerHTML = `
      <h3>${d.name}</h3>
      <p>Dostępny: ${d.available ? "TAK":"NIE"}</p>

      <button class="btn" onclick="toggleAvail(${d.id}, ${!d.available})">
        ${d.available ? "Zablokuj":"Udostępnij"}
      </button>

      <button class="btn" onclick="deleteDog(${d.id})">
        Usuń
      </button>
    `;

    g.appendChild(c);
  });
}

async function addDog() {
  const n = document.getElementById("newdog").value;
  if (!n) return;

  await fetch(`/api/admin/dogs?name=${encodeURIComponent(n)}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` }
  });
}

async function toggleAvail(id,val){
  await fetch(`/api/admin/dogs/${id}/availability?available=${val}`,{
    method:"POST",
    headers:{Authorization:`Bearer ${token}`}
  });
}

async function deleteDog(id){
  if(!confirm("Usunąć psa?")) return;

  await fetch(`/api/admin/dogs/${id}`,{
    method:"DELETE",
    headers:{Authorization:`Bearer ${token}`}
  });
}

function logout(){
  localStorage.removeItem("admin_token");
  token = null;
  adminMode = false;
  renderBoard();
}

function goBoard(){
  adminMode = false;
  renderBoard();
}

// =========================
// WEBSOCKET PRO 2.0
// =========================

function connectWS() {

  ws = new WebSocket(
    `${location.protocol==="https:"?"wss":"ws"}://${location.host}/ws`
  );

  ws.onopen = () => { wsState = "ONLINE"; };

  ws.onmessage = async () => {

    await fetchDogs();

    // ADMIN: nie ruszaj podczas pisania
    if (adminMode) {
      if (!typingLock) renderAdmin();
      return;
    }

    // TABLICA: update tylko kafelków
    if (!boardInitialized) {
      renderBoard();
      return;
    }

    dogs.forEach(updateDogCard);
  };

  ws.onclose = () => {
    wsState = "OFFLINE";

    if (!reconnectTimer) {
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connectWS();
      }, 3000);
    }
  };

  ws.onerror = () => ws.close();
}

// =========================
// START
// =========================

(async () => {
  await fetchDogs();
  renderBoard();
  connectWS();
})();
