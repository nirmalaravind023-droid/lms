(() => {
  const root = document.documentElement;
  const toggle = document.querySelector("[data-theme-toggle]");
  const label = document.querySelector("[data-theme-label]");
  const icon = document.querySelector("[data-theme-icon]");
  const savedTheme = window.localStorage.getItem("lms-theme") || "light";

  const applyTheme = (theme) => {
    root.setAttribute("data-theme", theme);
    if (label) {
      label.textContent = theme === "dark" ? "Dark Mode" : "Light Mode";
    }
    if (icon) {
      icon.innerHTML = theme === "dark" ? "&#9790;" : "&#9728;";
    }
  };

  applyTheme(savedTheme);

  if (toggle) {
    toggle.addEventListener("click", () => {
      const nextTheme = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      window.localStorage.setItem("lms-theme", nextTheme);
      applyTheme(nextTheme);
    });
  }

  const activeNav = document.querySelector(".nav-link-active");
  if (activeNav) {
    activeNav.setAttribute("aria-current", "page");
  }

  const loadingOverlay = document.querySelector("[data-page-loading-overlay]");
  let loadingLocked = false;

  const showLoadingState = (button, label) => {
    if (button) {
      if (!button.dataset.originalLabel) {
        button.dataset.originalLabel = button.textContent.trim();
      }
      button.classList.add("button-loading");
      button.setAttribute("aria-busy", "true");
      button.disabled = true;
      if (label) {
        button.textContent = label;
      }
    }
    if (loadingOverlay && !loadingLocked) {
      const title = loadingOverlay.querySelector("strong");
      if (title && label) {
        title.textContent = label;
      }
      loadingOverlay.hidden = false;
      loadingLocked = true;
    }
  };

  document.querySelectorAll("form[data-loading-form]").forEach((form) => {
    form.addEventListener("submit", () => {
      const submitter =
        form.querySelector("[data-loading-button]") ||
        form.querySelector('button[type="submit"]') ||
        form.querySelector('input[type="submit"]');
      showLoadingState(submitter, form.dataset.loadingLabel || "Saving...");
    });
  });

  document.querySelectorAll("[data-loading-link]").forEach((link) => {
    link.addEventListener("click", () => {
      showLoadingState(link.classList.contains("button") ? link : null, link.dataset.loadingLabel || "Loading...");
    });
  });

  const flashStack = document.querySelector(".flash-stack");
  if (flashStack) {
    setTimeout(() => {
      flashStack.classList.add("flash-stack-soft");
    }, 2400);
  }

  const errorModal = document.querySelector("[data-global-error-modal]");
  const errorModalBody = document.querySelector("[data-global-error-body]");
  const errorModalTitle = document.querySelector("[data-global-error-title]");
  const errorModalBadge = document.querySelector("[data-global-error-badge]");
  const errorModalClose = document.querySelector("[data-global-error-close]");

  const openErrorModal = (items, level = "error") => {
    if (!errorModal || !errorModalBody || !items.length) {
      return;
    }
    errorModalBody.innerHTML = "";
    items.forEach((text) => {
      const card = document.createElement("div");
      card.className = "flash";
      card.textContent = text;
      errorModalBody.appendChild(card);
    });
    if (errorModalTitle) {
      errorModalTitle.textContent =
        level === "success"
          ? "Action completed"
          : level === "warning"
            ? "Please review these messages"
            : "What is the error?";
    }
    if (errorModalBadge) {
      errorModalBadge.textContent = level === "success" ? "Success" : level === "warning" ? "Warning" : "Error";
    }
    errorModal.hidden = false;
  };

  errorModalClose?.addEventListener("click", () => {
    if (errorModal) {
      errorModal.hidden = true;
    }
  });

  const collectPopupMessages = () => {
    const unique = new Set();
    let level = "";
    let hasExplicitPopup = false;

    document.querySelectorAll(".flash-stack .flash").forEach((item) => {
      const text = item.textContent.trim();
      const itemLevel = (item.dataset.flashLevel || "error").toLowerCase();
      const itemWantsPopup = item.dataset.flashPopup === "true";
      if (!text) return;
      if (itemLevel.includes("error")) {
        level = "error";
      } else if (!level && itemLevel.includes("warning")) {
        level = "warning";
      } else if (!level && itemLevel.includes("success")) {
        level = "success";
      }
      if (itemWantsPopup) {
        hasExplicitPopup = true;
        unique.add(text);
      } else if (itemLevel.includes("error") || itemLevel.includes("warning")) {
        unique.add(text);
      }
    });

    document.querySelectorAll(".form-error-stack").forEach((stack) => {
      const text = stack.textContent.trim().replace(/\s+/g, " ");
      if (!text) return;
      level = "error";
      unique.add(text);
    });

    return { items: Array.from(unique), level: level || "error", hasExplicitPopup };
  };

  const popupMessages = collectPopupMessages();
  if (popupMessages.items.length && (popupMessages.hasExplicitPopup || popupMessages.level !== "success")) {
    window.setTimeout(() => openErrorModal(popupMessages.items, popupMessages.level), 120);
  }

  const searchRoot = document.querySelector("[data-global-search]");
  if (searchRoot) {
    const endpoint = searchRoot.getAttribute("data-search-endpoint");
    const input = searchRoot.querySelector("[data-search-input]");
    const results = searchRoot.querySelector("[data-search-results]");
    const body = searchRoot.querySelector("[data-search-body]");
    const source = searchRoot.querySelector("[data-search-source]");
    let timer = null;
    let activeQuery = "";

    const closeResults = () => {
      if (results) {
        results.hidden = true;
      }
      if (body) {
        body.innerHTML = "";
      }
      if (source) {
        source.textContent = "";
      }
    };

    const renderResults = (payload) => {
      if (!body || !results || !source) {
        return;
      }
      body.innerHTML = "";
      source.textContent = payload.source === "elasticsearch" ? "Elasticsearch" : "Database";
      const items = payload.results || [];
      if (!items.length) {
        const emptyState = document.createElement("p");
        emptyState.className = "muted";
        emptyState.textContent = "No results found.";
        body.appendChild(emptyState);
      } else {
        items.forEach((item) => {
          const link = document.createElement("a");
          link.className = "shell-search-result";
          link.href = item.url;

          const category = document.createElement("span");
          category.className = "shell-search-result-category";
          category.textContent = item.category;

          const title = document.createElement("strong");
          title.textContent = item.title;

          const subtitle = document.createElement("small");
          subtitle.textContent = item.meta ? `${item.subtitle} • ${item.meta}` : item.subtitle;

          link.appendChild(category);
          link.appendChild(title);
          link.appendChild(subtitle);
          body.appendChild(link);
        });
      }
      results.hidden = false;
    };

    const fetchResults = async (query) => {
      try {
        const response = await fetch(`${endpoint}?q=${encodeURIComponent(query)}`, {
          credentials: "same-origin",
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (!response.ok) {
          throw new Error("Search failed");
        }
        const payload = await response.json();
        if (activeQuery === query) {
          renderResults(payload);
        }
      } catch (error) {
        closeResults();
      }
    };

    if (input) {
      input.addEventListener("input", (event) => {
        const query = event.target.value.trim();
        activeQuery = query;
        window.clearTimeout(timer);
        if (query.length < 2) {
          closeResults();
          return;
        }
        timer = window.setTimeout(() => fetchResults(query), 220);
      });

      input.addEventListener("focus", () => {
        if (body && body.children.length) {
          results.hidden = false;
        }
      });
    }

    document.addEventListener("click", (event) => {
      if (!searchRoot.contains(event.target)) {
        closeResults();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeResults();
      }
    });
  }
})();
