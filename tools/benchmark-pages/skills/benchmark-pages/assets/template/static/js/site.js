/* benchmark-pages · 站点交互：BibTeX 复制、锚点导航 */
(function () {
  'use strict';

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    // file:// 下 clipboard API 不可用时的兜底
    return new Promise(function (resolve, reject) {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand('copy') ? resolve() : reject(new Error('copy failed'));
      } catch (e) {
        reject(e);
      } finally {
        document.body.removeChild(ta);
      }
    });
  }

  document.querySelectorAll('[data-copy-target]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var target = document.getElementById(btn.getAttribute('data-copy-target'));
      if (!target) return;
      var label = btn.querySelector('.copy-text');
      var original = label ? label.textContent : '';

      copyText(target.innerText).then(
        function () {
          btn.classList.add('is-done');
          if (label) label.textContent = 'Copied';
          setTimeout(function () {
            btn.classList.remove('is-done');
            if (label) label.textContent = original;
          }, 1800);
        },
        function () {
          if (label) label.textContent = 'Copy failed; select the text manually';
          setTimeout(function () { if (label) label.textContent = original; }, 2600);
        }
      );
    });
  });
})();
