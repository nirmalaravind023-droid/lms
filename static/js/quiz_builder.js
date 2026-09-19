(() => {
  const builder = document.querySelector("[data-quiz-builder]");
  if (!builder) {
    return;
  }

  const list = builder.querySelector("[data-question-list]");
  const payloadInput = builder.querySelector("[data-questions-payload]");
  const addQuestionButton = builder.querySelector("[data-add-question]");
  const addSectionButton = builder.querySelector("[data-add-section]");
  const questionTemplate = document.getElementById("quiz-question-template");
  const optionTemplate = document.getElementById("quiz-option-template");
  const filterDataNode = document.getElementById("quiz-builder-filter-data");
  const initialQuestionsNode = document.getElementById("quiz-builder-initial-questions");
  const rawFilterData = filterDataNode ? JSON.parse(filterDataNode.textContent) : {};
  const initialQuestions = initialQuestionsNode ? JSON.parse(initialQuestionsNode.textContent) : [];
  const filterData = {
    departments: Array.isArray(rawFilterData.departments) ? rawFilterData.departments : [],
    courses: Array.isArray(rawFilterData.courses) ? rawFilterData.courses : [],
    modules: Array.isArray(rawFilterData.modules) ? rawFilterData.modules : [],
    learners: Array.isArray(rawFilterData.learners) ? rawFilterData.learners : [],
  };
  const departmentSelect = builder.querySelector("#id_department");
  const assessmentTypeSelect = builder.querySelector("#id_assessment_type");
  const courseSelect = builder.querySelector("#id_course");
  const moduleSelect = builder.querySelector("#id_module");
  const assignDepartmentSelect = builder.querySelector("#id_assign_department");
  const assignLearnersSelect = builder.querySelector("#id_assign_learners");
  const moduleHelper = builder.querySelector("[data-module-helper]");
  const flowStatusBadge = builder.querySelector("[data-flow-status-badge]");
  const flowStatusTitle = builder.querySelector("[data-flow-status-title]");
  const flowStatusText = builder.querySelector("[data-flow-status-text]");
  const passScoreInput = builder.querySelector("#id_passing_score");
  const totalTimeInput = builder.querySelector("#id_time_limit_minutes");
  const totalMarksNode = builder.querySelector("[data-summary-total-marks]");
  const negativeMarksNode = builder.querySelector("[data-summary-negative-marks]");
  const totalTimeNode = builder.querySelector("[data-summary-total-time]");
  const passMarkNode = builder.querySelector("[data-summary-pass-mark]");
  let draggedCard = null;

  const findDepartmentName = (departmentId) => {
    if (!departmentId) return "this department";
    return filterData.departments?.find((department) => department.id === departmentId)?.name || "this department";
  };

  const findCourseTitle = (courseId) => {
    if (!courseId) return "This course";
    return filterData.courses?.find((course) => course.id === courseId)?.title || "This course";
  };

  const buildOptions = (select, items, placeholder) => {
    if (!select) return;
    const currentValue = select.value;
    select.innerHTML = "";
    const emptyOption = document.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = placeholder;
    select.appendChild(emptyOption);
    items.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.title || item.label || item.name || item.id;
      select.appendChild(option);
    });
    if ([...select.options].some((option) => option.value === currentValue)) {
      select.value = currentValue;
    }
  };

  const buildMultiSelectOptions = (select, items) => {
    if (!select) return;
    const selectedValues = new Set([...select.selectedOptions].map((option) => option.value));
    select.innerHTML = "";
    items.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.title || item.label || item.name || item.id;
      option.selected = selectedValues.has(item.id);
      select.appendChild(option);
    });
  };

  const setFlowStatus = (badge, title, text) => {
    if (flowStatusBadge) {
      flowStatusBadge.textContent = badge;
    }
    if (flowStatusTitle) {
      flowStatusTitle.textContent = title;
    }
    if (flowStatusText) {
      flowStatusText.textContent = text;
    }
  };

  const markFieldError = (field, hasError) => {
    if (!field) return;
    field.classList.toggle("calendar-input-error", !!hasError);
  };

  const syncDepartmentFilters = (options = {}) => {
    if (!departmentSelect) return;
    const departmentId = departmentSelect.value;
    const forceResetCourse = !!options.forceResetCourse;
    const forceResetModule = !!options.forceResetModule;
    if (forceResetCourse && courseSelect) {
      courseSelect.value = "";
    }
    if (forceResetModule && moduleSelect) {
      moduleSelect.value = "";
    }
    const courseItems = filterData.courses.filter((course) => {
      if (!departmentId) {
        return true;
      }
      return !course.department_id || course.department_id === departmentId;
    });
    buildOptions(courseSelect, courseItems, departmentId ? "Select department course" : "Select course");

    const courseId = courseSelect?.value || "";
    if (moduleSelect) {
      moduleSelect.disabled = !courseId;
    }
    const moduleItems = filterData.modules.filter((module) => {
      // Once a course is chosen, show that course's modules even if department metadata is stale.
      if (courseId) {
        return module.course_id === courseId;
      }
      if (departmentId && module.department_id && module.department_id !== departmentId) {
        return false;
      }
      return !departmentId;
    });
    buildOptions(moduleSelect, moduleItems, courseId ? "Select course module" : "Select module");
    const learnerDepartmentId = assignDepartmentSelect?.value || departmentId;
    const learnerItems = (filterData.learners || []).filter((learner) => {
      if (!learnerDepartmentId) {
        return true;
      }
      return learner.department_id === learnerDepartmentId;
    });
    buildMultiSelectOptions(assignLearnersSelect, learnerItems);
    if (assignDepartmentSelect && !assignDepartmentSelect.value && departmentId) {
      assignDepartmentSelect.value = departmentId;
    }
    if (moduleHelper) {
      const departmentName = findDepartmentName(departmentId);
      const companyCourseCount = (filterData.courses || []).length;
      if (!departmentId) {
        moduleHelper.textContent = "Choose a department, then choose a course to load its module list.";
        setFlowStatus(
          `${companyCourseCount} Course${companyCourseCount === 1 ? "" : "s"}`,
          companyCourseCount
            ? "Courses are already available for quiz connection."
            : "No courses are available yet.",
          companyCourseCount
            ? "Your courses are already built. Choose the department first, then connect this quiz to the right course and module."
            : "Create the first course and module, then return here to connect the quiz.",
        );
      } else if (!courseItems.length) {
        moduleHelper.textContent = companyCourseCount
          ? `No courses are linked to ${departmentName} yet. You already have courses elsewhere, so switch the department here or create one under ${departmentName}.`
          : `No courses are linked to ${departmentName} yet. Create the first course there before building this quiz.`;
        setFlowStatus(
          "Choose Dept",
          companyCourseCount
            ? `Courses exist, but not under ${departmentName}.`
            : `No course exists in ${departmentName} yet.`,
          companyCourseCount
            ? `The LMS already has ${companyCourseCount} course(s). Switch to the matching department or create a new course under ${departmentName}.`
            : `Create a course in ${departmentName} first, then connect the quiz here.`,
        );
      } else if (!courseId) {
        moduleHelper.textContent = "Choose a course to load its modules.";
        setFlowStatus(
          `${courseItems.length} Match${courseItems.length === 1 ? "" : "es"}`,
          `${courseItems.length} course(s) are available in ${departmentName}.`,
          "Select the course you want this quiz to belong to. After that, the module list will load automatically.",
        );
      } else {
        moduleHelper.textContent = moduleItems.length
          ? `${moduleItems.length} module(s) available in this course flow.`
          : "No modules available for this course yet. Create the module first.";
        setFlowStatus(
          moduleItems.length ? `${moduleItems.length} Module${moduleItems.length === 1 ? "" : "s"}` : "No Module",
          moduleItems.length
            ? `${findCourseTitle(courseId)} is ready for quiz connection.`
            : `${findCourseTitle(courseId)} needs a module before quiz connection.`,
          moduleItems.length
            ? "This quiz will be saved against the selected course and module."
            : "The course already exists. Add at least one module, then connect the quiz here.",
        );
      }
    }
  };

  const updateSummary = () => {
    const questions = [...list.querySelectorAll("[data-question-card]")];
    const totalMarks = questions.reduce((sum, card) => sum + Number(card.querySelector("[data-question-marks]")?.value || 0), 0);
    const totalNegative = questions.reduce((sum, card) => sum + Number(card.querySelector("[data-question-negative-marks]")?.value || 0), 0);
    const totalQuestionSeconds = questions.reduce((sum, card) => sum + Number(card.querySelector("[data-question-seconds]")?.value || 0), 0);
    const passingPercent = Number(passScoreInput?.value || 0);
    const requiredMarks = totalMarks ? Math.ceil((totalMarks * passingPercent) / 100) : 0;
    const totalMinutes = Number(totalTimeInput?.value || 0);
    if (totalMarksNode) totalMarksNode.textContent = `${totalMarks}`;
    if (negativeMarksNode) negativeMarksNode.textContent = `${totalNegative}`;
    if (totalTimeNode) {
      const guidedMinutes = totalQuestionSeconds ? `${Math.ceil(totalQuestionSeconds / 60)} min guided` : "0 min guided";
      totalTimeNode.textContent = totalMinutes ? `${totalMinutes} min total / ${guidedMinutes}` : guidedMinutes;
    }
    if (passMarkNode) passMarkNode.textContent = `${requiredMarks} / ${totalMarks || 0}`;
  };

  const syncPayload = () => {
    const questions = [...list.querySelectorAll("[data-question-card]")].map((card) => {
      refreshSectionBanner(card);
      const type = card.querySelector("[data-question-type]")?.value || "single_choice";
      const options = [...card.querySelectorAll("[data-option-row]")].map((row) => ({
        text: row.querySelector("[data-option-text]")?.value || "",
        is_correct: row.querySelector("[data-option-correct]")?.checked || false,
      }));
      return {
        prompt: card.querySelector("[data-question-prompt]")?.value || "",
        section_title: card.querySelector("[data-question-section]")?.value || "",
        question_type: type,
        marks: Number(card.querySelector("[data-question-marks]")?.value || 1),
        negative_marks: Number(card.querySelector("[data-question-negative-marks]")?.value || 0),
        suggested_seconds: Number(card.querySelector("[data-question-seconds]")?.value || 0),
        explanation: card.querySelector("[data-question-explanation]")?.value || "",
        correct_answer_text: card.querySelector("[data-question-correct-text]")?.value || "",
        style_config: {
          font_family: card.querySelector("[data-style-font-family]")?.value || "",
          color: card.querySelector("[data-style-color]")?.value || "",
          spacing: Number(card.querySelector("[data-style-spacing]")?.value || 14),
        },
        options: ["short_answer", "essay"].includes(type) ? [] : options,
      };
    });
    payloadInput.value = JSON.stringify(questions);
    updateSummary();
  };

  const refreshHeadings = () => {
    [...list.querySelectorAll("[data-question-card]")].forEach((card, index) => {
      const heading = card.querySelector("[data-question-heading]");
      if (heading) {
        heading.textContent = `Question ${index + 1}`;
      }
    });
  };

  const moveQuestionCard = (card, direction) => {
    if (!card) return;
    const sibling = direction === "up" ? card.previousElementSibling : card.nextElementSibling;
    if (!sibling) return;
    if (direction === "up") {
      list.insertBefore(card, sibling);
    } else {
      list.insertBefore(sibling, card);
    }
    refreshHeadings();
    syncPayload();
  };

  const numberToSectionLetters = (value) => {
    let number = Math.max(1, value);
    let label = "";
    while (number > 0) {
      const remainder = (number - 1) % 26;
      label = String.fromCharCode(65 + remainder) + label;
      number = Math.floor((number - 1) / 26);
    }
    return label;
  };

  const getNextSectionTitle = () => {
    const sectionValues = [...list.querySelectorAll("[data-question-section]")]
      .map((input) => input.value.trim())
      .filter(Boolean);
    const matchedIndexes = sectionValues
      .map((value) => {
        const match = value.match(/^Section\s+([A-Z]+)$/i);
        if (!match) return null;
        const letters = match[1].toUpperCase();
        let total = 0;
        for (let index = 0; index < letters.length; index += 1) {
          total = total * 26 + (letters.charCodeAt(index) - 64);
        }
        return total;
      })
      .filter((value) => value !== null);
    const nextIndex = matchedIndexes.length ? Math.max(...matchedIndexes) + 1 : sectionValues.length + 1;
    return `Section ${numberToSectionLetters(nextIndex)}`;
  };

  const refreshSectionBanner = (card) => {
    const sectionValue = card.querySelector("[data-question-section]")?.value?.trim() || "";
    const sectionBanner = card.querySelector("[data-question-section-banner]");
    const sectionLabel = card.querySelector("[data-question-section-label]");
    if (!sectionBanner || !sectionLabel) {
      return;
    }
    if (sectionValue) {
      sectionLabel.textContent = sectionValue;
      sectionBanner.hidden = false;
    } else {
      sectionBanner.hidden = true;
    }
  };

  const toggleOptionShell = (card) => {
    const type = card.querySelector("[data-question-type]")?.value;
    const optionShell = card.querySelector("[data-option-shell]");
    const textAnswerWrap = card.querySelector("[data-text-answer-wrap]");
    const typePreview = card.querySelector("[data-question-type-preview]");
    const typeDescription = card.querySelector("[data-question-type-description]");
    if (!optionShell) {
      return;
    }
    optionShell.hidden = ["short_answer", "essay"].includes(type);
    if (textAnswerWrap) {
      textAnswerWrap.hidden = type !== "short_answer";
    }
    if (typePreview) {
      const labels = {
        single_choice: "MCQ",
        multiple_choice: "MSQ",
        true_false: "True / False",
        short_answer: "Fill In",
        essay: "Descriptive",
      };
      typePreview.textContent = labels[type] || "Question";
    }
    if (typeDescription) {
      const descriptions = {
        single_choice: "One correct option is allowed for this question.",
        multiple_choice: "Multiple correct options can be marked for this question.",
        true_false: "Learner chooses the true or false statement.",
        short_answer: "Learner types the answer and it can score instantly if it matches.",
        essay: "Learner writes a descriptive answer for HR/admin review.",
      };
      typeDescription.textContent = descriptions[type] || "";
    }
  };

  const addOption = (card, seed = {}) => {
    const node = optionTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector("[data-option-text]").value = seed.text || "";
    node.querySelector("[data-option-correct]").checked = !!seed.is_correct;
    node.querySelector("[data-remove-option]").addEventListener("click", () => {
      node.remove();
      syncPayload();
    });
    node.querySelector("[data-option-text]").addEventListener("input", syncPayload);
    node.querySelector("[data-option-correct]").addEventListener("change", syncPayload);
    card.querySelector("[data-option-list]").appendChild(node);
    syncPayload();
  };

  const setDragEvents = (node) => {
    node.draggable = true;
    node.addEventListener("dragstart", (event) => {
      draggedCard = node;
      node.classList.add("is-dragging");
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
      }
    });
    node.addEventListener("dragend", () => {
      node.classList.remove("is-dragging");
      draggedCard = null;
      refreshHeadings();
      syncPayload();
    });
  };

  const addQuestion = (seed = {}) => {
    const node = questionTemplate.content.firstElementChild.cloneNode(true);
    const addOptionButton = node.querySelector("[data-add-option]");
    const removeQuestionButton = node.querySelector("[data-remove-question]");
    const moveUpButton = node.querySelector("[data-move-question-up]");
    const moveDownButton = node.querySelector("[data-move-question-down]");
    const questionType = node.querySelector("[data-question-type]");
    node.querySelector("[data-question-prompt]").value = seed.prompt || "";
    node.querySelector("[data-question-section]").value = seed.section_title || "";
    node.querySelector("[data-question-type]").value = seed.question_type || "single_choice";
    node.querySelector("[data-question-marks]").value = seed.marks ?? 1;
    node.querySelector("[data-question-negative-marks]").value = seed.negative_marks ?? 0;
    node.querySelector("[data-question-seconds]").value = seed.suggested_seconds ?? 0;
    node.querySelector("[data-question-explanation]").value = seed.explanation || "";
    node.querySelector("[data-question-correct-text]").value = seed.correct_answer_text || "";
    node.querySelector("[data-style-font-family]").value = seed.style_config?.font_family || "";
    node.querySelector("[data-style-color]").value = seed.style_config?.color || "#0f172a";
    node.querySelector("[data-style-spacing]").value = seed.style_config?.spacing ?? 14;

    removeQuestionButton.addEventListener("click", () => {
      node.remove();
      refreshHeadings();
      syncPayload();
    });

    moveUpButton?.addEventListener("click", () => moveQuestionCard(node, "up"));
    moveDownButton?.addEventListener("click", () => moveQuestionCard(node, "down"));

    addOptionButton.addEventListener("click", () => addOption(node));
    questionType.addEventListener("change", () => {
      toggleOptionShell(node);
      syncPayload();
    });

    node.querySelectorAll("textarea, input, select").forEach((field) => {
      field.addEventListener("input", syncPayload);
      field.addEventListener("change", syncPayload);
    });

    setDragEvents(node);
    list.appendChild(node);
    const selectedType = node.querySelector("[data-question-type]").value;
    const seededOptions = Array.isArray(seed.options) ? seed.options : [];
    if (!["short_answer", "essay"].includes(selectedType)) {
      if (seededOptions.length) {
        seededOptions.forEach((option) => addOption(node, option));
      } else if (selectedType === "true_false") {
        addOption(node, { text: "True", is_correct: true });
        addOption(node, { text: "False", is_correct: false });
      } else {
        addOption(node, { text: "", is_correct: true });
        addOption(node, { text: "", is_correct: false });
      }
    }
    toggleOptionShell(node);
    refreshSectionBanner(node);
    refreshHeadings();
    syncPayload();
  };

  list.addEventListener("dragover", (event) => {
    event.preventDefault();
    if (!draggedCard) return;
    const cards = [...list.querySelectorAll("[data-question-card]:not(.is-dragging)")];
    const nextCard = cards.find((card) => {
      const box = card.getBoundingClientRect();
      return event.clientY < box.top + box.height / 2;
    });
    if (nextCard) {
      list.insertBefore(draggedCard, nextCard);
    } else {
      list.appendChild(draggedCard);
    }
  });

  addQuestionButton?.addEventListener("click", () => addQuestion());
  addSectionButton?.addEventListener("click", () => addQuestion({ section_title: getNextSectionTitle() }));
  builder.addEventListener("submit", (event) => {
    syncPayload();
    const departmentId = departmentSelect?.value || "";
    const courseId = courseSelect?.value || "";
    const moduleId = moduleSelect?.value || "";
    const companyCourseCount = (filterData.courses || []).length;
    const courseItems = filterData.courses.filter((course) => {
      if (!departmentId) {
        return true;
      }
      return !course.department_id || course.department_id === departmentId;
    });
    const moduleItems = filterData.modules.filter((module) => {
      if (courseId) {
        return module.course_id === courseId;
      }
      if (departmentId && module.department_id && module.department_id !== departmentId) {
        return false;
      }
      return !departmentId;
    });

    markFieldError(departmentSelect, false);
    markFieldError(courseSelect, false);
    markFieldError(moduleSelect, false);

    if (!departmentId && companyCourseCount) {
      event.preventDefault();
      markFieldError(departmentSelect, true);
      setFlowStatus(
        `${companyCourseCount} Course${companyCourseCount === 1 ? "" : "s"}`,
        "Choose the department before saving the quiz.",
        "Your courses already exist. Select the department that owns the course you want to connect.",
      );
      departmentSelect?.focus();
      window.alert("Choose the department first. Your courses are already built.");
      return;
    }

    if (departmentId && !courseId && courseItems.length) {
      event.preventDefault();
      markFieldError(courseSelect, true);
      setFlowStatus(
        `${courseItems.length} Match${courseItems.length === 1 ? "" : "es"}`,
        "Choose the course before saving the quiz.",
        "The department already has course data. Pick the course this quiz should belong to.",
      );
      courseSelect?.focus();
      window.alert("Choose the course for this quiz before saving.");
      return;
    }

    if (departmentId && courseId && !moduleId && moduleItems.length) {
      event.preventDefault();
      markFieldError(moduleSelect, true);
      setFlowStatus(
        `${moduleItems.length} Module${moduleItems.length === 1 ? "" : "s"}`,
        "Choose the module before saving the quiz.",
        "The course is already connected. Pick the module this quiz should sit under in the learning flow.",
      );
      moduleSelect?.focus();
      window.alert("Choose the module for this quiz before saving.");
      return;
    }

    if (assessmentTypeSelect?.value === "test") {
      const missingSection = [...list.querySelectorAll("[data-question-card]")].some((card) => {
        const value = card.querySelector("[data-question-section]")?.value?.trim() || "";
        return !value;
      });
      if (missingSection) {
        event.preventDefault();
        window.alert("Test mode needs section name for every question.");
      }
    }
  });
  passScoreInput?.addEventListener("input", updateSummary);
  totalTimeInput?.addEventListener("input", updateSummary);
  departmentSelect?.addEventListener("change", () => syncDepartmentFilters({ forceResetCourse: true, forceResetModule: true }));
  courseSelect?.addEventListener("change", () => syncDepartmentFilters({ forceResetModule: true }));
  assignDepartmentSelect?.addEventListener("change", () => syncDepartmentFilters());
  syncDepartmentFilters();
  if (Array.isArray(initialQuestions) && initialQuestions.length) {
    initialQuestions.forEach((question) => addQuestion(question));
  } else {
    addQuestion();
  }
  updateSummary();
})();
