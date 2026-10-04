/* benchmark-pages · 榜单渲染
 * 数据从页面内嵌的 <script type="application/json"> 读取——不发起网络请求，
 * 因此整站在 file:// 下也能打开，且页面本身就是机器可读的。
 */
(function () {
  'use strict';

  function readJSON(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      console.error('[benchmark-pages] 解析 ' + id + ' 失败', e);
      return null;
    }
  }

  function fmt(value, unit, digits) {
    if (value === null || value === undefined || value === '') return '—';
    var n = Number(value);
    if (!isFinite(n)) return String(value);
    var s = n.toFixed(digits === undefined ? 2 : digits);
    return unit === 'percent' ? s + '%' : s;
  }

  /* ── 主榜 ──────────────────────────────────────────── */

  function renderLeaderboard(payload) {
    var mount = document.getElementById('leaderboard-table');
    if (!mount || typeof Tabulator === 'undefined') {
      if (mount) mount.innerHTML = '<p class="has-text-centered">Table engine could not load.</p>';
      return;
    }

    var unit = payload.unit || 'percent';
    var primary = payload.primary_metric;

    // 检索框：榜单超过 15 行时才有意义
    if (payload.rows.length > 0) {
      var bar = document.createElement('div');
      bar.className = 'baseline-bar';
      bar.style.marginBottom = '14px';
      bar.innerHTML = '<label for="lb-search">Find a model</label><input type="search" id="lb-search" aria-label="Filter models" placeholder="Search model or organization…" ' +
        'style="flex:1;min-width:220px;padding:7px 14px;border:1px solid var(--line);' +
        'border-radius:999px;font:inherit;font-size:14px;background:#fff">';
      mount.parentNode.insertBefore(bar, mount);
    }

    var columns = payload.columns.map(function (c) {
      var col = {
        title: c.title,
        field: c.field,
        sorter: c.numeric ? 'number' : 'string',
        hozAlign: c.numeric ? 'right' : 'left',
        headerHozAlign: c.numeric ? 'right' : 'left',
        minWidth: c.is_model ? 205 : (c.primary ? 150 : (c.field === '_ci' ? 150 : (c.numeric ? 92 : 110)))
      };

      // 模型名永远可见、永远在最左——列多时横向滚动，不参与折叠
      if (c.is_model) {
        col.frozen = true;
        col.widthGrow = 2;
      }

      if (c.numeric) {
        col.formatter = function (cell) {
          var v = cell.getValue();
          var n = Number(v);
          if (!isFinite(n)) return cell.getValue() === 0 ? '0' : '—';
          // 整数字段（题目数、答对数）不能带 % 后缀
          var isInt = c.fmt === 'int';
          var isPct = c.fmt === 'percent';
          var txt = isInt ? String(Math.round(n)) : n.toFixed(2) + (isPct ? '%' : '');
          if (c.primary && payload.baseline !== null && payload.baseline !== undefined) {
            var lift = n - Number(payload.baseline);
            txt += '<span class="ci-cell"> ' + (lift >= 0 ? '+' : '') + lift.toFixed(1) + '</span>';
          }
          return txt;
        };
      }

      if (c.field === 'model' && payload.has_link) {
        col.formatter = function (cell) {
          var row = cell.getRow().getData();
          var name = String(cell.getValue());
          return row.link
            ? '<a href="' + row.link + '" target="_blank" rel="noopener">' + name + '</a>'
            : name;
        };
      }

      if (c.field === 'org' || c.field === 'model') {
        col.headerFilter = 'input';
        col.headerFilterPlaceholder = 'Filter';
      }

      return col;
    });

    var table = new Tabulator(mount, {
      data: payload.rows,
      columns: columns,
      // fitDataFill：列多时横向滚动而不是把列折叠成竖排列表
      // （responsiveLayout:'collapse' 会在列多时把行撑到 200px+ 并隐藏模型名）
      layout: 'fitDataFill',
      responsiveLayout: false,
      pagination: payload.rows.length > 50,
      paginationSize: 50,
      initialSort: [{
        column: payload.primary_metric,
        dir: payload.higher_is_better === false ? 'asc' : 'desc'
      }],
      rowFormatter: function (row) {
        var d = row.getData();
        if (d._top) row.getElement().classList.add('is-top');
        if (d._flagged) row.getElement().classList.add('is-flagged');
      },
      placeholder: 'No matching models'
    });

    var search = document.getElementById('lb-search');
    if (search) {
      search.addEventListener('input', function () {
        var q = search.value.trim().toLowerCase();
        if (!q) { table.clearFilter(true); return; }
        table.setFilter(function (d) {
          return String(d.model || '').toLowerCase().indexOf(q) !== -1 ||
                 String(d.org || '').toLowerCase().indexOf(q) !== -1;
        });
      });
    }
  }

  /* ── 分维度热力图 ──────────────────────────────────── */

  function lerpColor(t) {
    // 白 → 品牌绿；t ∈ [0,1]
    var from = [255, 255, 255];
    var to = [47, 107, 79];
    var r = Math.round(from[0] + (to[0] - from[0]) * t);
    var g = Math.round(from[1] + (to[1] - from[1]) * t);
    var b = Math.round(from[2] + (to[2] - from[2]) * t);
    return 'rgb(' + r + ',' + g + ',' + b + ')';
  }

  function renderBreakdowns(payload) {
    var mount = document.getElementById('breakdown-tables');
    if (!mount || !payload || !payload.tables) return;

    mount.innerHTML = '';

    payload.tables.forEach(function (t) {
      var block = document.createElement('div');
      block.className = 'heat-block';

      var h = document.createElement('h3');
      h.textContent = t.title;
      block.appendChild(h);

      if (t.note) {
        var note = document.createElement('p');
        note.className = 'heat-note';
        note.textContent = t.note;
        block.appendChild(note);
      }

      // 色阶按列独立归一化：跨列难度不同，全表一个色阶会把列间差异抹平
      var bounds = t.dims.map(function (d, i) {
        var vals = t.rows
          .map(function (r) { return r.values[i]; })
          .filter(function (v) { return v !== null && isFinite(v); });
        return vals.length ? { min: Math.min.apply(null, vals), max: Math.max.apply(null, vals) } : null;
      });

      var wrap = document.createElement('div');
      wrap.className = 'heat-scroll';

      var table = document.createElement('table');
      table.className = 'heat';

      var thead = document.createElement('thead');
      var hrow = document.createElement('tr');
      var th0 = document.createElement('th');
      th0.className = 'heat-model';
      th0.scope = 'col';
      th0.textContent = 'Model';
      hrow.appendChild(th0);
      t.dims.forEach(function (d) {
        var th = document.createElement('th');
        th.scope = 'col';
        th.textContent = d;
        hrow.appendChild(th);
      });
      thead.appendChild(hrow);
      table.appendChild(thead);

      var tbody = document.createElement('tbody');
      t.rows.forEach(function (r) {
        var tr = document.createElement('tr');
        var td0 = document.createElement('td');
        td0.className = 'heat-model';
        td0.textContent = r.model;
        tr.appendChild(td0);

        r.values.forEach(function (v, i) {
          var td = document.createElement('td');
          var b = bounds[i];
          if (v === null || !isFinite(v)) {
            td.className = 'heat-empty';
            td.textContent = '—';
          } else {
            var span = b ? (b.max - b.min) : 0;
            var ratio = span > 0 ? (v - b.min) / span : 1;
            td.textContent = v.toFixed(1);
            td.style.background = lerpColor(0.08 + ratio * 0.72);
            td.style.color = ratio > 0.62 ? '#fff' : 'var(--ink)';
          }
          tr.appendChild(td);
        });

        tbody.appendChild(tr);
      });
      table.appendChild(tbody);

      wrap.appendChild(table);
      block.appendChild(wrap);
      mount.appendChild(block);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var lb = readJSON('leaderboard-data');
    if (lb) renderLeaderboard(lb);
    renderBreakdowns(readJSON('breakdown-data'));
  });
})();
