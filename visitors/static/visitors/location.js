const verifyButton = document.getElementById("verifyLocation");
const locationMessage = document.getElementById("locationMessage");
const registrationForm = document.getElementById("visitorForm");

verifyButton.addEventListener("click", () => {
    if (!navigator.geolocation) {
        locationMessage.textContent =
            "Your browser does not support location services.";
        return;
    }

    verifyButton.disabled = true;
    locationMessage.textContent =
        "Getting your location. Please allow location access.";

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            try {
                const csrfToken = document.querySelector(
                    '[name="csrfmiddlewaretoken"]'
                ).value;

                const response = await fetch("/check-location/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken
                    },
                    body: JSON.stringify({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude
                    })
                });

                const result = await response.json();

                if (!response.ok || !result.allowed) {
                    registrationForm.hidden = true;
                    locationMessage.textContent =
                        result.message || "Location verification failed.";
                    return;
                }

                locationMessage.textContent =
                    "Welcome, visitor! Location verified.";

                registrationForm.hidden = false;
                verifyButton.hidden = true;

            } catch (error) {
                console.error(error);
                locationMessage.textContent =
                    "Unable to verify your location. Please try again.";
            } finally {
                verifyButton.disabled = false;
            }
        },
        (error) => {
            if (error.code === error.PERMISSION_DENIED) {
                locationMessage.textContent =
                    "Please allow location access to continue.";
            } else {
                locationMessage.textContent =
                    "Unable to get your location. Please try again.";
            }

            verifyButton.disabled = false;
        },
        {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0
        }
    );
});
