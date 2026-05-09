document.addEventListener("DOMContentLoaded", () => {
  const firstEmptyInput = document.querySelector("input:not([type='hidden'])");

  if (firstEmptyInput && !firstEmptyInput.value) {
    firstEmptyInput.focus();
  }
});
