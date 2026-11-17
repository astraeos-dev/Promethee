// Combobox: a text field that suggests entries from a list (ARIA 1.2 combobox pattern).
// Free text stays allowed: the list only proposes known values.

import { escapeHtml as h } from "./common.js";

// Lower case without accents: "resistance" finds "Résistance".
export const fold = (text) => String(text ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

let lastId = 0;

/**
 * Turn a text field into a combobox.
 * entries: [{ label, group?, detail?, badge?, search?, extra?, data? }], grouped entries kept together.
 * Typing matches the label and `search` (references, category…); `extra` (a description)
 * is only searched when nothing else matches, so that "résistance" lists resistors, not
 * every device whose description mentions one.
 * onSelect(entry, { typed }) runs when an entry is picked in the list (typed: false)
 * or when the field is left holding the exact label of an entry (typed: true).
 */
export function attachCombobox(input, { entries = [], label = "Suggestions", openOnFocus = false, onSelect = () => {} } = {}) {
  const id = `combobox-${++lastId}`;
  const hadFocus = document.activeElement === input; // moving the field takes the focus away
  const box = document.createElement("div");
  box.className = "combobox";
  input.replaceWith(box);

  const toggle = document.createElement("button");
  toggle.type = "button"; // never the default button of the form
  toggle.className = "combobox-toggle";
  toggle.tabIndex = -1;
  toggle.setAttribute("aria-label", label);
  toggle.innerHTML = '<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  const list = document.createElement("div");
  list.id = `${id}-list`;
  list.className = "combobox-list";
  list.setAttribute("role", "listbox");
  list.setAttribute("aria-label", label);
  list.hidden = true;
  box.append(input, toggle, list);

  input.autocomplete = "off";
  input.setAttribute("role", "combobox");
  input.setAttribute("aria-autocomplete", "list");
  input.setAttribute("aria-controls", list.id);
  input.setAttribute("aria-expanded", "false");

  let items = [];   // entries with their folded label and search text
  let shown = [];   // entries of the open list, in display order
  let active = -1;  // index in shown of the option chosen with the arrow keys
  let picked = null;
  let mode = "browse"; // how the list was last opened, see matches()

  function setEntries(next) {
    items = next.map((entry) => ({
      ...entry,
      key: fold(entry.label),
      text: fold(`${entry.label} ${entry.search ?? ""}`),
      extraText: fold(entry.extra),
    }));
    box.classList.toggle("has-entries", items.length > 0);
    if (!list.hidden) open(mode);
  }

  // mode: "filter" while typing; "browse" when the list is opened on a field that is empty
  // or holds a known value, to choose or change it; "all" from the toggle button.
  function matches() {
    const query = fold(input.value);
    if (mode === "all" || !query || (mode === "browse" && items.some((e) => e.key === query))) return items;
    const words = query.split(/\s+/);
    const found = items.filter((e) => words.every((w) => e.text.includes(w)));
    return found.length ? found : items.filter((e) => words.every((w) => e.text.includes(w) || e.extraText.includes(w)));
  }

  // Keep an option visible inside the scrolling list, without scrolling the page or the dialog.
  function reveal(option, center = false) {
    const top = option.offsetTop, bottom = top + option.offsetHeight;
    if (center) list.scrollTop = top - (list.clientHeight - option.offsetHeight) / 2;
    else if (top < list.scrollTop) list.scrollTop = top - (option.previousElementSibling?.offsetHeight ?? 0);
    else if (bottom > list.scrollTop + list.clientHeight) list.scrollTop = bottom - list.clientHeight;
  }

  function setActive(index) {
    active = index;
    for (const option of list.querySelectorAll("[role=option]")) {
      const on = Number(option.dataset.index) === index;
      option.classList.toggle("active", on);
      option.setAttribute("aria-selected", String(on));
      if (on) reveal(option);
    }
    if (index >= 0) input.setAttribute("aria-activedescendant", `${id}-option-${index}`);
    else input.removeAttribute("aria-activedescendant");
  }

  function open(how = "browse") {
    mode = how;
    shown = matches();
    if (!shown.length) return close();
    const current = fold(input.value);
    let html = "";
    let group;
    shown.forEach((entry, i) => {
      if (entry.group !== group) {
        if (group !== undefined) html += "</div>";
        group = entry.group;
        html += entry.group
          ? `<div role="group" aria-labelledby="${id}-group-${i}"><div class="combobox-group" id="${id}-group-${i}">${h(entry.group)}</div>`
          : '<div role="group">';
      }
      html += `<div class="combobox-option${entry.key === current ? " current" : ""}" role="option" id="${id}-option-${i}" data-index="${i}" aria-selected="false">
        <span class="text"><span>${h(entry.label)}</span>${entry.detail ? `<small>${h(entry.detail)}</small>` : ""}</span>
        ${entry.badge ? `<span class="badge badge-accent">${h(entry.badge)}</span>` : ""}</div>`;
    });
    list.innerHTML = `${html}</div>`;
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
    active = -1;
    input.removeAttribute("aria-activedescendant");
    const currentOption = list.querySelector(".current");
    if (currentOption) reveal(currentOption, true);
    else list.scrollTop = 0;
  }

  function close() {
    list.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    active = -1;
  }

  function select(entry, typed = false) {
    picked = entry;
    input.value = entry.label; // also corrects the case and accents of a typed name
    close();
    onSelect(entry, { typed });
  }

  input.addEventListener("input", () => { picked = null; open("filter"); });
  input.addEventListener("focus", () => { if (openOnFocus) open(); });
  input.addEventListener("click", () => { if (list.hidden) open(); });
  input.addEventListener("blur", close);
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (list.hidden) open();
      if (list.hidden) return;
      const last = shown.length - 1;
      if (e.key === "ArrowDown") setActive(active >= last ? 0 : active + 1);
      else setActive(active <= 0 ? last : active - 1);
    } else if (e.key === "Enter" && !list.hidden && active >= 0) {
      e.preventDefault(); // pick the option instead of submitting the form
      select(shown[active]);
    } else if (e.key === "Escape" && !list.hidden) {
      e.preventDefault(); // close the list, not the dialog
      e.stopPropagation();
      close();
    }
  });
  // A known name typed in full counts as picked.
  input.addEventListener("change", () => {
    const entry = items.find((e) => e.key === fold(input.value));
    if (entry && entry.key !== picked?.key) select(entry, true);
  });

  list.addEventListener("mousedown", (e) => e.preventDefault()); // keep the focus in the field
  list.addEventListener("click", (e) => {
    const option = e.target.closest("[role=option]");
    if (option) select(shown[Number(option.dataset.index)]);
  });
  toggle.addEventListener("mousedown", (e) => e.preventDefault());
  toggle.addEventListener("click", () => {
    if (!list.hidden) return close();
    input.focus();
    open("all");
  });

  setEntries(entries);
  if (hadFocus) input.focus();
  return { setEntries, open: () => open(), close, isOpen: () => !list.hidden };
}
