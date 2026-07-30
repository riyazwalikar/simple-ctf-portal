(function () {
  "use strict";

  // Progressive enhancement: CSS only hides accordion panels when JS is on,
  // so the no-JS fallback (plain forms) stays reachable.
  document.documentElement.classList.add("js");

  // --- Theme toggle ---
  var themeToggle = document.getElementById("theme-toggle");
  if (themeToggle) {
    var syncToggleLabel = function () {
      var isLight = document.documentElement.getAttribute("data-theme") === "light";
      themeToggle.textContent = isLight ? "🌙" : "☀️";
      themeToggle.setAttribute("aria-label", isLight ? "Switch to dark mode" : "Switch to light mode");
    };
    syncToggleLabel();
    themeToggle.addEventListener("click", function () {
      var next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", next);
      try {
        localStorage.setItem("theme", next);
      } catch (e) {}
      syncToggleLabel();
    });
  }

  // --- Accordion ---
  document.querySelectorAll(".accordion-trigger").forEach(function (trigger) {
    trigger.addEventListener("click", function () {
      var expanded = this.getAttribute("aria-expanded") === "true";
      this.setAttribute("aria-expanded", !expanded);
    });
  });

  // --- Async flag submission ---
  document.querySelectorAll(".flag-form").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();

      var challengeId = this.dataset.challengeId;
      var input = this.querySelector(".flag-input");
      var feedback = this.querySelector(".flag-feedback");
      var submitBtn = this.querySelector("button[type='submit']");
      var csrfToken = this.querySelector("input[name='csrf_token']").value;

      var flag = input.value.trim();
      if (!flag) {
        feedback.textContent = "Please enter a flag.";
        feedback.className = "flag-feedback incorrect";
        return;
      }

      feedback.textContent = "";
      feedback.className = "flag-feedback";
      submitBtn.disabled = true;

      var formData = new URLSearchParams();
      formData.append("flag", flag);
      formData.append("csrf_token", csrfToken);

      fetch("/challenges/" + challengeId + "/submit", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "X-Requested-With": "XMLHttpRequest",
        },
        body: formData.toString(),
      })
        .then(function (res) {
          if (res.status === 429) {
            return { status: 429, data: { result: "rate_limited" } };
          }
          return res.json().then(function (data) {
            return { status: res.status, data: data };
          });
        })
        .then(function (result) {
          var data = result.data;
          submitBtn.disabled = false;

          if (result.status === 429) {
            feedback.textContent = "Rate limited. Slow down and try again.";
            feedback.className = "flag-feedback incorrect";
          } else if (data.result === "correct") {
            feedback.textContent = "Correct!";
            feedback.className = "flag-feedback correct";
            markSolved(challengeId, data.score);
          } else if (data.result === "incorrect") {
            feedback.textContent = "Incorrect flag.";
            feedback.className = "flag-feedback incorrect";
            input.classList.add("shake");
            setTimeout(function () {
              input.classList.remove("shake");
            }, 400);
          } else if (data.result === "already_solved") {
            feedback.textContent = "Already solved.";
            feedback.className = "flag-feedback already-solved";
          } else {
            feedback.textContent = data.message || "Error.";
            feedback.className = "flag-feedback incorrect";
          }
        })
        .catch(function () {
          submitBtn.disabled = false;
          feedback.textContent = "Network error. Try again.";
          feedback.className = "flag-feedback incorrect";
        });
    });
  });

  function markSolved(challengeId, newScore) {
    var card = document.getElementById("challenge-" + challengeId);
    if (card) {
      card.classList.add("solved");
      var solvedBadge = card.querySelector(".badge-solved");
      if (solvedBadge) {
        solvedBadge.classList.add("visible");
      }
    }

    // Update score chip
    var scoreChip = document.getElementById("score-chip");
    if (scoreChip) {
      scoreChip.textContent = newScore + " pts";
    }
  }
})();
