document.addEventListener("DOMContentLoaded", function () {
  const darkModeToggle = document.getElementById("appThemeDarkMode");
  const body = document.body;
  const navbar = document.querySelector(".navbar");
  const sidebar = document.querySelector(".sidebar");
  const cards = document.querySelectorAll(".card");
  const tables = document.querySelectorAll(".table");

  // Check for saved preference
  if (localStorage.getItem("dark-mode") === "enabled") {
    body.classList.add("dark-mode");
    navbar.classList.add("navbar-dark-mode");
    sidebar.classList.add("sidebar-dark-mode");
    cards.forEach((card) => card.classList.add("card-dark-mode"));
    tables.forEach((table) => table.classList.add("table-dark-mode"));
    darkModeToggle.checked = true;
  }

  darkModeToggle.addEventListener("change", function () {
    if (darkModeToggle.checked) {
      body.classList.add("dark-mode");
      navbar.classList.add("navbar-dark-mode");
      sidebar.classList.add("sidebar-dark-mode");
      cards.forEach((card) => card.classList.add("card-dark-mode"));
      tables.forEach((table) => table.classList.add("table-dark-mode"));
      localStorage.setItem("dark-mode", "enabled");
    } else {
      body.classList.remove("dark-mode");
      navbar.classList.remove("navbar-dark-mode");
      sidebar.classList.remove("sidebar-dark-mode");
      cards.forEach((card) => card.classList.remove("card-dark-mode"));
      tables.forEach((table) => table.classList.remove("table-dark-mode"));
      localStorage.removeItem("dark-mode");
    }
  });
});
