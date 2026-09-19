document.addEventListener("DOMContentLoaded", () => {
  if (!window.LMSChat) {
    return;
  }

  const windowNode = document.getElementById("chat-window");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");

  const socket = new WebSocket(
    `${window.LMSChat.wsScheme}://${window.location.host}/ws/chat/${window.LMSChat.conversationId}/`
  );

  socket.addEventListener("message", (event) => {
    const data = JSON.parse(event.data);
    const article = document.createElement("article");
    article.className = "chat-message";
    article.innerHTML = `<strong>${data.sender}</strong><p>${data.body}</p><small>${data.created_at}</small>`;
    windowNode.appendChild(article);
    windowNode.scrollTop = windowNode.scrollHeight;
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) {
      return;
    }
    socket.send(JSON.stringify({ message }));
    input.value = "";
  });
});

