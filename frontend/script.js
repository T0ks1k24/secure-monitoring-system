function startEvents() {
  const eventsList = document.getElementById("events");
  const riskLabel = document.getElementById("risk");

  eventsList.innerHTML = "";

  const source = new EventSource("http://127.0.0.1:8000/events");

  source.onmessage = function (event) {
    const data = JSON.parse(event.data);

    // update events list
    const li = document.createElement("li");
    li.innerText = `${data.event} (${data.confidence.toFixed(2)})`;
    eventsList.appendChild(li);

    // update risk
    riskLabel.innerText = data.risk;
    riskLabel.style.color =
      data.risk === "HIGH"
        ? "red"
        : data.risk === "MEDIUM"
        ? "orange"
        : "green";
  };

  source.onerror = function () {
    console.log("SSE connection closed");
    source.close();
  };
}
