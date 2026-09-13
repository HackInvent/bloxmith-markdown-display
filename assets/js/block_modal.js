(function () {
  "use strict";

  const registry = (window.CWBlockUiBlocks = window.CWBlockUiBlocks || {});

  registry.markdown_display = {
    /**
     * Mark the Markdown Display modal as block-owned while the framework keeps
     * generic title/apply/copy controls.
     *
     * @param {HTMLElement} root - Mounted Markdown Display modal root.
     */
    mount(root) {
      if (root instanceof HTMLElement) {
        root.dataset.markdownDisplayModalMounted = "true";
      }
    },
  };
})();
