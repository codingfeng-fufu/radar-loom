/* Small shared state helpers used by the standalone Viewer surfaces. */
(function (root) {
  function setState(element, kind, title, detail) {
    if (!element) return;
    element.className = `rl-state rl-state-${kind}`;
    element.replaceChildren();
    const heading = document.createElement('strong');
    heading.className = 'rl-state-title';
    heading.textContent = title || '';
    element.append(heading);
    if (detail) {
      const body = document.createElement('span');
      body.className = 'rl-state-detail';
      body.textContent = detail;
      element.append(body);
    }
  }
  root.RadarLoomUI = Object.freeze({ setState });
})(window);
