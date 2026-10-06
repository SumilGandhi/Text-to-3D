const button = document.getElementById("generateButton");
const promptInput = document.getElementById("prompt");
const status = document.getElementById("status");

button.addEventListener("click", async () => {

    const prompt = promptInput.value.trim();

    if (!prompt) {
        status.textContent = "Please enter a description.";
        return;
    }

    status.textContent = "Sending request...";

    try {

        const response = await fetch(
            "/generate",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ prompt })
            }
        );

        const data = await response.json();

        status.textContent =
            `Backend received: ${data.prompt}`;

    } catch (error) {

        console.error(error);

        status.textContent =
            "Could not connect to the backend.";
    }
});

