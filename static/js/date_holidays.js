(function () {
  const holidayDataNode = document.getElementById("india-holiday-map");
  if (!holidayDataNode) {
    return;
  }

  let holidayMap = {};
  try {
    holidayMap = JSON.parse(holidayDataNode.textContent || "{}");
  } catch (error) {
    holidayMap = {};
  }

  function getHolidayItems(value) {
    if (!value) {
      return [];
    }
    const isoDate = value.slice(0, 10);
    const year = isoDate.slice(0, 4);
    return (holidayMap[year] || []).filter((item) => item.date === isoDate);
  }

  function getMonthHolidayItems(value) {
    if (!value) {
      return [];
    }
    const isoDate = value.slice(0, 10);
    const year = isoDate.slice(0, 4);
    const yearMonth = isoDate.slice(0, 7);
    return (holidayMap[year] || []).filter((item) => item.date.slice(0, 7) === yearMonth);
  }

  document.querySelectorAll("[data-holiday-widget]").forEach((widget) => {
    const input = widget.querySelector("[data-holiday-date-input]");
    const toggle = widget.querySelector("[data-holiday-toggle]");
    const help = widget.querySelector("[data-holiday-help]");
    const note = widget.querySelector("[data-holiday-note]");
    const list = widget.querySelector("[data-holiday-list]");
    if (!input || !toggle || !help || !note || !list) {
      return;
    }

    const render = () => {
      const selectedHolidays = getHolidayItems(input.value);
      const monthHolidays = getMonthHolidayItems(input.value);
      note.textContent = selectedHolidays.length
        ? `Selected date matches ${selectedHolidays.map((item) => item.label).join(", ")}.`
        : "Selected date is not one of the built-in India national holidays.";

      list.innerHTML = "";
      const itemsToRender = monthHolidays.length ? monthHolidays : [];
      if (!itemsToRender.length) {
        const item = document.createElement("li");
        item.textContent = input.value ? "No India national holidays in this month." : "Pick a date to see holidays in that month.";
        list.appendChild(item);
      } else {
        itemsToRender.forEach((itemData) => {
          const item = document.createElement("li");
          item.textContent = `${itemData.date}: ${itemData.label} (${itemData.calendar_label})`;
          list.appendChild(item);
        });
      }
      help.hidden = !toggle.checked;
    };

    toggle.addEventListener("change", render);
    input.addEventListener("input", render);
    input.addEventListener("change", render);
    render();
  });
})();
