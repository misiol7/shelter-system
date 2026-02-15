const app=document.getElementById("app");
let dogs=[];

function color(d){
 if(!d.available) return "gray";
 if(d.status!=="WALKING") return "blue";
 return "green";
}

async function load(){
 const r=await fetch("/api/dogs");
 dogs=await r.json();
 render();
}

function render(){
 app.innerHTML="<h1>🐾 Schronisko PRO</h1><div class='grid' id='g'></div>";
 const g=document.getElementById("g");
 dogs.forEach(d=>{
  const c=document.createElement("div");
  c.className="card "+color(d);
  c.innerHTML=`<h3>${d.name}</h3>
  <p>${d.daily_minutes} min</p>
  <button onclick="start(${d.id})">START</button>
  <button onclick="stop(${d.id})">STOP</button>`;
  g.appendChild(c);
 });
}

async function start(id){await fetch(`/api/walk/start?dog_id=${id}`,{method:"POST"});}
async function stop(id){await fetch(`/api/walk/stop?dog_id=${id}`,{method:"POST"});}

setInterval(load,5000);
load();

const ws=new WebSocket((location.protocol==="https:"?"wss":"ws")+`://${location.host}/ws`);
ws.onmessage=load;
