(function () {
  var socket = io();
  var taskList = document.getElementById("task-list");
  var statsGrid = document.getElementById("stats-grid");
  var insightPanel = document.getElementById("insight-panel");
  var statusEl = document.getElementById("socket-status");
  var kanbanBoard = document.getElementById("kanban-board");
  var sidebarToggle = document.getElementById("sidebar-toggle");
  var taskForm = document.getElementById("task-form");
  var currentView = localStorage.getItem("kanban-view") || "kanban";
  var currentGroup = localStorage.getItem("kanban-group") || "status";

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
    var activeCount = (stats.todo || 0) + (stats.in_progress || 0);
    statsGrid.innerHTML =
      '<div><span>Portfolio</span><strong>' + stats.total + '</strong></div>' +
      '<div><span>Active work</span><strong>' + activeCount + '</strong></div>' +
      '<div><span>Completed</span><strong>' + stats.done + '</strong></div>' +
      '<div><span>Critical focus</span><strong>' + stats.high + '</strong></div>';
    var subtitle = document.getElementById("dashboard-subtitle");
    if (subtitle) {
      subtitle.textContent = stats.total + " items tracked, " + activeCount + " active, " + stats.done + " completed";
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

  // ─── Kanban Card Builder ─────────────────────────────────────────

  function buildKanbanCard(task) {
    var article = document.createElement("article");
    var statusClass = task.status === "done" ? " done" : "";
    article.className = "kanban-card" + statusClass + " priority-" + task.priority;
    article.dataset.taskId = String(task.id);
    article.dataset.status = task.status;
    article.dataset.priority = task.priority;
    article.dataset.position = String(task.position || 0);
    article.dataset.dueDate = task.due_date || "";
    article.dataset.createdAt = task.created_at;

    var dueDate = formatDate(task.due_date);
    var toggleTitle = task.status === "done" ? "Reopen" : "Complete";
    var toggleIcon = task.status === "done" ? "&#x21BA;" : "&#x2713;";

    var html =
      '<div class="kanban-card-body">' +
        '<div class="card-title-row">' +
          '<span class="card-title">' + escapeHtml(task.title) + '</span>' +
          '<span class="status-dot"></span>' +
        '</div>' +
        '<div class="card-meta">' +
          '<span class="tag priority">' + capitalize(task.priority) + '</span>';
    if (dueDate) {
      html += '<span class="tag">Due ' + dueDate + '</span>';
    }
    html +=
        '</div>' +
      '</div>' +
      '<div class="card-actions">' +
        '<form action="/tasks/' + task.id + '/toggle" method="post" class="inline-form">' +
          '<button class="card-action-btn" title="' + toggleTitle + '">' + toggleIcon + '</button>' +
        '</form>' +
        '<a class="card-action-btn" href="/tasks/' + task.id + '/edit" title="Edit">&#x270E;</a>' +
        '<form action="/tasks/' + task.id + '/delete" method="post" class="inline-form">' +
          '<button class="card-action-btn danger" title="Delete">&#x2715;</button>' +
        '</form>' +
      '</div>';
    article.innerHTML = html;
    return article;
  }

  // ─── Flat List Card Builder ──────────────────────────────────────

  function buildListCard(task) {
    var article = document.createElement("article");
    var statusClass = task.status === "done" ? " done" : task.status === "in_progress" ? " in-progress" : "";
    article.className = "task" + statusClass + " priority-" + task.priority;
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

  // ─── Kanban Column Operations ────────────────────────────────────

  function getColumnEl(columnKey) {
    return document.querySelector('.kanban-column[data-column="' + columnKey + '"]');
  }

  function getCardsContainer(columnKey) {
    var col = getColumnEl(columnKey);
    return col ? col.querySelector(".kanban-cards") : null;
  }

  function getColumnCountEl(columnKey) {
    var col = getColumnEl(columnKey);
    return col ? col.querySelector(".column-count") : null;
  }

  function updateColumnCounts() {
    document.querySelectorAll(".kanban-column").forEach(function (col) {
      var key = col.dataset.column;
      var count = col.querySelectorAll(".kanban-card").length;
      var countEl = col.querySelector(".column-count");
      if (countEl) countEl.textContent = count;
    });
  }

  function insertIntoColumn(task, columnKey) {
    var container = getCardsContainer(columnKey);
    if (!container) return;
    var existing = container.querySelector('[data-task-id="' + task.id + '"]');
    if (existing) return;
    var card = buildKanbanCard(task);
    container.appendChild(card);
    updateColumnCounts();
  }

  function removeFromBoard(taskId) {
    document.querySelectorAll(".kanban-card").forEach(function (card) {
      if (card.dataset.taskId === String(taskId)) {
        card.remove();
      }
    });
    updateColumnCounts();
  }

  function updateCardInBoard(task) {
    var card = document.querySelector('.kanban-card[data-task-id="' + task.id + '"]');
    if (card) {
      var columnKey = task.status;
      var container = getCardsContainer(columnKey);
      if (container && container !== card.parentNode) {
        removeFromBoard(task.id);
        insertIntoColumn(task, columnKey);
      } else {
        var newCard = buildKanbanCard(task);
        card.replaceWith(newCard);
      }
      updateColumnCounts();
    }
  }

  function moveCardOnBoard(taskId, sourceCol, targetCol, position) {
    var card = document.querySelector('.kanban-card[data-task-id="' + taskId + '"]');
    if (!card) return;
    var targetContainer = getCardsContainer(targetCol);
    if (!targetContainer) return;
    card.remove();
    card.dataset.status = targetCol;
    if (position !== undefined) {
      card.dataset.position = position;
    }
    targetContainer.appendChild(card);
    updateColumnCounts();
  }

  // ─── Flat List Operations ────────────────────────────────────────

  function insertIntoFlatList(task) {
    if (!taskList) return;
    var existing = taskList.querySelector('[data-task-id="' + task.id + '"]');
    if (!existing) {
      var card = buildListCard(task);
      var emptyState = taskList.querySelector(".empty-state");
      if (emptyState) emptyState.remove();
      taskList.insertBefore(card, taskList.firstChild);
    }
  }

  function removeFromFlatList(taskId) {
    if (!taskList) return;
    var existing = taskList.querySelector('[data-task-id="' + taskId + '"]');
    if (existing) existing.remove();
    var remaining = taskList.querySelectorAll(".task");
    var emptyState = taskList.querySelector(".empty-state");
    if (remaining.length === 0 && !emptyState) {
      var p = document.createElement("p");
      p.className = "empty-state";
      p.id = "empty-state";
      p.textContent = "Your workspace is clear.";
      taskList.appendChild(p);
    }
  }

  function updateInFlatList(task) {
    if (!taskList) return;
    var existing = taskList.querySelector('[data-task-id="' + task.id + '"]');
    if (existing) {
      var card = buildListCard(task);
      existing.replaceWith(card);
    }
  }

  // ─── Board Render ────────────────────────────────────────────────

  function fetchKanban(groupBy, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/api/kanban?group_by=" + groupBy);
    xhr.onload = function () {
      if (xhr.status === 200) {
        callback(JSON.parse(xhr.responseText));
      }
    };
    xhr.send();
  }

  function renderBoardFromData(data) {
    if (!kanbanBoard) return;
    kanbanBoard.innerHTML = "";
    data.columns.forEach(function (col) {
      var columnDiv = document.createElement("div");
      columnDiv.className = "kanban-column kanban-column-" + col.key;
      columnDiv.dataset.column = col.key;

      var header = document.createElement("div");
      header.className = "kanban-column-header";
      header.innerHTML =
        '<span class="column-title">' + escapeHtml(col.label) + '</span>' +
        '<span class="column-count" id="count-' + col.key + '">' + col.count + '</span>';

      var cardsDiv = document.createElement("div");
      cardsDiv.className = "kanban-cards";
      cardsDiv.id = "column-" + col.key;

      col.tasks.forEach(function (task) {
        cardsDiv.appendChild(buildKanbanCard(task));
      });

      var dropZone = document.createElement("div");
      dropZone.className = "kanban-drop-zone";
      dropZone.textContent = "Drop tasks here";

      columnDiv.appendChild(header);
      columnDiv.appendChild(cardsDiv);
      columnDiv.appendChild(dropZone);
      kanbanBoard.appendChild(columnDiv);
    });
    initSortable();
  }

  // ─── Drag & Drop ─────────────────────────────────────────────────

  function computePosition(container, newIndex) {
    var cards = container.querySelectorAll(".kanban-card");
    if (cards.length === 0) return 0.0;
    if (newIndex <= 0) return parseFloat(cards[0].dataset.position || 0) / 2;
    if (newIndex >= cards.length) return parseFloat(cards[cards.length - 1].dataset.position || 0) + 1.0;
    var prev = parseFloat(cards[newIndex - 1].dataset.position || 0);
    var next = parseFloat(cards[newIndex].dataset.position || 0);
    return (prev + next) / 2;
  }

  function initSortable() {
    document.querySelectorAll(".kanban-cards").forEach(function (el) {
      if (el.sortableInstance) {
        el.sortableInstance.destroy();
      }
      el.sortableInstance = new Sortable(el, {
        group: "kanban",
        animation: 200,
        ghostClass: "kanban-card-ghost",
        dragClass: "kanban-card-dragging",
        onEnd: function (evt) {
          var taskId = evt.item.dataset.taskId;
          var targetCol = evt.to.closest(".kanban-column").dataset.column;
          var isSameCol = evt.from === evt.to;
          var position = computePosition(evt.to, evt.newIndex);

          if (isSameCol && evt.oldIndex === evt.newIndex) return;

          evt.item.dataset.position = String(position);

          var url = isSameCol ? "/tasks/" + taskId + "/reorder" : "/tasks/" + taskId + "/move";
          var body = isSameCol ? JSON.stringify({ position: position }) : JSON.stringify({ status: targetCol, position: position });

          fetch(url, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: body,
          });
        },
      });
    });
  }

  // ─── View Switching ──────────────────────────────────────────────

  function switchView(view) {
    currentView = view;
    localStorage.setItem("kanban-view", view);
    var kanbanEl = document.getElementById("kanban-board");
    var listEl = document.getElementById("task-list");
    var groupToggle = document.getElementById("group-toggle");

    if (view === "kanban") {
      if (kanbanEl) kanbanEl.classList.remove("hidden");
      if (listEl) listEl.classList.add("hidden");
      if (groupToggle) groupToggle.classList.remove("hidden");
    } else {
      if (kanbanEl) kanbanEl.classList.add("hidden");
      if (listEl) listEl.classList.remove("hidden");
      if (groupToggle) groupToggle.classList.add("hidden");
    }

    document.querySelectorAll(".view-toggle button").forEach(function (btn) {
      btn.classList.toggle("active", btn.dataset.view === view);
    });
  }

  function switchGroupBy(groupBy) {
    currentGroup = groupBy;
    localStorage.setItem("kanban-group", groupBy);
    fetchKanban(groupBy, function (data) {
      renderBoardFromData(data);
    });
    document.querySelectorAll(".group-toggle button").forEach(function (btn) {
      btn.classList.toggle("active", btn.dataset.group === groupBy);
    });
  }

  function initViewToggles() {
    document.querySelectorAll(".view-toggle button").forEach(function (btn) {
      btn.addEventListener("click", function () {
        switchView(btn.dataset.view);
      });
    });
    document.querySelectorAll(".group-toggle button").forEach(function (btn) {
      btn.addEventListener("click", function () {
        switchGroupBy(btn.dataset.group);
      });
    });
    switchView(currentView);
  }

  // ─── Sidebar ─────────────────────────────────────────────────────

  function initSidebar() {
    var stored = localStorage.getItem("kanban-sidebar");
    if (stored === "expanded") {
      if (taskForm) {
        taskForm.classList.remove("sidebar-collapsed");
        taskForm.classList.add("sidebar-expanded");
      }
    }
    if (sidebarToggle) {
      sidebarToggle.addEventListener("click", function () {
        if (taskForm) {
          taskForm.classList.toggle("sidebar-collapsed");
          taskForm.classList.toggle("sidebar-expanded");
          localStorage.setItem("kanban-sidebar",
            taskForm.classList.contains("sidebar-expanded") ? "expanded" : "collapsed");
        }
      });
    }
  }

  // ─── WebSocket Handlers ──────────────────────────────────────────

  function handleTaskCreated(data) {
    updateStats(data.stats);
    updateInsights(data.insights);
    if (!data.task) return;
    insertIntoColumn(data.task, data.task.status);
    insertIntoFlatList(data.task);
  }

  function handleTaskUpdated(data) {
    updateStats(data.stats);
    updateInsights(data.insights);
    if (!data.task) return;
    updateCardInBoard(data.task);
    updateInFlatList(data.task);
  }

  function handleTaskDeleted(data) {
    updateStats(data.stats);
    updateInsights(data.insights);
    if (!data.task) return;
    removeFromBoard(data.task.id);
    removeFromFlatList(data.task.id);
  }

  function handleTaskMoved(data) {
    updateStats(data.stats);
    updateInsights(data.insights);
    if (!data.task) return;
    if (currentView === "kanban") {
      removeFromBoard(data.task.id);
      insertIntoColumn(data.task, data.task.status);
    }
    updateInFlatList(data.task);
  }

  // ─── Socket Events ───────────────────────────────────────────────

  socket.on("task_created", handleTaskCreated);
  socket.on("task_updated", handleTaskUpdated);
  socket.on("task_deleted", handleTaskDeleted);
  socket.on("task_moved", handleTaskMoved);

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

  // ─── Init ────────────────────────────────────────────────────────

  initSortable();
  initSidebar();
  initViewToggles();
})();
