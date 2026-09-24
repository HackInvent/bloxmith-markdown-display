import { withProperties } from "./properties.js";



/**
 * Mark the Markdown Display modal as block-owned while the framework keeps
 * generic title/apply/copy controls.
 *
 * @param {HTMLElement} root - Mounted Markdown Display modal root.
 */
function mountOwned(root) {
  if (root instanceof HTMLElement) {
    root.dataset.markdownDisplayModalMounted = "true";
  }
}

/** Keep the block behavior and add properties-only accessibility. */
export function mount(root, ...args) {
  return withProperties(mountOwned).call(this, root, ...args);
}
