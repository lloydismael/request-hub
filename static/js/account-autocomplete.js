(function (window, document) {
  "use strict";

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function escapeAttr(str) {
    return escapeHtml(str).replace(/`/g, "&#96;");
  }

  function normalize(str) {
    return String(str || "")
      .trim()
      .toLowerCase();
  }

  function readOptionsFromInput(input) {
    var listId = input.getAttribute("list");
    if (!listId) return [];
    var datalist = document.getElementById(listId);
    if (!datalist) return [];
    return Array.from(datalist.options)
      .map(function (opt) {
        return (opt.value || "").trim();
      })
      .filter(Boolean);
  }

  function highlightMatch(text, query) {
    var q = String(query || "").trim();
    if (!q) return escapeHtml(text);
    var lowerText = String(text).toLowerCase();
    var lowerQ = q.toLowerCase();
    var idx = lowerText.indexOf(lowerQ);
    if (idx < 0) return escapeHtml(text);
    return (
      escapeHtml(text.slice(0, idx)) +
      '<mark class="acct-dropdown__mark">' +
      escapeHtml(text.slice(idx, idx + q.length)) +
      "</mark>" +
      escapeHtml(text.slice(idx + q.length))
    );
  }

  function rankFilter(options, query) {
    var q = normalize(query);
    var cmp = function (a, b) {
      return a.localeCompare(b, undefined, { sensitivity: "base" });
    };
    if (!q) return options.slice().sort(cmp);

    var starts = [];
    var contains = [];
    options.forEach(function (name) {
      var n = normalize(name);
      if (!n.includes(q)) return;
      if (n.startsWith(q)) starts.push(name);
      else contains.push(name);
    });
    starts.sort(cmp);
    contains.sort(cmp);
    return starts.concat(contains);
  }

  function initAccountAutocomplete(input, options) {
    if (!input || input.dataset.acctAutocompleteReady === "1") return;
    input.dataset.acctAutocompleteReady = "1";

    var allOptions = Array.isArray(options) ? options.slice() : readOptionsFromInput(input);
    if (input.hasAttribute("list")) {
      input.removeAttribute("list");
    }

    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("autocomplete", "off");

    var dropdown = document.createElement("div");
    dropdown.className = "acct-dropdown";
    dropdown.setAttribute("role", "listbox");
    dropdown.id = (input.id || "account-name") + "-acct-listbox";
    dropdown.style.display = "none";
    document.body.appendChild(dropdown);
    input.setAttribute("aria-controls", dropdown.id);

    var activeIndex = -1;
    var isOpen = false;

    function positionDropdown() {
      var rect = input.getBoundingClientRect();
      dropdown.style.top = rect.bottom + 3 + "px";
      dropdown.style.left = rect.left + "px";
      dropdown.style.width = Math.max(rect.width, 220) + "px";
    }

    function closeDropdown() {
      dropdown.style.display = "none";
      dropdown.innerHTML = "";
      activeIndex = -1;
      isOpen = false;
      input.setAttribute("aria-expanded", "false");
    }

    function setActive(index) {
      var items = dropdown.querySelectorAll(".acct-dropdown__item");
      if (!items.length) {
        activeIndex = -1;
        return;
      }
      if (index < 0) index = 0;
      if (index > items.length - 1) index = items.length - 1;
      items.forEach(function (el, i) {
        var on = i === index;
        el.classList.toggle("is-active", on);
        if (on) el.setAttribute("aria-selected", "true");
        else el.removeAttribute("aria-selected");
      });
      if (items[index]) items[index].scrollIntoView({ block: "nearest" });
      activeIndex = index;
    }

    function selectItem(item) {
      if (!item) return;
      input.value = item.getAttribute("data-value") || "";
      input.dispatchEvent(new Event("change", { bubbles: true }));
      closeDropdown();
      input.focus();
    }

    function renderOptions(query) {
      var trimmed = String(query || "").trim();
      var filtered = rankFilter(allOptions, trimmed).slice(0, 60);
      var exact = allOptions.some(function (name) {
        return normalize(name) === normalize(trimmed);
      });
      var showCreate = trimmed.length > 0 && !exact;

      if (!filtered.length && !showCreate) {
        closeDropdown();
        return;
      }

      var html = "";
      filtered.forEach(function (name) {
        html +=
          '<div class="acct-dropdown__item" role="option" data-value="' +
          escapeAttr(name) +
          '"><span class="acct-dropdown__label">' +
          highlightMatch(name, trimmed) +
          "</span></div>";
      });

      if (showCreate) {
        html +=
          '<div class="acct-dropdown__item acct-dropdown__item--create" role="option" data-action="create" data-value="' +
          escapeAttr(trimmed) +
          '">' +
          '<span class="acct-dropdown__create-label">' +
          '<i class="bi bi-plus-circle me-1" aria-hidden="true"></i>' +
          "Create new account <strong>“" +
          escapeHtml(trimmed) +
          "”</strong>" +
          "</span>" +
          '<span class="acct-dropdown__hint">Not in the list — will be created on submit</span>' +
          "</div>";
      }

      dropdown.innerHTML = html;
      activeIndex = -1;
      positionDropdown();
      dropdown.style.display = "block";
      isOpen = true;
      input.setAttribute("aria-expanded", "true");
    }

    input.addEventListener("input", function () {
      renderOptions(input.value);
    });

    input.addEventListener("focus", function () {
      renderOptions(input.value);
    });

    input.addEventListener("keydown", function (e) {
      if (!isOpen) {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          renderOptions(input.value);
        }
        return;
      }

      var items = dropdown.querySelectorAll(".acct-dropdown__item");
      if (!items.length) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActive(activeIndex < 0 ? 0 : activeIndex + 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActive(activeIndex < 0 ? items.length - 1 : activeIndex - 1);
      } else if (e.key === "Enter") {
        if (activeIndex >= 0 && items[activeIndex]) {
          e.preventDefault();
          selectItem(items[activeIndex]);
        } else if (
          items.length === 1 &&
          items[0].getAttribute("data-action") === "create"
        ) {
          e.preventDefault();
          selectItem(items[0]);
        }
      } else if (e.key === "Escape") {
        e.preventDefault();
        closeDropdown();
      } else if (e.key === "Tab") {
        closeDropdown();
      }
    });

    dropdown.addEventListener("mousedown", function (e) {
      var item = e.target.closest(".acct-dropdown__item");
      if (!item) return;
      e.preventDefault();
      selectItem(item);
    });

    document.addEventListener("click", function (e) {
      if (!input.contains(e.target) && !dropdown.contains(e.target)) {
        closeDropdown();
      }
    });

    var positionRaf = 0;
    function schedulePosition() {
      if (!isOpen || positionRaf) return;
      positionRaf = window.requestAnimationFrame(function () {
        positionRaf = 0;
        if (isOpen) positionDropdown();
      });
    }
    window.addEventListener("scroll", schedulePosition, true);
    window.addEventListener("resize", schedulePosition);
  }

  function initAccountAutocompletes(root) {
    var scope = root || document;
    scope
      .querySelectorAll(
        '#id_account_name, [data-account-autocomplete="true"], input[list="account-name-options"]'
      )
      .forEach(function (el) {
        initAccountAutocomplete(el);
      });
  }

  window.initAccountAutocomplete = initAccountAutocomplete;
  window.initAccountAutocompletes = initAccountAutocompletes;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initAccountAutocompletes();
    });
  } else {
    initAccountAutocompletes();
  }
})(window, document);
