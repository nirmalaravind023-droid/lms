(() => {
  const timer = document.querySelector("[data-reading-timer]");
  const completeButton = document.querySelector("[data-reading-complete-button]");
  const attentionWarning = document.querySelector("[data-attention-warning]");
  if (!timer || !completeButton) {
    return;
  }

  const config = window.lessonPlayerConfig || {};
  const sendAttentionEvent = async (eventName, extra = {}) => {
    if (!config.enableTracking || !config.attentionUrl) {
      return;
    }
    await fetch(config.attentionUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": config.csrfToken,
      },
      body: JSON.stringify({ event: eventName, ...extra }),
      credentials: "same-origin",
    });
  };

  const showAttentionWarning = (message) => {
    if (!attentionWarning) {
      return;
    }
    attentionWarning.hidden = false;
    attentionWarning.textContent = message;
  };

  let remaining = Number(timer.dataset.readingRemaining || 0);
  const content = document.querySelector(".lesson-article-body");
  const wordCount = content ? (content.textContent || "").trim().split(/\s+/).filter(Boolean).length : 0;
  if (Number.isNaN(remaining) || remaining <= 0) {
    completeButton.disabled = false;
    completeButton.removeAttribute("data-reading-complete-button");
    timer.textContent = "Article reading requirement completed. You can continue.";
    return;
  }

  const tick = () => {
    remaining -= 1;
    if (remaining <= 0) {
      completeButton.disabled = false;
      completeButton.removeAttribute("data-reading-complete-button");
      timer.textContent = "Article reading requirement completed. You can continue.";
      return;
    }
    timer.innerHTML = `Keep this page open for <strong>${remaining}</strong> more seconds to unlock completion.`;
    window.setTimeout(tick, 1000);
  };

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      sendAttentionEvent("tab_hidden");
      showAttentionWarning("Warning: tab switching is being recorded for admin review.");
    }
  });

  window.addEventListener("blur", () => {
    sendAttentionEvent("window_blur");
    showAttentionWarning("Warning: leaving the lesson window is being recorded for admin review.");
  });

  document.addEventListener("fullscreenchange", () => {
    if (document.fullscreenElement) {
      sendAttentionEvent("fullscreen_enter");
    }
  });

  timer.innerHTML = `Keep this page open for <strong>${remaining}</strong> more seconds to unlock completion.`;
  if (wordCount > 0) {
    const estimatedMinutes = Math.max(1 / 60, Number(timer.dataset.readingRemaining || 0) / 60);
    const wpm = wordCount / estimatedMinutes;
    const flag = wpm > 260 ? "fast" : "normal";
    sendAttentionEvent("reading_speed", { wpm, flag });
    if (flag === "fast") {
      showAttentionWarning("Warning: reading too fast was detected and stored for admin review.");
    }
  }
  window.setTimeout(tick, 1000);
})();
