function convertLocalDatetimes() {
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".local-datetime").forEach(function (el) {
      var iso = el.getAttribute("data-iso");
      if (!iso) return;
      var d = new Date(iso);
      if (isNaN(d.getTime())) return;
      var year = d.getFullYear();
      var month = String(d.getMonth() + 1).padStart(2, "0");
      var day = String(d.getDate()).padStart(2, "0");
      var hours = String(d.getHours()).padStart(2, "0");
      var minutes = String(d.getMinutes()).padStart(2, "0");
      el.textContent = year + "." + month + "." + day + " " + hours + ":" + minutes;
    });
  });
}

function makeTableSortable(tableId) {
  document.addEventListener("DOMContentLoaded", function () {
    var table = document.getElementById(tableId);
    if (!table) return;
    var headers = table.querySelectorAll("thead th");
    var tbody = table.querySelector("tbody");
    var currentCol = 0;
    var ascending = true;

    headers.forEach(function (th, colIdx) {
      th.addEventListener("click", function () {
        var sortType = th.getAttribute("data-sort");
        if (currentCol === colIdx) {
          ascending = !ascending;
        } else {
          currentCol = colIdx;
          ascending = sortType !== "number";
        }

        var rows = Array.from(tbody.querySelectorAll("tr"));
        rows.sort(function (a, b) {
          var aText = a.children[colIdx].textContent.trim();
          var bText = b.children[colIdx].textContent.trim();
          var cmp = 0;
          if (sortType === "number") {
            cmp = parseFloat(aText) - parseFloat(bText);
          } else {
            cmp = aText.localeCompare(bText, undefined, { sensitivity: "base" });
          }
          return ascending ? cmp : -cmp;
        });

        rows.forEach(function (row) {
          tbody.appendChild(row);
        });

        headers.forEach(function (h, idx) {
          var indicator = h.querySelector(".sort-indicator");
          if (indicator) {
            indicator.textContent = idx === currentCol ? (ascending ? "▲" : "▼") : "";
          }
        });
      });
    });
  });
}
