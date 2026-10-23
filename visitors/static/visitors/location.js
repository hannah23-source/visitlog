
document.addEventListener("DOMContentLoaded", () => {
    const verifyButton = document.getElementById("verifyLocation");
    const locationMessage = document.getElementById("locationMessage");
    const locationBadge = document.getElementById("locationBadge");
    const locationSection = document.getElementById("locationSection");
    const visitorSection = document.getElementById("visitorSection");
    const visitorForm = document.getElementById("visitorForm");

    if (!locationSection || !visitorSection) {
        console.error("VisitLog: Required HTML elements are missing.");
        return;
    }

    function showRegistration() {
        locationSection.hidden = true;
        visitorSection.hidden = false;

        if (visitorForm) {
            visitorForm.hidden = false;
        }
    }

    function showLocationVerification() {
        locationSection.hidden = false;
        visitorSection.hidden = true;

        if (verifyButton) {
            verifyButton.disabled = false;
            verifyButton.innerHTML =
                '<i class="fa-solid fa-location-crosshairs"></i> Verify My Location';
        }
    }

    function getCookie(name) {
        const cookies = document.cookie
            ? document.cookie.split(";")
            : [];

        for (const cookie of cookies) {
            const item = cookie.trim();

            if (item.startsWith(name + "=")) {
                return decodeURIComponent(
                    item.substring(name.length + 1)
                );
            }
        }

        return "";
    }

    function getCsrfToken() {
        const cookieToken = getCookie("csrftoken");
        const formToken = document.querySelector(
            'input[name="csrfmiddlewaretoken"]'
        );

        return cookieToken || (formToken ? formToken.value : "");
    }

    async function checkTestingMode() {
        if (!verifyButton) {
            return;
        }

        try {
            verifyButton.disabled = true;
            verifyButton.textContent = "Checking registration access...";

            const response = await fetch("/check-location/", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken()
                },
                body: JSON.stringify({})
            });

            const result = await response.json();

            console.log("VisitLog location check:", response.status, result);

            if (
                response.ok &&
                result.allowed === true &&
                result.testing_mode === true
            ) {
                showRegistration();
                console.log("VisitLog: Testing bypass enabled.");
                return;
            }

            // The bypass is not active. Require normal location verification.
            showLocationVerification();

            if (locationMessage) {
                locationMessage.textContent =
                    result.message ||
                    "Please verify your location to continue.";
            }

            if (locationBadge) {
                locationBadge.textContent = "Location not verified";
            }

            if (!response.ok) {
                console.error(
                    "VisitLog: Location check request failed.",
                    response.status,
                    result
                );
            }
        } catch (error) {
            console.error("VisitLog: Could not check testing mode.", error);
            showLocationVerification();

            if (locationMessage) {
                locationMessage.textContent =
                    "Unable to check registration access. Please try again.";
            }
        }
    }

    if (verifyButton) {
        verifyButton.addEventListener("click", () => {
            if (!navigator.geolocation) {
                if (locationMessage) {
                    locationMessage.textContent =
                        "Your browser does not support location access.";
                }
                return;
            }

            verifyButton.disabled = true;
            verifyButton.textContent = "Checking location...";

            if (locationMessage) {
                locationMessage.textContent =
                    "Please allow location access.";
            }

            if (locationBadge) {
                locationBadge.textContent = "Checking...";
            }

            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    try {
                        const response = await fetch("/check-location/", {
                            method: "POST",
                            credentials: "same-origin",
                            headers: {
                                "Content-Type": "application/json",
                                "X-CSRFToken": getCsrfToken()
                            },
                            body: JSON.stringify({
                                latitude: position.coords.latitude,
                                longitude: position.coords.longitude
                            })
                        });

                        const result = await response.json();

                        if (locationMessage) {
                            locationMessage.textContent =
                                result.message ||
                                "Location verification failed.";
                        }

                        if (
                            response.ok &&
                            result.allowed === true
                        ) {
                            if (locationBadge) {
                                locationBadge.textContent =
                                    result.testing_mode
                                        ? "Testing mode"
                                        : "Location verified";
                            }

                            showRegistration();
                        } else {
                            showLocationVerification();

                            if (locationBadge) {
                                locationBadge.textContent =
                                    "Outside school location";
                            }
                        }
                    } catch (error) {
                        console.error(
                            "VisitLog: Location verification failed.",
                            error
                        );

                        showLocationVerification();

                        if (locationMessage) {
                            locationMessage.textContent =
                                "Could not verify your location. Please try again.";
                        }

                        if (locationBadge) {
                            locationBadge.textContent =
                                "Verification failed";
                        }
                    }
                },
                (error) => {
                    console.error("Browser location error:", error);
                    showLocationVerification();

                    if (locationMessage) {
                        locationMessage.textContent =
                            error.code === 1
                                ? "Location access was denied. Please allow it in your browser."
                                : "Unable to get your location. Please try again.";
                    }

                    if (locationBadge) {
                        locationBadge.textContent = "Verification failed";
                    }
                },
                {
                    enableHighAccuracy: true,
                    timeout: 15000,
                    maximumAge: 0
                }
            );
        });
    }

    // If Django already displayed the form, keep it visible.
    if (!visitorSection.hidden) {
        showRegistration();
        return;
    }

    // Ask the server whether the temporary bypass is enabled.
    checkTestingMode();
});
