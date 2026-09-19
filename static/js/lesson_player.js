(() => {
  // Frontend side of the anti-skip lesson player.
  // This script sends playback events to the Django endpoint:
  // /courses/lessons/<lesson_id>/playback/
  const video = document.querySelector("[data-lesson-player]");
  if (!video) {
    return;
  }

  const config = window.lessonPlayerConfig || {};
  const playbackUrl = video.dataset.playbackUrl;
  const statusEl = document.querySelector("[data-video-status]");
  const progressFill = document.querySelector("[data-video-progress-fill]");
  const controls = document.querySelectorAll("[data-video-action]");
  const nextButtons = document.querySelectorAll("[data-next-link]");
  const transcriptRoot = document.querySelector("[data-live-transcript]");
  const transcriptPlaceholder = document.querySelector("[data-transcript-placeholder]");
  const currentTimeEl = document.querySelector("[data-video-current-time]");
  const durationEl = document.querySelector("[data-video-duration]");
  const attentionWarning = document.querySelector("[data-attention-warning]");
  const completeButton = document.querySelector("[data-complete-button]");
  let lastAllowedPosition = 0;
  let suppressSeekEvent = false;
  let lastSentAt = 0;
  let transcriptNodes = [];

  const renderTranscriptFromTrack = () => {
    if (!transcriptRoot) {
      return;
    }
    const track = Array.from(video.textTracks || []).find((item) => item.kind === "subtitles" || item.kind === "captions");
    if (!track) {
      return;
    }

    track.mode = "hidden";

    const buildNodes = () => {
      const cues = Array.from(track.cues || []);
      if (!cues.length) {
        return;
      }
      transcriptRoot.innerHTML = "";
      transcriptNodes = cues.map((cue, index) => {
        const line = document.createElement("button");
        line.type = "button";
        line.className = "transcript-line";
        line.dataset.cueIndex = String(index);
        line.textContent = cue.text;
        line.addEventListener("click", () => {
          video.currentTime = cue.startTime;
          video.play().catch(() => {});
        });
        transcriptRoot.appendChild(line);
        return line;
      });
      if (transcriptPlaceholder) {
        transcriptPlaceholder.remove();
      }
    };

    const syncActiveCue = () => {
      const activeCues = Array.from(track.activeCues || []);
      const activeCue = activeCues[0];
      transcriptNodes.forEach((node, index) => {
        const cue = track.cues[index];
        const isActive = Boolean(activeCue && cue && cue.startTime === activeCue.startTime && cue.endTime === activeCue.endTime);
        node.classList.toggle("transcript-line-active", isActive);
        if (isActive) {
          node.scrollIntoView({ block: "nearest", behavior: "smooth" });
        }
      });
    };

    buildNodes();
    track.addEventListener("cuechange", syncActiveCue);
    video.addEventListener("timeupdate", syncActiveCue);
  };

  const setStatus = (message) => {
    if (statusEl) {
      statusEl.textContent = message;
    }
  };

  const showAttentionWarning = (message) => {
    if (!attentionWarning) {
      return;
    }
    attentionWarning.hidden = false;
    attentionWarning.textContent = message;
  };

  const formatTime = (seconds) => {
    const safeSeconds = Math.max(0, Math.floor(seconds || 0));
    const mins = Math.floor(safeSeconds / 60);
    const secs = safeSeconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  };

  const syncTimeLabels = () => {
    if (currentTimeEl) {
      currentTimeEl.textContent = formatTime(video.currentTime);
    }
    if (durationEl) {
      durationEl.textContent = formatTime(video.duration);
    }
  };

  const updateCoverage = (coverageRatio, canAdvance) => {
    if (progressFill) {
      progressFill.style.width = `${Math.max(0, Math.min(coverageRatio * 100, 100))}%`;
    }
    nextButtons.forEach((nextButton) => {
      if (nextButton.tagName !== "A") {
        return;
      }
      nextButton.classList.toggle("button-disabled", !canAdvance);
      nextButton.setAttribute("aria-disabled", canAdvance ? "false" : "true");
      if (!canAdvance) {
        nextButton.addEventListener("click", preventNavigation);
      } else {
        nextButton.removeEventListener("click", preventNavigation);
      }
    });
  };

  const preventNavigation = (event) => {
    event.preventDefault();
    setStatus("Finish the current video without skipping ahead before going to the next lesson.");
  };

  const sendEvent = async (eventName) => {
    if (!config.enableTracking) {
      return;
    }
    // This fetch() call is the browser -> backend API connection for lesson progress.
    if (!playbackUrl || Number.isNaN(video.currentTime)) {
      return;
    }

    const payload = {
      event: eventName,
      position: video.currentTime || 0,
      duration: video.duration || 0,
    };

    const response = await fetch(playbackUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": config.csrfToken,
      },
      body: JSON.stringify(payload),
      credentials: "same-origin",
    });

    if (!response.ok) {
      return;
    }

    const data = await response.json();
    lastAllowedPosition = data.allowed_position ?? lastAllowedPosition;
    updateCoverage(data.coverage_ratio ?? 0, Boolean(data.can_advance));

    if (data.ok === false && typeof data.allowed_position === "number") {
      suppressSeekEvent = true;
      video.currentTime = data.allowed_position;
      setTimeout(() => {
        suppressSeekEvent = false;
      }, 150);
      setStatus(data.message || "Skipping ahead is disabled for this lesson.");
      if (!video.paused) {
        video.pause();
      }
      return;
    }

    if (data.video_completed) {
      setStatus("Lesson completed. You can continue to the next lesson.");
      if (completeButton) {
        completeButton.textContent = "Completed";
      }
    } else {
      setStatus("Pause and rewind are allowed. Skipping ahead will not unlock the next lesson.");
    }
  };

  const sendAttentionEvent = async (eventName, extra = {}) => {
    if (!config.enableTracking || !config.attentionUrl) {
      return;
    }
    const response = await fetch(config.attentionUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": config.csrfToken,
      },
      body: JSON.stringify({
        event: eventName,
        ...extra,
      }),
      credentials: "same-origin",
    });
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    if (["tab_hidden", "window_blur"].includes(eventName)) {
      showAttentionWarning("Warning: leaving the lesson window or switching tabs is being recorded for admin review.");
    }
    if (eventName === "reading_speed" && data.reading_speed_flag === "fast") {
      showAttentionWarning("Warning: reading too fast was detected and stored for admin review.");
    }
  };

  controls.forEach((control) => {
    control.addEventListener("click", async () => {
      const action = control.dataset.videoAction;
      if (action === "toggle") {
        if (video.paused) {
          await video.play();
          control.textContent = "Pause";
        } else {
          video.pause();
          control.textContent = "Play";
        }
      } else if (action === "rewind") {
        video.currentTime = Math.max(0, (video.currentTime || 0) - 10);
        sendEvent("rewind");
      } else if (action === "mute") {
        video.muted = !video.muted;
        control.textContent = video.muted ? "Unmute" : "Mute";
      } else if (action === "fullscreen" && video.requestFullscreen) {
        video.requestFullscreen();
      }
    });
  });

  video.addEventListener("play", () => {
    sendEvent("play");
    const toggleButton = document.querySelector('[data-video-action="toggle"]');
    if (toggleButton) {
      toggleButton.textContent = "Pause";
    }
  });

  video.addEventListener("pause", () => {
    sendEvent("pause");
    const toggleButton = document.querySelector('[data-video-action="toggle"]');
    if (toggleButton) {
      toggleButton.textContent = "Play";
    }
  });

  video.addEventListener("seeked", () => {
    if (suppressSeekEvent) {
      return;
    }
    sendEvent("seeked");
  });

  video.addEventListener("timeupdate", () => {
    syncTimeLabels();
    const now = Date.now();
    if (now - lastSentAt < 2500) {
      return;
    }
    lastSentAt = now;
    sendEvent("timeupdate");
  });

  video.addEventListener("ended", () => {
    sendEvent("ended");
    syncTimeLabels();
  });

  video.addEventListener("loadedmetadata", syncTimeLabels);
  video.addEventListener("durationchange", syncTimeLabels);
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

  nextButtons.forEach((nextButton) => {
    if (nextButton.tagName === "A" && video.dataset.nextUnlocked !== "true") {
      nextButton.addEventListener("click", preventNavigation);
    }
  });

  renderTranscriptFromTrack();
  syncTimeLabels();
})();
