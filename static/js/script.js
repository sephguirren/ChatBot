async function sendMessage() {
    const userMessage = document.getElementById("userInput").value;

    if (!userMessage.trim()) return;

    // Show user message in chatbox
    document.getElementById("chatbox").innerHTML += `<p><b>You:</b> ${userMessage}</p>`;
    document.getElementById("userInput").value = "";

    try {
        const response = await fetch("/get", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: userMessage })
        });

        const data = await response.json();

        if (data.reply) {
            document.getElementById("chatbox").innerHTML += `<p><b>Bot:</b> ${data.reply}</p>`;
        } else {
            document.getElementById("chatbox").innerHTML += `<p><b>Bot:</b> (error: no reply)</p>`;
        }
    } catch (err) {
        document.getElementById("chatbox").innerHTML += `<p><b>Bot:</b> (server error)</p>`;
        console.error("Error:", err);
    }
}
