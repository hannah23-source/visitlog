
document.addEventListener("DOMContentLoaded", () => {
    const verifyButton = document.getElementById("verifyLocation");
    const locationMessage = document.getElementById("locationMessage");
    const locationBadge = document.getElementById("locationBadge");
    const locationSection = document.getElementById("locationSection");
    const visitorSection = document.getElementById("visitorSection");
    const visitorForm = document.getElementById("visitorForm");

    if (
        !verifyButton ||
        !locationMessage ||
        !locationBadge ||
        !locationSection ||
        !visitorSection ||
        !visitorForm
    ) {
        console.error("VisitLog: A required HTML element is missing.");
        return;
    }

    // Keep the registration form hidden until location is verified.
    visitorSection.hidden = true;

    verifyButton.addEventListener("click", () => {
        if (!navigator.geolocation) {
            locationMessage.textContent =
                "Your browser does not support location access.";
            return;
        }

        verifyButton.disabled = true;
        verifyButton.textContent = "Checking location...";
        locationMessage.textContent = "Please allow location access.";
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
                        visitorForm.hidden = false;
                    } else {
                        locationBadge.textContent = "Outside school location";
                        visitorSection.hidden = true;
                        verifyButton.disabled = false;
                        verifyButton.innerHTML =
                            '<i class="fa-solid fa-location-crosshairs"></i> Verify My Location';
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

                if (error.code === 1) {
                    locationMessage.textContent =
                        "Location access was denied. Please allow location access in your browser.";
                } else if (error.code === 2) {
                    locationMessage.textContent =
                        "Your location could not be detected. Please try again.";
                } else if (error.code === 3) {
                    locationMessage.textContent =
                        "Location request timed out. Please try again.";
                } else {
                    locationMessage.textContent =
                        "Unable to get your location. Please try again.";
                }

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

    function getCookie(name) {
        const cookies = document.cookie ? document.cookie.split(";") : [];

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
