const modal = document.getElementById("google-modal");


function connectGoogle() {

    modal.classList.remove("hidden");

}


function closeGoogleModal() {

    modal.classList.add("hidden");

}


function continueGoogleAuth() {

    window.location.href = "/auth/google";

}


async function loadConnections() {

    try {

        const response = await fetch(
            "/api/connections"
        );

        const data = await response.json();


        updateStatus(
            "gmail-status",
            data.gmail
        );

        updateStatus(
            "calendar-status",
            data.calendar
        );

        updateStatus(
            "drive-status",
            data.drive
        );

    } catch (error) {

        console.error(
            "Erreur chargement connexions:",
            error
        );

    }

}


function updateStatus(elementId, connected) {

    const element =
        document.getElementById(elementId);

    if (!element) {
        return;
    }


    if (connected) {

        element.textContent =
            "Connecté";

        element.classList.remove(
            "disconnected"
        );

        element.classList.add(
            "connected"
        );

    } else {

        element.textContent =
            "Non connecté";

        element.classList.remove(
            "connected"
        );

        element.classList.add(
            "disconnected"
        );

    }

}


loadConnections();
