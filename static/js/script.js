async function sendMessage() {
  let input = document.getElementById("input");
  let message = input.value.trim();
  if (!message) return;

  let chatbox = document.getElementById("chatbox");

  // User message
  let userDiv = document.createElement("div");
  userDiv.className = "user-message";
  userDiv.innerText = message;
  chatbox.appendChild(userDiv);

  input.value = "";
  chatbox.scrollTop = chatbox.scrollHeight;

  // Send to Flask backend
  let res = await fetch("/get", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });
  let data = await res.json();

  // Bot reply
  let botDiv = document.createElement("div");
  botDiv.className = "bot-message";
  botDiv.innerText = data.reply;
  chatbox.appendChild(botDiv);

  chatbox.scrollTop = chatbox.scrollHeight;
}
