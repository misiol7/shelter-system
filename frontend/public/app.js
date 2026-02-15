const app=document.getElementById("app");
let token=localStorage.getItem("admin_token");
let dogs=[];

function color(d){if(!d.available)return"gray";if(d.status!=="WALKING")return"blue";if(d.daily_minutes>=90)return"red";if(d.daily_minutes>=60)return"orange";return"green";}
function showLogin(){app.innerHTML=`<div class='panel'><h2>Logowanie admina</h2><input id='u' value='admin'><input id='p' type='password' value='admin123'><button class='btn' onclick='login()'>Login</button><hr><button class='btn' onclick='showBoard()'>Tablica spacerów</button></div>`}
async function login(){let u=uEl().value,p=pEl().value;let r=await fetch(`/api/admin/login?username=${u}&password=${p}`,{method:"POST"});if(r.status!==200){alert("Błąd");return;}let d=await r.json();token=d.token;localStorage.setItem("admin_token",token);loadDogs(true)}
function uEl(){return document.getElementById("u")} function pEl(){return document.getElementById("p")}
async function loadDogs(admin=false){dogs=await (await fetch("/api/dogs")).json(); admin?renderAdmin():renderBoard();}
async function startWalk(id){await fetch(`/api/walk/start?dog_id=${id}`,{method:"POST"})}
async function stopWalk(id){await fetch(`/api/walk/stop?dog_id=${id}`,{method:"POST"})}
function renderBoard(){app.innerHTML=`<div class='header'><h2>🐾 Ewidencja spacerów</h2><button class='btn' onclick='showLogin()'>Admin</button></div><div class='grid' id='g'></div>`;let g=document.getElementById("g");dogs.forEach(d=>{let c=document.createElement("div");c.className=`card ${color(d)}`;c.innerHTML=`<h3>${d.name}</h3><p>${d.status}</p><p>Dziś: ${d.daily_minutes} min</p>${d.available?`<button class='btn' onclick='startWalk(${d.id})'>START</button><button class='btn' onclick='stopWalk(${d.id})'>STOP</button>`:"<p>Niedostępny</p>"}`;g.appendChild(c);});}
function renderAdmin(){app.innerHTML=`<div class='header'><h2>Admin</h2><div><button class='btn' onclick='showBoard()'>Tablica</button><button class='btn' onclick='logout()'>Wyloguj</button></div></div><div class='panel'><input id='newdog' placeholder='imię psa'><button class='btn' onclick='addDog()'>Dodaj</button></div><div class='grid' id='g'></div>`;let g=document.getElementById("g");dogs.forEach(d=>{let c=document.createElement("div");c.className='card blue';c.innerHTML=`<h3>${d.name}</h3><p>Dostępny: ${d.available}</p><button class='btn' onclick='toggle(${d.id},${!d.available})'>${d.available?"Zablokuj":"Udostępnij"}</button>`;g.appendChild(c);});}
async function addDog(){let n=document.getElementById("newdog").value;if(!n)return;await fetch(`/api/admin/dogs?name=${encodeURIComponent(n)}`,{method:"POST",headers:{Authorization:`Bearer ${token}`}});loadDogs(true)}
async function toggle(id,val){await fetch(`/api/admin/dogs/${id}/availability?available=${val}`,{method:"POST",headers:{Authorization:`Bearer ${token}`}});loadDogs(true)}
function logout(){localStorage.removeItem("admin_token");token=null;showLogin()}
function showBoard(){loadDogs(false)}
const ws=new WebSocket(`${location.protocol==="https:"?"wss":"ws"}://${location.host}/ws`);
ws.onmessage=()=>loadDogs(false);
showBoard();
