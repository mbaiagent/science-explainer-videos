// 通用统计脚本：文章页阅读量 / 视频页播放量
// 用法：<script src="../assets/stats.js" data-kind="reads"></script>
// data-kind: reads（文章）| views（视频）
(function () {
  var s = document.currentScript;
  var kind = (s && s.getAttribute('data-kind')) || 'reads';
  var topic = location.pathname.split('/')[1];
  if (!topic || !/^[a-z0-9-]+$/.test(topic)) return;

  var key = kind + '_' + topic, record = true;
  try {
    record = !sessionStorage.getItem(key);
    if (record) sessionStorage.setItem(key, '1');
  } catch (e) {}

  fetch('/api/' + kind + '/' + topic, { method: record ? 'POST' : 'GET' })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (!d || !d.pv) return;
      var label = kind === 'views'
        ? '▶ ' + d.pv + ' 次播放 · ' + d.uv + ' 人看过'
        : '📖 ' + d.pv + ' 次阅读 · ' + d.uv + ' 人读过';
      var meta = document.querySelector('header.hero .meta');
      if (meta) meta.textContent += ' · ' + label;
    })
    .catch(function () {});
})();
