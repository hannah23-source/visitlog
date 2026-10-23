document.addEventListener("DOMContentLoaded", () => {
    const verifyButton = document.getElementById("verifyLocation");
    const locationMessage = document.getElementById("locationMessage");
    const locationBadge = document.getElementById("locationBadge");
    const locationSection = document.getElementById("locationSection");
    const visitorSection = document.getElementById("visitorSection");
    const visitorForm = document.getElementById("visitorForm");

    if (
        !locationSection ||
        !visitorSection
    ) {
        console.error("VisitLog: Required HTML elements are missing.");
        return;
    }

    // If Django already rendered the registration form, keep it visible.
    const registrationAlreadyVisible = !visitorSection.hidden;

    if (registrationAlreadyVisible) {
        locationSection.hidden = true;
        visitorSection.hidden = false;
        return;
    }

    // Ask Django whether the temporary testing bypass is enabled.
    async function checkTestingMode() {
        if (!verifyButton || !locationMessage || !locationBadge) {
            return;
        }

        try {
            verifyButton.disabled = true;
            verifyButton.textContent = "Loading...";

            const response = await fetch("/check-location/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken")
                },
                credentials: "same-origin",
                body: JSON.stringify({})
            });

            const result = await response.json();

            if (response.ok && result.testing_mode === true &&
                result.allowed === true) {
                locationSection.hidden = true;
                visitorSection.hidden = false;

                if (visitorForm) {
                    visitorForm.hidden = false;
                }

                return;
            }
        } catch (error) {
            console.error("Testing mode check failed:", error);
        }

        // Bypass is not active; require normal GPS verification.
        locationSection.hidden = false;
        visitorSection.hidden = true;

        verifyButton.disabled = false;
        verifyButton.innerHTML =
            '<i class="fa-solid fa-location-crosshairs"></i> Verify My Location';

        locationBadge.textContent = "Location not verified";
        locationMessage.textContent =
            "Please verify that you are within the school premises.";
    }

    if (verifyButton) {
        verifyButton.addEventListener("click", () => {
            if (!navigator.geolocation) {
                locationMessage.textContent =
                    "Your browser does not support location access.";
                return;
            }

            verifyButton.disabled = true;
            verifyButton.textContent = "Checking location...";
            locationMessage.textContent =
                "Please allow location access.";
            locationBadge.textContent = "Checking...";

            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    try {
                        const response = await fetch("/check-location/", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                                "X-CSRFToken": getCookie("csrftoken")
                            },
                            credentials: "same-origin",
                            body: JSON.stringify({
                                latitude: position.coords.latitude,
                                longitude: position.coords.longitude
                            })
                        });

                        const result = await response.json();

                        locationMessage.textContent =
                            result.message || "Location verification failed.";

                        if (response.ok && result.allowed === true) {
                            locationBadge.textContent = "Location verified";
                            locationSection.hidden = true;
                            visitorSection.hidden = false;

                            if (visitorForm) {
                                visitorForm.hidden = false;
                            }
                        } else {
                            locationBadge.textContent =
                                "Outside school location";
                            visitorSection.hidden = true;
                            locationSection.hidden = false;
                            verifyButton.disabled = false;
                            verifyButton.textContent = "Verify My Location";
                        }
                    } catch (error) {
                        console.error("Location verification error:", error);
                        locationMessage.textContent =
                            "Could not verify your location. Please try again.";
                        locationBadge.textContent = "Verification failed";
                        verifyButton.disabled = false;
                        verifyButton.textContent = "Verify My Location";
                    }
                },
                (error) => {
                    console.error("Browser location error:", error);

                    locationMessage.textContent =
                        error.code === 1
                            ? "Location access was denied. Please allow it in your browser."
                            : "Unable to get your location. Please try again.";

                    locationBadge.textContent = "Verification failed";
                    verifyButton.disabled = false;
                    verifyButton.textContent = "Verify My Location";
                },
                {
                    enableHighAccuracy: true,
                    timeout: 15000,
                    maximumAge: 0
                }
            );
        });
    }

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

    checkTestingMode();
});