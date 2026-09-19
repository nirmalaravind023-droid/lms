(() => {
  const lessonType =
    document.querySelector("[data-lesson-type-field]") ||
    document.querySelector("[data-lesson-type-field-wrap] select");
  const currentTypeBadge = document.querySelector("[data-current-lesson-type]");
  const articleImageInput = document.querySelector("#id_article_image");
  const articleImagePreview = document.querySelector("[data-article-image-preview]");
  const toolbar = document.querySelector("[data-rich-toolbar]");
  const richPreview = document.querySelector("[data-rich-preview]");
  const tableModal = document.querySelector("[data-table-modal]");
  const tableRowsInput = document.querySelector("[data-table-rows]");
  const tableColsInput = document.querySelector("[data-table-cols]");
  const tableGrid = document.querySelector("[data-table-grid]");
  const tableHeaderBgInput = document.querySelector("[data-table-header-bg]");
  const tableHeaderTextInput = document.querySelector("[data-table-header-text]");
  const tableTotalBgInput = document.querySelector("[data-table-total-bg]");
  const tableTotalTextInput = document.querySelector("[data-table-total-text]");
  const tableBuildButton = document.querySelector("[data-table-build]");
  const tableClearButton = document.querySelector("[data-table-clear]");
  const tableApplyPasteButton = document.querySelector("[data-table-apply-paste]");
  const tableInsertButton = document.querySelector("[data-table-insert]");
  const tableCloseButton = document.querySelector("[data-table-close]");
  const tablePasteInput = document.querySelector("[data-table-paste]");
  const tableAddRowButton = document.querySelector("[data-table-add-row]");
  const tableAddColButton = document.querySelector("[data-table-add-col]");
  const tableRemoveRowButton = document.querySelector("[data-table-remove-row]");
  const tableRemoveColButton = document.querySelector("[data-table-remove-col]");
  const isEditorShortcut = (event, key) => event.ctrlKey && !event.shiftKey && !event.altKey && event.key.toLowerCase() === key;
  const isAltShiftShortcut = (event, key) => event.altKey && event.shiftKey && !event.ctrlKey && event.key === key;
  const isCtrlAltShortcut = (event, key) => event.ctrlKey && event.altKey && !event.shiftKey && event.key.toLowerCase() === key;
  let draggedTableRow = null;
  let lastSelectionStart = 0;
  let lastSelectionEnd = 0;
  let activeTableRange = null;

  const tableColorMeta = () => ({
    header_bg: tableHeaderBgInput ? tableHeaderBgInput.value : "#ffffff",
    header_text: tableHeaderTextInput ? tableHeaderTextInput.value : "#0f172a",
    total_bg: tableTotalBgInput ? tableTotalBgInput.value : "#f3f6fb",
    total_text: tableTotalTextInput ? tableTotalTextInput.value : "#0f172a",
  });

  const tableMetaLine = () => {
    const meta = tableColorMeta();
    return `{{table:header_bg=${meta.header_bg};header_text=${meta.header_text};total_bg=${meta.total_bg};total_text=${meta.total_text}}}`;
  };

  const applyTableMetaToInputs = (meta) => {
    if (tableHeaderBgInput) {
      tableHeaderBgInput.value = meta && meta.header_bg ? meta.header_bg : "#ffffff";
    }
    if (tableHeaderTextInput) {
      tableHeaderTextInput.value = meta && meta.header_text ? meta.header_text : "#0f172a";
    }
    if (tableTotalBgInput) {
      tableTotalBgInput.value = meta && meta.total_bg ? meta.total_bg : "#f3f6fb";
    }
    if (tableTotalTextInput) {
      tableTotalTextInput.value = meta && meta.total_text ? meta.total_text : "#0f172a";
    }
  };

  const rememberSelection = (textarea) => {
    lastSelectionStart = textarea.selectionStart || 0;
    lastSelectionEnd = textarea.selectionEnd || 0;
  };

  const wrapSelection = (textarea, prefix, suffix = prefix, placeholder = "text") => {
    const start = textarea.selectionStart ?? lastSelectionStart ?? 0;
    const end = textarea.selectionEnd ?? lastSelectionEnd ?? 0;
    const selected = textarea.value.slice(start, end) || placeholder;
    const replacement = `${prefix}${selected}${suffix}`;
    textarea.setRangeText(replacement, start, end, "end");
    textarea.focus();
    rememberSelection(textarea);
  };

  const prefixLines = (textarea, prefix, placeholder) => {
    const start = textarea.selectionStart ?? lastSelectionStart ?? 0;
    const end = textarea.selectionEnd ?? lastSelectionEnd ?? 0;
    const selected = textarea.value.slice(start, end) || placeholder;
    const replacement = selected
      .split("\n")
      .map((line, index) => `${prefix(index)}${line || "item"}`)
      .join("\n");
    textarea.setRangeText(replacement, start, end, "end");
    textarea.focus();
    rememberSelection(textarea);
  };

  const insertTable = (textarea) => {
    const start = textarea.selectionStart ?? lastSelectionStart ?? 0;
    const end = textarea.selectionEnd ?? lastSelectionEnd ?? 0;
    const block = "| Column 1 | Column 2 |\n| Value A | Value B |";
    textarea.setRangeText(block, start, end, "end");
    textarea.focus();
    rememberSelection(textarea);
  };

  const readTableData = () => {
    if (!tableGrid) {
      return [];
    }
    return Array.from(tableGrid.querySelectorAll("[data-table-row-wrap]")).map((rowWrap) =>
      Array.from(rowWrap.querySelectorAll("[data-table-cell]")).map((input) => input.value || "")
    );
  };

  const setTableDimensions = (rows, cols) => {
    if (tableRowsInput) {
      tableRowsInput.value = String(Math.min(8, Math.max(1, rows)));
    }
    if (tableColsInput) {
      tableColsInput.value = String(Math.min(6, Math.max(1, cols)));
    }
  };

  const tableLinesToData = (lines) =>
    lines.map((line) =>
      line
        .trim()
        .replace(/^\|/, "")
        .replace(/\|$/, "")
        .split("|")
        .map((cell) => cell.trim())
    );

  const findEditableTable = (text, cursorIndex) => {
    const regex = /\|.+\|(?:\r?\n\|.+\|)*/g;
    const matches = [];
    let match;
    while ((match = regex.exec(text)) !== null) {
      matches.push(match);
    }
    if (!matches.length) {
      return null;
    }
    let chosen = matches[matches.length - 1];
    for (const match of matches) {
      const start = match.index || 0;
      const end = start + match[0].length;
      if (cursorIndex >= start && cursorIndex <= end) {
        chosen = match;
        break;
      }
    }
    const tableStart = chosen.index || 0;
    const beforeText = text.slice(0, tableStart);
    const beforeLines = beforeText.split(/\r?\n/);
    const previousLine = beforeLines.length ? beforeLines[beforeLines.length - 1].trim() : "";
    const metaMatch = previousLine.match(/^\{\{table:(.+)\}\}$/);
    let meta = null;
    let start = tableStart;
    if (metaMatch) {
      meta = {};
      metaMatch[1].split(";").forEach((pair) => {
        const parts = pair.split("=");
        if (parts.length === 2) {
          meta[parts[0].trim()] = parts[1].trim();
        }
      });
      start = tableStart - previousLine.length - 1;
    }
    return {
      start,
      end: tableStart + chosen[0].length,
      data: tableLinesToData(chosen[0].split(/\r?\n/).filter(Boolean)),
      meta,
    };
  };

  const buildTableGrid = (seedData = null) => {
    if (!tableGrid || !tableRowsInput || !tableColsInput) {
      return;
    }
    const rows = Math.min(8, Math.max(1, Number(tableRowsInput.value) || 2));
    const cols = Math.min(6, Math.max(1, Number(tableColsInput.value) || 2));
    tableRowsInput.value = String(rows);
    tableColsInput.value = String(cols);
    const currentData = seedData || readTableData();
    tableGrid.innerHTML = "";
    for (let row = 0; row < rows; row += 1) {
      const rowWrap = document.createElement("div");
      rowWrap.className = "authoring-table-row-wrap";
      rowWrap.dataset.tableRowWrap = "true";
      rowWrap.draggable = true;
      rowWrap.dataset.row = String(row);
      const handle = document.createElement("button");
      handle.type = "button";
      handle.className = "authoring-table-row-handle";
      handle.textContent = row === 0 ? "Headers" : `Row ${row}`;
      handle.title = row === 0 ? "Header row" : "Drag to reorder row";
      rowWrap.appendChild(handle);
      const cellsWrap = document.createElement("div");
      cellsWrap.className = "authoring-table-row-cells";
      cellsWrap.style.gridTemplateColumns = `repeat(${cols}, minmax(120px, 1fr))`;
      for (let col = 0; col < cols; col += 1) {
        const input = document.createElement("input");
        input.type = "text";
        input.className = "authoring-table-cell";
        input.dataset.tableCell = "true";
        input.dataset.row = String(row);
        input.dataset.col = String(col);
        input.placeholder = row === 0 ? `Header ${col + 1}` : `Value`;
        if (row === 0) {
          input.classList.add("authoring-table-cell-header");
        }
        input.value = (currentData[row] && currentData[row][col]) || "";
        cellsWrap.appendChild(input);
      }
      rowWrap.appendChild(cellsWrap);
      tableGrid.appendChild(rowWrap);
    }
  };

  const applyPastedTable = () => {
    if (!tablePasteInput || !tableRowsInput || !tableColsInput || !tableGrid) {
      return;
    }
    const raw = (tablePasteInput.value || "").trim();
    if (!raw) {
      return;
    }
    const rows = raw
      .split(/\r?\n/)
      .map((line) => line.split("\t").map((cell) => cell.trim()))
      .filter((row) => row.some(Boolean));
    if (!rows.length) {
      return;
    }
    const rowCount = Math.min(8, rows.length);
    const colCount = Math.min(6, Math.max(...rows.map((row) => row.length)));
    setTableDimensions(rowCount, colCount);
    buildTableGrid(rows.slice(0, rowCount).map((row) => row.slice(0, colCount)));
  };

  const openTableModal = (initialTable = null) => {
    if (!tableModal) {
      return;
    }
    tableModal.hidden = false;
    activeTableRange = initialTable ? { start: initialTable.start, end: initialTable.end } : null;
    applyTableMetaToInputs(initialTable ? initialTable.meta : null);
    if (initialTable && initialTable.data && initialTable.data.length) {
      const rows = initialTable.data.length;
      const cols = Math.max(...initialTable.data.map((row) => row.length), 1);
      setTableDimensions(rows, cols);
      buildTableGrid(initialTable.data);
    } else {
      buildTableGrid();
    }
    const firstInput = tableGrid ? tableGrid.querySelector("input") : null;
    if (firstInput) {
      firstInput.focus();
    }
  };

  const closeTableModal = () => {
    if (!tableModal) {
      return;
    }
    tableModal.hidden = true;
    activeTableRange = null;
  };

  const insertBuiltTable = (textarea) => {
    if (!tableGrid || !tableRowsInput || !tableColsInput) {
      insertTable(textarea);
      return;
    }
    const rows = Number(tableRowsInput.value) || 2;
    const cols = Number(tableColsInput.value) || 2;
    const lines = [tableMetaLine()];
    const data = readTableData();
    for (let row = 0; row < rows; row += 1) {
      const cells = [];
      for (let col = 0; col < cols; col += 1) {
        const fallback = row === 0 ? `Header ${col + 1}` : `Value ${row}-${col + 1}`;
        cells.push((((data[row] && data[row][col]) || "").trim()) || fallback);
      }
      lines.push(`| ${cells.join(" | ")} |`);
    }
    const replacement = lines.join("\n");
    if (activeTableRange) {
      textarea.setRangeText(replacement, activeTableRange.start, activeTableRange.end, "end");
    } else {
      const start = textarea.selectionStart || 0;
      const end = textarea.selectionEnd || 0;
      const prefix = textarea.value && !textarea.value.endsWith("\n") ? "\n" : "";
      const suffix = "\n";
      textarea.setRangeText(`${prefix}${replacement}${suffix}`, start, end, "end");
    }
    textarea.focus();
    rememberSelection(textarea);
    closeTableModal();
  };

  const escapeHtml = (value) =>
    value
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

  const applyInlineFormatting = (text) =>
    text
      .replace(/`(.+?)`/g, "<code>$1</code>")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/__(.+?)__/g, "<u>$1</u>");

  const renderRichPreview = (value) => {
    if (!richPreview) {
      return;
    }
    const lines = escapeHtml(value || "").split("\n");
    const rendered = [];
    let paragraph = [];
    let inBullets = false;
    let inNumbers = false;
    let inTable = false;
    let tableRowIndex = 0;

    const flushParagraph = () => {
      if (paragraph.length) {
        rendered.push(`<p>${paragraph.join("<br>")}</p>`);
        paragraph = [];
      }
    };

    const closeLists = () => {
      if (inBullets) {
        rendered.push("</ul>");
        inBullets = false;
      }
      if (inNumbers) {
        rendered.push("</ol>");
        inNumbers = false;
      }
    };

    const closeTable = () => {
      if (inTable) {
        rendered.push("</tbody></table>");
        inTable = false;
        tableRowIndex = 0;
      }
    };

    lines.forEach((rawLine) => {
      const stripped = rawLine.trim();
      if (!stripped) {
        flushParagraph();
        closeLists();
        closeTable();
        return;
      }

      if (stripped.startsWith("### ")) {
        flushParagraph();
        closeLists();
        closeTable();
        rendered.push(`<h4>${applyInlineFormatting(stripped.slice(4))}</h4>`);
        return;
      }
      if (stripped.startsWith("## ")) {
        flushParagraph();
        closeLists();
        closeTable();
        rendered.push(`<h3>${applyInlineFormatting(stripped.slice(3))}</h3>`);
        return;
      }
      if (stripped.startsWith("# ")) {
        flushParagraph();
        closeLists();
        closeTable();
        rendered.push(`<h2>${applyInlineFormatting(stripped.slice(2))}</h2>`);
        return;
      }

      if (stripped.startsWith("- ") || stripped.startsWith("* ")) {
        flushParagraph();
        closeTable();
        if (!inBullets) {
          closeLists();
          rendered.push("<ul>");
          inBullets = true;
        }
        rendered.push(`<li>${applyInlineFormatting(stripped.slice(2))}</li>`);
        return;
      }

      const orderedMatch = stripped.match(/^\d+\.\s+(.+)$/);
      if (orderedMatch) {
        flushParagraph();
        closeTable();
        if (!inNumbers) {
          closeLists();
          rendered.push("<ol>");
          inNumbers = true;
        }
        rendered.push(`<li>${applyInlineFormatting(orderedMatch[1])}</li>`);
        return;
      }

      if (stripped.includes("|") && (stripped.match(/\|/g) || []).length >= 2) {
        const cells = stripped
          .replace(/^\|/, "")
          .replace(/\|$/, "")
          .split("|")
          .map((cell) => cell.trim());
        if (cells.some(Boolean)) {
          flushParagraph();
          closeLists();
          if (!inTable) {
            rendered.push('<table class="lesson-rich-table"><tbody>');
            inTable = true;
            tableRowIndex = 0;
          }
          const isHeaderRow = tableRowIndex === 0;
          const isTotalRow = cells.some((cell) => cell.toLowerCase().indexOf("total") === 0);
          const cellTag = isHeaderRow ? "th" : "td";
          const rowClass = isTotalRow ? ' class="lesson-rich-table-row-total"' : "";
          const meta = tableColorMeta();
          let styleAttr = "";
          if (isHeaderRow) {
            styleAttr = ` style="background:${meta.header_bg};color:${meta.header_text};font-weight:700;"`;
          } else if (isTotalRow) {
            styleAttr = ` style="background:${meta.total_bg};color:${meta.total_text};font-weight:700;"`;
          }
          rendered.push(`<tr${rowClass}>${cells.map((cell) => `<${cellTag}${styleAttr}>${applyInlineFormatting(cell)}</${cellTag}>`).join("")}</tr>`);
          tableRowIndex += 1;
          return;
        }
      }

      closeLists();
      closeTable();
      paragraph.push(applyInlineFormatting(stripped));
    });

    flushParagraph();
    closeLists();
    closeTable();
    richPreview.innerHTML = rendered.join("") || '<p class="muted">Start typing article content to preview it here.</p>';
  };

  const resizeTable = (nextRows, nextCols) => {
    const current = readTableData();
    const safeRows = Math.min(8, Math.max(1, nextRows));
    const safeCols = Math.min(6, Math.max(1, nextCols));
    const resized = Array.from({ length: safeRows }, (_, rowIndex) =>
      Array.from({ length: safeCols }, (_, colIndex) => (current[rowIndex] && current[rowIndex][colIndex]) || "")
    );
    setTableDimensions(safeRows, safeCols);
    buildTableGrid(resized);
  };

  const clearTableGrid = () => {
    if (!tableRowsInput || !tableColsInput) {
      return;
    }
    const rows = Number(tableRowsInput.value) || 2;
    const cols = Number(tableColsInput.value) || 2;
    buildTableGrid(
      Array.from({ length: rows }, () => Array.from({ length: cols }, () => ""))
    );
    if (tablePasteInput) {
      tablePasteInput.value = "";
    }
  };

  const updatePreviewImage = () => {
    if (!articleImageInput || !articleImagePreview) {
      return;
    }
    const file = articleImageInput.files && articleImageInput.files[0];
    if (!file) {
      const existingImage = articleImagePreview.dataset.existingImage;
      if (existingImage) {
        articleImagePreview.innerHTML = "";
        const image = document.createElement("img");
        image.src = existingImage;
        image.alt = "Current article banner";
        articleImagePreview.appendChild(image);
        return;
      }
      articleImagePreview.innerHTML = '<span class="muted">Article image preview will appear here.</span>';
      return;
    }
    const fileReader = new FileReader();
    fileReader.onload = (event) => {
      articleImagePreview.innerHTML = "";
      const image = document.createElement("img");
      image.src = (event.target && event.target.result) || "";
      image.alt = file.name;
      articleImagePreview.appendChild(image);
    };
    fileReader.readAsDataURL(file);
  };

  const syncPanels = () => {
    if (!lessonType) {
      return;
    }
    const value = lessonType.value;
    document.querySelectorAll("[data-lesson-panel]").forEach((panel) => {
      const allowed = (panel.dataset.lessonPanel || "").split(",");
      panel.classList.toggle("lesson-panel-hidden", !allowed.includes(value));
    });
    if (currentTypeBadge) {
      const selected = lessonType.options[lessonType.selectedIndex];
      currentTypeBadge.textContent = selected ? selected.text : value;
    }
  };

  if (lessonType) {
    lessonType.addEventListener("change", syncPanels);
    syncPanels();
  }
  if (articleImageInput) {
    articleImageInput.addEventListener("change", updatePreviewImage);
    updatePreviewImage();
  }

  if (toolbar) {
    const targetId = toolbar.dataset.target;
    const textarea = targetId ? document.getElementById(targetId) : null;
    const triggerAction = (action) => {
      if (!textarea) {
        return;
      }
      if (action === "bold") {
        wrapSelection(textarea, "**");
      } else if (action === "italic") {
        wrapSelection(textarea, "*");
      } else if (action === "underline") {
        wrapSelection(textarea, "__");
      } else if (action === "bullet") {
        prefixLines(textarea, () => "- ", "item");
      } else if (action === "number") {
        prefixLines(textarea, (index) => `${index + 1}. `, "step");
      } else if (action === "heading") {
        prefixLines(textarea, () => "# ", "Heading");
      } else if (action === "table") {
        openTableModal();
      } else if (action === "edit-table") {
        const existingTable = findEditableTable(textarea.value, textarea.selectionStart || lastSelectionStart || 0);
        openTableModal(existingTable);
      }
    };
    if (textarea) {
      textarea.addEventListener("select", () => rememberSelection(textarea));
      textarea.addEventListener("click", () => rememberSelection(textarea));
      textarea.addEventListener("keyup", () => rememberSelection(textarea));

      toolbar.addEventListener("mousedown", (event) => {
        const button = event.target.closest("[data-rich-action]");
        if (button) {
          event.preventDefault();
        }
      });

      toolbar.addEventListener("click", (event) => {
        const button = event.target.closest("[data-rich-action]");
        if (!button) {
          return;
        }
        triggerAction(button.dataset.richAction);
        renderRichPreview(textarea.value);
      });

      textarea.addEventListener("keydown", (event) => {
        let action = "";
        if (isEditorShortcut(event, "b")) {
          action = "bold";
        } else if (isEditorShortcut(event, "i")) {
          action = "italic";
        } else if (isEditorShortcut(event, "u")) {
          action = "underline";
        } else if (isAltShiftShortcut(event, "7")) {
          action = "bullet";
        } else if (isAltShiftShortcut(event, "8")) {
          action = "number";
        } else if (isCtrlAltShortcut(event, "h")) {
          action = "heading";
        } else if (isCtrlAltShortcut(event, "t")) {
          action = "table";
        }
        if (!action) {
          return;
        }
        event.preventDefault();
        triggerAction(action);
        renderRichPreview(textarea.value);
      });

      textarea.addEventListener("input", () => {
        rememberSelection(textarea);
        renderRichPreview(textarea.value);
      });

      rememberSelection(textarea);
      renderRichPreview(textarea.value);

      if (tableBuildButton) {
        tableBuildButton.addEventListener("click", () => buildTableGrid(readTableData()));
      }
      if (tableClearButton) {
        tableClearButton.addEventListener("click", () => {
          if (tablePasteInput) {
            tablePasteInput.value = "";
          }
          buildTableGrid(
            Array.from({ length: Number(tableRowsInput && tableRowsInput.value) || 2 }, () =>
              Array.from({ length: Number(tableColsInput && tableColsInput.value) || 2 }, () => "")
            )
          );
        });
      }
      if (tableApplyPasteButton) {
        tableApplyPasteButton.addEventListener("click", applyPastedTable);
      }
      if (tableCloseButton) {
        tableCloseButton.addEventListener("click", closeTableModal);
      }
      if (tableInsertButton) {
        tableInsertButton.addEventListener("click", () => {
          insertBuiltTable(textarea);
          renderRichPreview(textarea.value);
        });
      }
      if (tableRowsInput) {
        tableRowsInput.addEventListener("change", () => resizeTable(Number(tableRowsInput.value) || 2, Number(tableColsInput && tableColsInput.value) || 2));
      }
      if (tableColsInput) {
        tableColsInput.addEventListener("change", () => resizeTable(Number(tableRowsInput && tableRowsInput.value) || 2, Number(tableColsInput.value) || 2));
      }
      if (tableAddRowButton) {
        tableAddRowButton.addEventListener("click", () => resizeTable((Number(tableRowsInput && tableRowsInput.value) || 2) + 1, Number(tableColsInput && tableColsInput.value) || 2));
      }
      if (tableAddColButton) {
        tableAddColButton.addEventListener("click", () => resizeTable(Number(tableRowsInput && tableRowsInput.value) || 2, (Number(tableColsInput && tableColsInput.value) || 2) + 1));
      }
      if (tableRemoveRowButton) {
        tableRemoveRowButton.addEventListener("click", () => resizeTable((Number(tableRowsInput && tableRowsInput.value) || 2) - 1, Number(tableColsInput && tableColsInput.value) || 2));
      }
      if (tableRemoveColButton) {
        tableRemoveColButton.addEventListener("click", () => resizeTable(Number(tableRowsInput && tableRowsInput.value) || 2, (Number(tableColsInput && tableColsInput.value) || 2) - 1));
      }
      if (tableClearButton) {
        tableClearButton.addEventListener("click", clearTableGrid);
      }
      if (tableModal) {
        tableModal.addEventListener("click", (event) => {
          if (event.target === tableModal) {
            closeTableModal();
          }
        });
      }
      if (tableGrid) {
        tableGrid.addEventListener("dragstart", (event) => {
          const rowWrap = event.target.closest("[data-table-row-wrap]");
          if (!rowWrap || rowWrap.dataset.row === "0") {
            event.preventDefault();
            return;
          }
          draggedTableRow = rowWrap;
          rowWrap.classList.add("authoring-table-row-dragging");
        });
        tableGrid.addEventListener("dragend", () => {
          if (draggedTableRow) {
            draggedTableRow.classList.remove("authoring-table-row-dragging");
          }
          draggedTableRow = null;
        });
        tableGrid.addEventListener("dragover", (event) => {
          if (!draggedTableRow) {
            return;
          }
          event.preventDefault();
          const targetRow = event.target.closest("[data-table-row-wrap]");
          if (!targetRow || targetRow === draggedTableRow || targetRow.dataset.row === "0") {
            return;
          }
          const bounds = targetRow.getBoundingClientRect();
          const insertBefore = event.clientY < bounds.top + bounds.height / 2;
          tableGrid.insertBefore(draggedTableRow, insertBefore ? targetRow : targetRow.nextSibling);
        });
      }
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && tableModal && !tableModal.hidden) {
          closeTableModal();
        }
      });
    }
  }
})();
