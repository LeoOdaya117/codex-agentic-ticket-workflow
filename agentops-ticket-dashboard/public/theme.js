try {
  const savedTheme = localStorage.getItem("agentops-theme");
  const prefersLight = window.matchMedia?.("(prefers-color-scheme: light)").matches;
  document.documentElement.dataset.theme =
    savedTheme === "light" || savedTheme === "dark"
      ? savedTheme
      : prefersLight ? "light" : "dark";
} catch {
  document.documentElement.dataset.theme = "dark";
}
