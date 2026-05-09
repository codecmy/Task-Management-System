(function () {
  var socket = io();
  var taskList = document.getElementById("task-list");
  var statsGrid = document.getElementById("stats-grid");
  var insightPanel = document.getElementById("insight-panel");
  var statusEl = document.getElementById("socket-status");

  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  function formatDate(dateStr) {
    if (!dateStr) return null;
    var d = new Date(dateStr);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function updateStats(stats) {
    if (!statsGrid) return;
    statsGrid.innerHTML =
      '<div><span>Portfolio</span><strong>' + stats.total + '</strong></div>' +
      '<div><span>Active work</span><strong>' + stats.todo + '</strong></div>' +
      '<div><span>Completed</span><strong>' + stats.done + '</strong></div>' +
      '<div><span>Critical focus</span><strong>' + stats.high + '</strong></div>';
    var subtitle = document.getElementById("dashboard-subtitle");
    if (subtitle) {
      subtitle.textContent = stats.total + " items tracked, " + stats.todo + " active, " + stats.done + " completed";
    }
  }

  function updateInsights(insights) {
    if (!insightPanel) return;
    var h2 = insightPanel.querySelector("h2");
    var p = insightPanel.querySelector("p");
    if (h2) h2.textContent = insights.completion_rate + "% completion rate";
    if (p) p.textContent = insights.recommendation;
    var metrics = insightPanel.querySelector(".insight-metrics");
    if (metrics) {
      var spans = metrics.querySelectorAll("span");
      if (spans[0]) spans[0].textContent = insights.overdue + " overdue";
      if (spans[1]) spans[1].textContent = insights.due_soon + " due this week";
    }
  }

  function buildTaskCard(task) {
    var article = document.createElement("article");
    article.className = "task" + (task.status === "done" ? " done" : "") + " priority-" + task.priority;
    article.dataset.taskId = String(task.id);
    article.dataset.status = task.status;
    article.dataset.priority = task.priority;
    article.dataset.dueDate = task.due_date || "";
    article.dataset.createdAt = task.created_at;

    var dueDate = formatDate(task.due_date);
    var html = '<div class="task-body">' +
      '<div class="task-title-row">' +
      '<h2>' + escapeHtml(task.title) + '</h2>' +
      '<span class="status-dot"></span>' +
      '</div>';
    if (task.description) {
      html += '<p>' + escapeHtml(task.description) + '</p>';
    }
    html += '<div class="task-meta">' +
      '<span class="tag priority">' + capitalize(task.priority) + '</span>';
    if (dueDate) {
      html += '<span class="tag">Due ' + dueDate + '</span>';
    }
    html += '</div></div>' +
      '<div class="task-actions">' +
      '<a class="button secondary compact" href="/tasks/' + task.id + '/edit">Edit</a>' +
      '<form action="/tasks/' + task.id + '/toggle" method="post">' +
      '<button class="compact" type="submit">' + (task.status === "done" ? "Reopen" : "Complete") + '</button>' +
      '</form>' +
      '<form action="/tasks/' + task.id + '/delete" method="post">' +
      '<button class="danger compact" type="submit">Delete</button>' +
      '</form>' +
      '</div>';
    article.innerHTML = html;
    return article;
  }

  function updateEmptyState() {
    if (!taskList) return;
    var tasks = taskList.querySelectorAll(".task");
    var emptyState = taskList.querySelector(".empty-state");
    if (tasks.length === 0) {
      if (!emptyState) {
        var p = document.createElement("p");
        p.className = "empty-state";
        p.id = "empty-state";
        p.textContent = "Your workspace is clear.";
        taskList.appendChild(p);
      }
    } else {
      if (emptyState) emptyState.remove();
    }
  }

  function handleTaskCreated(data) {
    updateStats(data.stats);
    updateInsights(data.insights);
    if (data.task && taskList) {
      var existing = taskList.querySelector('[data-task-id="' + data.task.id + '"]');
      if (!existing) {
        var card = buildTaskCard(data.task);
        var emptyState = taskList.querySelector(".empty-state");
        if (emptyState) emptyState.remove();
        taskList.insertBefore(card, taskList.firstChild);
      }
    }
  }

  function handleTaskUpdated(data) {
    updateStats(data.stats);
    updateInsights(data.insights);
    if (data.task && taskList) {
      var existing = taskList.querySelector('[data-task-id="' + data.task.id + '"]');
      if (existing) {
        var card = buildTaskCard(data.task);
        existing.replaceWith(card);
      }
    }
  }

  function handleTaskDeleted(data) {
    updateStats(data.stats);
    updateInsights(data.insights);
    if (data.task && taskList) {
      var existing = taskList.querySelector('[data-task-id="' + data.task.id + '"]');
      if (existing) existing.remove();
      updateEmptyState();
    }
  }

  socket.on("task_created", handleTaskCreated);
  socket.on("task_updated", handleTaskUpdated);
  socket.on("task_deleted", handleTaskDeleted);

  socket.on("connect", function () {
    if (statusEl) {
      statusEl.className = "socket-status connected";
    }
  });

  socket.on("disconnect", function () {
    if (statusEl) {
      statusEl.className = "socket-status disconnected";
    }
  });
})();
