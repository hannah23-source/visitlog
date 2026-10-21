document.addEventListener("DOMContentLoaded", () => {
    const verifyButton = document.getElementById("verifyLocation");
    const locationMessage = document.getElementById("locationMessage");
    const registrationForm = document.getElementById("visitorForm");
    const locationBadge = document.getElementById("locationBadge");

    if (!verifyButton || !locationMessage) {
        console.error("Location verification elements were not found.");
        return;
    }

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
                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;

                console.log("Latitude:", latitude);
                console.log("Longitude:", longitude);
                console.log(
                    "GPS accuracy (meters):",
                    position.coords.accuracy
                );

                locationMessage.textContent =
                    "Checking your school location...";

                try {
                    const csrfInput = document.querySelector(
                        '#csrfForm [name="csrfmiddlewaretoken"]'
                    );

                    const csrfToken = csrfInput
                        ? csrfInput.value
                        : getCookie("csrftoken");

                    if (!csrfToken) {
                        throw new Error(
                            "CSRF token missing. Refresh the page and try again."
                        );
                    }

                    const response = await fetch("/check-location/", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": csrfToken
                        },
                        credentials: "same-origin",
                        body: JSON.stringify({
                            latitude: latitude,
                            longitude: longitude
                        })
                    });

                    let result;

                    try {
                        result = await response.json();
                    } catch {
                        throw new Error(
                            "Unable to verify your location. Please try again."
                        );
                    }

                    console.log("Server status:", response.status);
                    console.log("Server location check:", result);

                    if (!response.ok) {
                        throw new Error(
                            "Unable to verify your location. Please try again."
                        );
                    }

                    if (!result.allowed) {
                        if (registrationForm) {
                            registrationForm.hidden = true;
                        }

                        if (locationBadge) {
                            locationBadge.textContent =
                                "Location not verified";
                        }

                        locationMessage.textContent =
                            "You are not within the school location.";

                        return;
                    }

                    locationMessage.textContent =
                        "Welcome, visitor! Location verified.";

                    if (locationBadge) {
                        locationBadge.textContent =
                            "Location verified";
                    }

                    if (registrationForm) {
                        registrationForm.hidden = false;
                    }

                    verifyButton.hidden = true;

                } catch (error) {
                    console.error("Location verification error:", error);

                    locationMessage.textContent =
                        error.message ||
                        "Unable to verify your location. Please try again.";

                } finally {
                    verifyButton.disabled = false;
                }
            },

            (error) => {
                console.error("GPS error:", error);

                if (error.code === error.PERMISSION_DENIED) {
                    locationMessage.textContent =
                        "Please allow location access to continue.";
                } else if (error.code === error.POSITION_UNAVAILABLE) {
                    locationMessage.textContent =
                        "Your location is currently unavailable. Please try again.";
                } else if (error.code === error.TIMEOUT) {
                    locationMessage.textContent =
                        "Getting your location took too long. Please try again.";
                } else {
                    locationMessage.textContent =
                        "Unable to get your location. Please try again.";
                }

                verifyButton.disabled = false;
            },

            {
                enableHighAccuracy: true,
                timeout: 20000,
                maximumAge: 0
            }
        );
    });

    function getCookie(name) {
        const cookies = document.cookie
            ? document.cookie.split(";")
            : [];

        for (const cookie of cookies) {
            const trimmedCookie = cookie.trim();

            if (trimmedCookie.startsWith(name + "=")) {
                return decodeURIComponent(
                    trimmedCookie.substring(name.length + 1)
                );
            }
        }

        return "";
    }
});
