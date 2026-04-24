const signInForm = document.querySelector("#landing-sign-in");
const usernameInput = document.querySelector("#landing-username");
const passwordInput = document.querySelector("#landing-password");
const statusText = document.querySelector("#landing-sign-in-status");

signInForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusText.textContent = "Signing in...";
  try {
    const response = await fetch("/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "same-origin",
      body: JSON.stringify({
        username: usernameInput.value.trim(),
        password: passwordInput.value,
      }),
    });
    if (!response.ok) {
      throw new Error("Invalid username or password");
    }
    window.location.href = "/dashboard";
  } catch (error) {
    statusText.textContent = "Sign in failed. Check the username and password.";
  }
});
