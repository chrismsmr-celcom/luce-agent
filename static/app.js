const navItems = document.querySelectorAll(".nav-item");
const views = document.querySelectorAll(".view");


// ---------------------------------------------------------
// NAVIGATION
// ---------------------------------------------------------

navItems.forEach((button) => {

    button.addEventListener("click", () => {

        const target = button.dataset.view;

        navItems.forEach((item) => {
            item.classList.remove("active");
        });

        button.classList.add("active");

        views.forEach((view) => {
            view.classList.remove("active");
        });

        document
            .getElementById(`${target}-view`)
            .classList.add("active");

    });

});


// ---------------------------------------------------------
// CONNECTIONS
// ---------------------------------------------------------

async function loadConnections() {

    try {

        const response = await fetch(
            "/api/connections"
        );

        const data = await response.json();

        document
            .querySelectorAll(".connection-card")
            .forEach((card) => {

                const toolkit =
                    card.dataset.toolkit;

                const connected =
                    data[toolkit] === true;

                const status =
                    card.querySelector(".status");

                const button =
                    card.querySelector(".connect-button");

                if (connected) {

                    status.textContent =
                        "Connected";

                    status.classList.add(
                        "connected"
                    );

                    button.textContent =
                        "Connected";

                    button.disabled = true;

                }

            });

    } catch (error) {

        console.error(
            "Connection status error:",
            error
        );

    }

}


document
    .querySelectorAll(".connect-button")
    .forEach((button) => {

        button.addEventListener(
            "click",
            async () => {

                const card =
                    button.closest(
                        ".connection-card"
                    );

                const toolkit =
                    card.dataset.toolkit;

                button.disabled = true;

                button.textContent =
                    "Connecting...";

                try {

                    const response =
                        await fetch(
                            `/api/connect/${toolkit}`,
                            {
                                method: "POST",
                            }
                        );

                    const data =
                        await response.json();

                    if (!response.ok) {
                        throw new Error(
                            data.error ||
                            "Connection failed"
                        );
                    }

                    if (data.redirect_url) {

                        window.location.href =
                            data.redirect_url;

                    }

                } catch (error) {

                    console.error(error);

                    button.disabled = false;

                    button.textContent =
                        "Connect";

                    alert(
                        "Connection failed: " +
                        error.message
                    );

                }

            }
        );

    });


// ---------------------------------------------------------
// CHAT
// ---------------------------------------------------------

const chatForm =
    document.getElementById(
        "chat-form"
    );

const input =
    document.getElementById(
        "message-input"
    );

const messages =
    document.getElementById(
        "messages"
    );


function addMessage(
    content,
    type
) {

    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        `message ${type}`;

    const bubble =
        document.createElement(
            "div"
        );

    bubble.className =
        "bubble";

    bubble.textContent =
        content;

    wrapper.appendChild(
        bubble
    );

    messages.appendChild(
        wrapper
    );

    messages.scrollTop =
        messages.scrollHeight;
}


chatForm.addEventListener(
    "submit",
    async (event) => {

        event.preventDefault();

        const message =
            input.value.trim();

        if (!message) {
            return;
        }

        addMessage(
            message,
            "user"
        );

        input.value = "";

        try {

            const response =
                await fetch(
                    "/api/chat",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",
                        },

                        body: JSON.stringify({
                            message,
                        }),
                    }
                );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.error ||
                    "Request failed"
                );
            }

            addMessage(
                data.message ||
                "No response.",
                "assistant"
            );

        } catch (error) {

            addMessage(
                "Error: " +
                error.message,
                "assistant"
            );

        }

    }
);


// ---------------------------------------------------------
// INITIALIZATION
// ---------------------------------------------------------

loadConnections();
