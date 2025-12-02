const term = document.getElementById("terminal");
const statusEl = document.getElementById("status");
const tweetCountEl = document.getElementById("tweet-count");
const tableBody = document.querySelector("#tweet-table tbody");

let evt = null;
function appendLog(obj){
  const t = new Date(obj.time*1000).toLocaleTimeString();
  const line = `[${t}] ${obj.level} — ${obj.msg}`;
  term.innerHTML += line + "<br>";
  term.scrollTop = term.scrollHeight;
}

function startLogs(){
  if(evt) evt.close();
  evt = new EventSource("/stream");
  evt.onmessage = function(e){
    if(e.data && e.data !== ":"){
      try{
        const obj = JSON.parse(e.data);
        appendLog(obj);
      } catch(err){}
    }
  };
  evt.onerror = function(){ /* ignore */ };
}

// fetch live data and render table
async function refreshData(){
  try{
    const res = await fetch("/data");
    const j = await res.json();
    const tweets = j.tweets || [];
    tweetCountEl.textContent = tweets.length;
    // render last 200 tweets only
    tableBody.innerHTML = "";
    tweets.slice(-200).forEach((t,i) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${i+1}</td>
        <td>${escapeHtml(t.username||"")}</td>
        <td>${escapeHtml(t.handle||"")}</td>
        <td>${escapeHtml(t.text||"")}</td>
        <td>${escapeHtml(t.timestamp||"")}</td>
        <td>${t.url ? `<a href="${t.url}" target="_blank">link</a>` : ""}</td>`;
      tableBody.appendChild(tr);
    });
  }catch(err){
    console.error(err);
  }
}

// start polling every 2s
setInterval(refreshData, 2000);
refreshData();
startLogs();

// buttons
document.getElementById("btn-start").onclick = async () => {
  const keyword = document.getElementById("keyword").value.trim();
  const max_tweets = document.getElementById("max_tweets").value || 50;
  let cookies = document.getElementById("cookies").value.trim();
  let cookies_json = null;
  if(cookies){
    try{ cookies_json = JSON.parse(cookies); } catch(e){ alert("Invalid cookies JSON"); return; }
  }
  statusEl.textContent = "Starting...";
  appendLog({time:Date.now()/1000, level:"INFO", msg:`Requesting start for '${keyword}' max ${max_tweets}`});
  const res = await fetch("/start", {
    method:"POST",
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({keyword, max_tweets, cookies: cookies_json})
  });
  const j = await res.json();
  if(j.status === "ok"){
    statusEl.textContent = "Running";
    appendLog({time:Date.now()/1000, level:"OK", msg:j.message});
  } else {
    statusEl.textContent = "Error";
    appendLog({time:Date.now()/1000, level:"ERROR", msg:j.message});
  }
};

document.getElementById("btn-stop").onclick = async () => {
  appendLog({time:Date.now()/1000, level:"INFO", msg:"Stop requested by user"});
  const res = await fetch("/stop", {method:"POST"});
  const j = await res.json();
  appendLog({time:Date.now()/1000, level:j.status==="ok"?"OK":"ERROR", msg:j.message});
  statusEl.textContent = "Stopped";
};

document.getElementById("btn-download-csv").onclick = () => {
  window.location = "/download/csv";
};
document.getElementById("btn-download-json").onclick = () => {
  window.location = "/download/json";
};

function escapeHtml(unsafe){
  return (unsafe || "").toString()
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
