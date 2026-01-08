async function loadEvents() {
  const res = await fetch("http://127.0.0.1:8000/events");
  const data = await res.json();

  const list = document.getElementById("events");
  list.innerHTML = "";

  data.forEach(e => {
    const li = document.createElement("li");
    li.innerText = e.event + " (" + e.confidence.toFixed(2) + ")";
    list.appendChild(li);
  });
}

async function loadRisk() {
  const res = await fetch("http://127.0.0.1:8000/risk");
  const data = await res.json();
  alert("Рівень ризику: " + data.risk);
}