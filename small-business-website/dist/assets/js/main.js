(function () {
  "use strict";

  // Mobile menu toggle
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("primary-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    nav.addEventListener("click", function (e) {
      if (e.target.tagName === "A" && nav.classList.contains("open")) {
        nav.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  // Current year in footer
  var year = document.getElementById("year");
  if (year) {
    year.textContent = String(new Date().getFullYear());
  }

  // Contact form validation
  var form = document.getElementById("contact-form");
  if (!form) return;

  var success = document.getElementById("form-success");

  function showError(field, message) {
    var el = document.getElementById(field.id + "-error");
    if (el) {
      el.textContent = message;
      el.hidden = false;
    }
    field.setAttribute("aria-invalid", "true");
  }

  function clearError(field) {
    var el = document.getElementById(field.id + "-error");
    if (el) {
      el.textContent = "";
      el.hidden = true;
    }
    field.removeAttribute("aria-invalid");
  }

  function validEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  }

  function validate() {
    var ok = true;
    var firstInvalid = null;

    var name = form.elements.name;
    if (!name.value.trim()) {
      showError(name, "Please enter your name.");
      ok = false;
      firstInvalid = firstInvalid || name;
    } else {
      clearError(name);
    }

    var email = form.elements.email;
    if (!email.value.trim()) {
      showError(email, "Please enter your email address.");
      ok = false;
      firstInvalid = firstInvalid || email;
    } else if (!validEmail(email.value.trim())) {
      showError(email, "Please enter a valid email address.");
      ok = false;
      firstInvalid = firstInvalid || email;
    } else {
      clearError(email);
    }

    var phone = form.elements.phone;
    if (phone.value.trim() && phone.value.replace(/[^0-9]/g, "").length < 7) {
      showError(phone, "Please enter a valid phone number.");
      ok = false;
      firstInvalid = firstInvalid || phone;
    } else {
      clearError(phone);
    }

    var message = form.elements.message;
    if (!message.value.trim()) {
      showError(message, "Please tell us how we can help.");
      ok = false;
      firstInvalid = firstInvalid || message;
    } else {
      clearError(message);
    }

    if (firstInvalid) firstInvalid.focus();
    return ok;
  }

  form.addEventListener("submit", function (e) {
    if (!validate()) {
      e.preventDefault();
      return;
    }
    var action = form.getAttribute("action");
    if (!action || action.trim() === "") {
      e.preventDefault();
      if (success) {
        success.textContent = "Demo form: connect Formspree/Netlify Forms/your email in site.json";
        success.hidden = false;
      }
    }
  });

  ["name", "email", "phone", "message"].forEach(function (id) {
    var field = form.elements[id];
    if (field) {
      field.addEventListener("input", function () {
        if (field.getAttribute("aria-invalid") === "true") clearError(field);
      });
    }
  });
})();
