function gatherPayloadFromContainer(container, childSelector) {
  return Array.from(container.querySelectorAll(childSelector)).map((element, index) => ({
    id: element.dataset.id,
    order: index + 1
  }));
}

function refreshModuleLabels(container) {
  Array.from(container.querySelectorAll(".builder-card[data-id]")).forEach((card, index) => {
    const label = card.querySelector("[data-module-order-label]");
    if (label) {
      label.textContent = `Module ${index + 1}`;
    }
  });
}

function refreshLessonLabels(container) {
  Array.from(container.querySelectorAll(".lesson-chip[data-id]")).forEach((card, index) => {
    const label = card.querySelector("[data-lesson-order-label]");
    if (label) {
      label.textContent = `Lesson ${index + 1}`;
    }
  });
}

async function postOrder(url, payload, csrfToken) {
  await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken
    },
    body: JSON.stringify(payload)
  });
}

function enableDrag(container, childSelector, saveCallback) {
  let dragged = null;

  container.addEventListener("dragstart", (event) => {
    dragged = event.target.closest(childSelector);
    if (dragged) {
      dragged.classList.add("is-dragging");
    }
  });

  container.addEventListener("dragover", (event) => {
    event.preventDefault();
    const target = event.target.closest(childSelector);
    if (!dragged || !target || dragged === target) {
      return;
    }
    const targetRect = target.getBoundingClientRect();
    const after = event.clientY > targetRect.top + targetRect.height / 2;
    container.insertBefore(dragged, after ? target.nextSibling : target);
  });

  container.addEventListener("drop", async () => {
    if (dragged) {
      await saveCallback();
      dragged.classList.remove("is-dragging");
      dragged = null;
    }
  });

  container.addEventListener("dragend", () => {
    if (dragged) {
      dragged.classList.remove("is-dragging");
      dragged = null;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const builder = document.getElementById("course-builder");
  if (!builder) {
    return;
  }

  const csrfToken = builder.dataset.csrf;
  const moduleContainer = document.getElementById("modules");
  if (moduleContainer) {
    refreshModuleLabels(moduleContainer);
    enableDrag(moduleContainer, ".builder-card", async () => {
      refreshModuleLabels(moduleContainer);
      await postOrder(builder.dataset.moduleUrl, gatherPayloadFromContainer(moduleContainer, ".builder-card"), csrfToken);
    });
  }

  document.querySelectorAll(".sortable-lessons").forEach((lessonContainer) => {
    refreshLessonLabels(lessonContainer);
    enableDrag(lessonContainer, ".lesson-chip", async () => {
      refreshLessonLabels(lessonContainer);
      await postOrder(builder.dataset.lessonUrl, gatherPayloadFromContainer(lessonContainer, ".lesson-chip"), csrfToken);
    });
  });
});
