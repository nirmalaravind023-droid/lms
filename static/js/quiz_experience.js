(() => {
  const form = document.querySelector("[data-quiz-form]");
  if (!form) {
    return;
  }

  const questionCards = Array.from(document.querySelectorAll("[data-question-card]"));
  const sectionBlocks = Array.from(document.querySelectorAll("[data-section-block]"));
  const sectionNavCards = Array.from(document.querySelectorAll("[data-quiz-section-nav]"));
  const ring = document.querySelector("[data-quiz-progress-ring]");
  const progressValue = document.querySelector("[data-quiz-progress-value]");
  const jumpButtons = Array.from(document.querySelectorAll("[data-quiz-jump]"));
  const previousButtons = Array.from(document.querySelectorAll("[data-prev-question]"));
  const nextButtons = Array.from(document.querySelectorAll("[data-next-question]"));
  const submitButton = document.querySelector("[data-submit-button]");
  const submitCopyNode = document.querySelector("[data-submit-copy]");
  const sectionLabelNode = document.querySelector("[data-current-section-label]");
  const sectionLockCopyNode = document.querySelector("[data-section-lock-copy]");
  const autosaveStatusNode = document.querySelector("[data-quiz-autosave-status]");
  const instructionModal = document.querySelector("[data-quiz-instruction-modal]");
  const startButton = document.querySelector("[data-start-quiz]");
  const startForm = document.getElementById("quiz-start-form");
  const totalMinutes = Number(form.dataset.totalMinutes || 0);
  const draftUrl = form.dataset.draftUrl || "";
  const draftAnswers = JSON.parse(form.dataset.draftAnswers || "{}");
  const csrfToken = form.querySelector("[name='csrfmiddlewaretoken']")?.value || "";
  let totalSecondsLeft = Math.max(0, totalMinutes * 60);
  let timerHandle = null;
  let questionTimerHandle = null;
  let questionSecondsLeft = 0;
  let activeSectionIndex = 0;
  let activeQuestionIndex = 0;
  let draftSaveHandle = null;
  let saveStateTimeoutHandle = null;
  let timedAutoSubmit = false;

  const sections = sectionBlocks.map((block) => {
    const sectionIndex = Number(block.dataset.sectionIndex || 0);
    return {
      block,
      sectionIndex,
      questions: questionCards.filter((card) => Number(card.dataset.sectionIndex || 0) === sectionIndex),
      navCard: sectionNavCards.find((card) => Number(card.dataset.sectionIndex || 0) === sectionIndex) || null,
    };
  });

  const setAutosaveStatus = (state, message) => {
    if (!autosaveStatusNode) {
      return;
    }
    autosaveStatusNode.textContent = message;
    autosaveStatusNode.classList.remove(
      "quiz-autosave-status-idle",
      "quiz-autosave-status-saving",
      "quiz-autosave-status-saved",
      "quiz-autosave-status-error",
    );
    autosaveStatusNode.classList.add(`quiz-autosave-status-${state}`);
  };

  const scheduleAutosaveReadyReset = () => {
    if (saveStateTimeoutHandle) {
      window.clearTimeout(saveStateTimeoutHandle);
    }
    saveStateTimeoutHandle = window.setTimeout(() => {
      setAutosaveStatus("idle", "Autosave ready");
    }, 1800);
  };

  const buildDraftPayload = () => {
    const payload = {};
    questionCards.forEach((card) => {
      const questionId = card.dataset.questionId || "";
      if (!questionId) return;
      const inputs = Array.from(card.querySelectorAll("input[type='radio'], input[type='checkbox']"));
      if (inputs.length) {
        payload[questionId] = {
          selected_choice_ids: inputs.filter((input) => input.checked).map((input) => String(input.value)),
          answer_text: "",
        };
        return;
      }
      const textarea = card.querySelector("[data-question-textarea]");
      payload[questionId] = {
        selected_choice_ids: [],
        answer_text: textarea ? textarea.value : "",
      };
    });
    return payload;
  };

  const applyDraftAnswers = () => {
    Object.entries(draftAnswers).forEach(([questionId, value]) => {
      const card = questionCards.find((item) => item.dataset.questionId === questionId);
      if (!card) return;
      const selectedIds = new Set((value.selected_choice_ids || []).map((item) => String(item)));
      card.querySelectorAll("input[type='radio'], input[type='checkbox']").forEach((input) => {
        input.checked = selectedIds.has(String(input.value));
      });
      const textarea = card.querySelector("[data-question-textarea]");
      if (textarea) {
        textarea.value = value.answer_text || "";
      }
    });
  };

  const queueDraftSave = () => {
    if (!draftUrl) {
      return;
    }
    if (draftSaveHandle) {
      window.clearTimeout(draftSaveHandle);
    }
    setAutosaveStatus("saving", "Saving...");
    draftSaveHandle = window.setTimeout(async () => {
      try {
        const response = await fetch(draftUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify(buildDraftPayload()),
        });
        if (!response.ok) {
          throw new Error("Draft save failed");
        }
        setAutosaveStatus("saved", "Autosaved");
        scheduleAutosaveReadyReset();
      } catch (error) {
        setAutosaveStatus("error", "Save failed");
      }
    }, 400);
  };

  const formatTimer = (seconds) => {
    const safeSeconds = Math.max(0, Math.floor(seconds));
    const mins = Math.floor(safeSeconds / 60).toString().padStart(2, "0");
    const secs = (safeSeconds % 60).toString().padStart(2, "0");
    return `${mins}:${secs}`;
  };

  const isQuestionAnswered = (card) => {
    const inputs = Array.from(card.querySelectorAll("input[type='radio'], input[type='checkbox']"));
    if (inputs.length) {
      return inputs.some((input) => input.checked);
    }
    const textarea = card.querySelector("[data-question-textarea]");
    return textarea ? textarea.value.trim().length > 0 : false;
  };

  const getActiveSection = () => sections[activeSectionIndex] || null;

  const getActiveCard = () => {
    const section = getActiveSection();
    return section?.questions[activeQuestionIndex] || null;
  };

  const isSectionComplete = (section) => section.questions.every(isQuestionAnswered);

  const isAssessmentComplete = () => questionCards.every(isQuestionAnswered);

  const setSectionStatusCopy = (message) => {
    if (sectionLockCopyNode) {
      sectionLockCopyNode.textContent = message;
    }
  };

  const syncQuestionTimer = () => {
    const timerNodes = document.querySelectorAll("[data-question-timer]");
    if (!timerNodes.length) {
      return;
    }
    if (questionTimerHandle) {
      window.clearInterval(questionTimerHandle);
      questionTimerHandle = null;
    }
    const activeCard = getActiveCard();
    if (!activeCard) {
      timerNodes.forEach((node) => { node.textContent = "Flexible"; });
      return;
    }
    const suggestedSeconds = Number(activeCard.dataset.questionSeconds || 0);
    if (!suggestedSeconds) {
      timerNodes.forEach((node) => { node.textContent = "Flexible"; });
      return;
    }
    questionSecondsLeft = suggestedSeconds;
    timerNodes.forEach((node) => { node.textContent = formatTimer(questionSecondsLeft); });
    questionTimerHandle = window.setInterval(() => {
      questionSecondsLeft -= 1;
      if (questionSecondsLeft <= 0) {
        timerNodes.forEach((node) => { node.textContent = "Time up"; });
        window.clearInterval(questionTimerHandle);
        questionTimerHandle = null;
        return;
      }
      timerNodes.forEach((node) => { node.textContent = formatTimer(questionSecondsLeft); });
    }, 1000);
  };

  const updateProgress = () => {
    const answeredCount = questionCards.filter(isQuestionAnswered).length;
    const total = questionCards.length || 1;
    const percent = Math.round((answeredCount / total) * 100);
    const degrees = Math.round((answeredCount / total) * 360);

    questionCards.forEach((card) => {
      card.classList.toggle("quiz-question-complete", isQuestionAnswered(card));
    });

    sections.forEach((section, index) => {
      const isCurrent = index === activeSectionIndex;
      const isCompleted = index < activeSectionIndex || (isCurrent && isSectionComplete(section));
      const isLocked = index > activeSectionIndex;
      section.block.classList.toggle("quiz-section-flow-active", isCurrent);
      section.block.classList.toggle("quiz-section-flow-complete", isCompleted);
      section.block.classList.toggle("quiz-section-flow-locked", isLocked);
      if (section.navCard) {
        section.navCard.classList.toggle("quiz-section-nav-active", isCurrent);
        section.navCard.classList.toggle("quiz-section-nav-complete", isCompleted);
        section.navCard.classList.toggle("quiz-section-nav-locked", isLocked);
      }
    });

    jumpButtons.forEach((button) => {
      const buttonSectionIndex = Number(button.dataset.sectionIndex || 0);
      const buttonQuestionIndex = Number(button.dataset.questionIndex || 0);
      const activeCard = getActiveCard();
      const isCurrent = activeCard && buttonQuestionIndex === Number(activeCard.dataset.questionIndex || -1);
      const enabled = buttonSectionIndex === activeSectionIndex;
      button.disabled = !enabled;
      button.classList.toggle("button", isCurrent);
      button.classList.toggle("button-secondary", !isCurrent);
      button.classList.toggle("button-disabled", !enabled);
    });

    if (ring) {
      ring.style.background = `conic-gradient(#2563eb 0deg, #14b8a6 ${degrees}deg, #e2e8f0 ${degrees}deg)`;
    }
    if (progressValue) {
      progressValue.textContent = `${percent}%`;
    }
  };

  const updateVisibility = () => {
    const currentSection = getActiveSection();
    sectionBlocks.forEach((block) => {
      block.style.display = "grid";
    });
    questionCards.forEach((card) => {
      const sameSection = Number(card.dataset.sectionIndex || 0) === activeSectionIndex;
      const sameQuestion = currentSection?.questions[activeQuestionIndex] === card;
      card.style.display = sameSection && sameQuestion ? "grid" : "none";
    });
    if (sectionLabelNode && currentSection) {
      sectionLabelNode.textContent = `${currentSection.navCard?.querySelector("strong")?.textContent || `Section ${activeSectionIndex + 1}`}`;
    }
    const currentCard = getActiveCard();
    if (sectionLockCopyNode && currentSection && currentCard) {
      const questionNumber = currentCard.dataset.sectionQuestionNumber || "1";
      setSectionStatusCopy(
        `You are in ${sectionLabelNode?.textContent || `Section ${activeSectionIndex + 1}`}, question ${questionNumber}. Finish this section before the next section opens.`,
      );
    }
    syncQuestionTimer();
    updateProgress();
    updateControls();
  };

  const updateControls = () => {
    const currentSection = getActiveSection();
    if (!currentSection) {
      return;
    }
    const onFirstQuestion = activeQuestionIndex === 0;
    const onLastQuestionInSection = activeQuestionIndex === currentSection.questions.length - 1;
    const onLastSection = activeSectionIndex === sections.length - 1;
    previousButtons.forEach((previousButton) => {
      previousButton.disabled = onFirstQuestion;
      previousButton.classList.toggle("button-disabled", onFirstQuestion);
    });
    nextButtons.forEach((nextButton) => {
      nextButton.disabled = onLastQuestionInSection && onLastSection;
      nextButton.classList.toggle("button-disabled", onLastQuestionInSection && onLastSection);
      nextButton.textContent = onLastQuestionInSection ? (onLastSection ? "Complete Final Question" : "Unlock Next Section") : "Next Question";
    });
    if (submitButton) {
      const canSubmit = onLastSection && isAssessmentComplete();
      submitButton.disabled = !canSubmit;
      submitButton.classList.toggle("button-disabled", !canSubmit);
    }
    if (submitCopyNode) {
      submitCopyNode.textContent = onLastSection
        ? "Finish the final question and submit. If the exam timer ends first, results open automatically."
        : "Answer every question in this section to unlock the next section. Earlier sections stay locked after you move ahead.";
    }
  };

  const moveWithinSection = (nextIndex) => {
    const currentSection = getActiveSection();
    if (!currentSection) {
      return;
    }
    if (nextIndex < 0 || nextIndex >= currentSection.questions.length) {
      return;
    }
    activeQuestionIndex = nextIndex;
    updateVisibility();
  };

  const moveToNextStep = () => {
    const currentSection = getActiveSection();
    const currentCard = getActiveCard();
    if (!currentSection || !currentCard) {
      return;
    }
    if (!isQuestionAnswered(currentCard)) {
      setSectionStatusCopy("Answer the current question before moving ahead.");
      return;
    }
    if (activeQuestionIndex < currentSection.questions.length - 1) {
      activeQuestionIndex += 1;
      updateVisibility();
      return;
    }
    if (!isSectionComplete(currentSection)) {
      setSectionStatusCopy("Complete every question in this section before unlocking the next section.");
      return;
    }
    if (activeSectionIndex < sections.length - 1) {
      activeSectionIndex += 1;
      activeQuestionIndex = 0;
      updateVisibility();
      return;
    }
    setSectionStatusCopy("Final section complete. Submit the assessment when ready.");
    updateControls();
  };

  const navigateViaJump = (sectionIndex, globalQuestionIndex) => {
    if (sectionIndex !== activeSectionIndex) {
      return;
    }
    const currentSection = getActiveSection();
    const targetIndex = currentSection.questions.findIndex(
      (card) => Number(card.dataset.questionIndex || -1) === globalQuestionIndex,
    );
    if (targetIndex === -1) {
      return;
    }
    activeQuestionIndex = targetIndex;
    updateVisibility();
  };

  const syncExamTimerNodes = (value) => {
    document.querySelectorAll("[data-quiz-main-timer]").forEach((node) => {
      node.textContent = value;
    });
  };

  const startTimer = () => {
    if (totalSecondsLeft <= 0) {
      syncExamTimerNodes("No limit");
      return;
    }
    syncExamTimerNodes(formatTimer(totalSecondsLeft));
    timerHandle = window.setInterval(() => {
      totalSecondsLeft -= 1;
      syncExamTimerNodes(formatTimer(totalSecondsLeft));
      if (totalSecondsLeft <= 0) {
        window.clearInterval(timerHandle);
        timerHandle = null;
        timedAutoSubmit = true;
        if (typeof form.requestSubmit === "function") {
          form.requestSubmit();
        } else {
          form.submit();
        }
      }
    }, 1000);
  };

  const syncInitialPosition = () => {
    const firstIncompleteCard = questionCards.find((card) => !isQuestionAnswered(card));
    if (!firstIncompleteCard) {
      const lastSection = sections[sections.length - 1];
      activeSectionIndex = sections.length - 1;
      activeQuestionIndex = Math.max((lastSection?.questions.length || 1) - 1, 0);
      return;
    }
    activeSectionIndex = Number(firstIncompleteCard.dataset.sectionIndex || 0);
    const currentSection = getActiveSection();
    activeQuestionIndex = Math.max(
      currentSection.questions.findIndex((card) => card === firstIncompleteCard),
      0,
    );
  };

  form.addEventListener("change", () => {
    updateProgress();
    updateControls();
    queueDraftSave();
  });
  form.addEventListener("input", () => {
    updateProgress();
    updateControls();
    queueDraftSave();
  });

  jumpButtons.forEach((button) => {
    button.addEventListener("click", () => {
      navigateViaJump(
        Number(button.dataset.sectionIndex || 0),
        Number(button.dataset.questionIndex || -1),
      );
    });
  });

  previousButtons.forEach((previousButton) => {
    previousButton.addEventListener("click", () => {
      moveWithinSection(activeQuestionIndex - 1);
    });
  });

  nextButtons.forEach((nextButton) => {
    nextButton.addEventListener("click", () => {
      moveToNextStep();
    });
  });

  form.addEventListener("submit", (event) => {
    if (!timedAutoSubmit && !isAssessmentComplete()) {
      event.preventDefault();
      setSectionStatusCopy("Complete every question in every section before submitting.");
    }
  });

  startButton?.addEventListener("click", () => {
    startButton.disabled = true;
    startButton.setAttribute("aria-busy", "true");
    if (instructionModal) {
      instructionModal.hidden = true;
      document.body.style.overflow = "";
    }
    if (startForm) {
      if (typeof startForm.requestSubmit === "function") {
        startForm.requestSubmit();
      } else {
        startForm.submit();
      }
      return;
    }
    startTimer();
    syncQuestionTimer();
  });

  applyDraftAnswers();
  syncInitialPosition();
  if (!instructionModal) {
    startTimer();
    syncQuestionTimer();
  } else {
    document.body.style.overflow = "hidden";
  }
  updateVisibility();
})();
