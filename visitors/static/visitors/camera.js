
document.addEventListener("DOMContentLoaded", () => {
    const video = document.getElementById("cameraPreview");
    const canvas = document.getElementById("cameraCanvas");
    const uploadInput = document.getElementById("id_document");
    const preview = document.getElementById("capturedImage");

    const openButton = document.getElementById("openCamera");
    const captureButton = document.getElementById("capturePhoto");
    const cancelButton = document.getElementById("cancelCamera");
    const retakeButton = document.getElementById("retakePhoto");

    const message = document.getElementById("cameraMessage");
    const form = document.getElementById("visitorForm");

    if (
        !video || !canvas || !uploadInput || !preview ||
        !openButton || !captureButton || !cancelButton ||
        !retakeButton || !form
    ) {
        console.error("Camera setup failed: missing HTML element.");
        return;
    }

    let stream = null;
    let photoUrl = null;
    let openingCamera = false;

    // Hidden input for the captured photo.
    let cameraInput = document.getElementById("camera_capture");

    if (!cameraInput) {
        cameraInput = document.createElement("input");
        cameraInput.type = "file";
        cameraInput.id = "camera_capture";
        cameraInput.name = "camera_capture";
        cameraInput.accept = "image/jpeg,image/png";
        cameraInput.hidden = true;
        form.appendChild(cameraInput);
    }

    function showMessage(text) {
        if (message) message.textContent = text;
    }

    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
        video.srcObject = null;
    }

    function clearPreview() {
        cameraInput.value = "";

        if (photoUrl) {
            URL.revokeObjectURL(photoUrl);
            photoUrl = null;
        }

        preview.removeAttribute("src");
        preview.hidden = true;
    }

    function resetButtons() {
        openButton.hidden = false;
        captureButton.hidden = true;
        cancelButton.hidden = true;
        retakeButton.hidden = true;
        captureButton.disabled = false;
    }

    // OPEN CAMERA
    openButton.addEventListener("click", async () => {
        if (openingCamera) return;

        openingCamera = true;
        openButton.disabled = true;
        showMessage("Opening camera...");

        try {
            if (!window.isSecureContext) {
                throw new Error(
                    "INSECURE_CONTEXT: Open the deployed website using HTTPS."
                );
            }

            if (!navigator.mediaDevices ||
                !navigator.mediaDevices.getUserMedia) {
                throw new Error(
                    "CAMERA_API_UNAVAILABLE: This browser does not provide camera access."
                );
            }

            stopCamera();
            clearPreview();

            // Prefer the phone's rear camera.
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: { ideal: "environment" } },
                    audio: false
                });
            } catch (firstError) {
                console.warn(
                    "Rear camera attempt failed; trying default camera:",
                    firstError.name,
                    firstError.message
                );

                // Try the default camera if the rear camera is unavailable.
                stream = await navigator.mediaDevices.getUserMedia({
                    video: true,
                    audio: false
                });
            }

            video.srcObject = stream;
            video.hidden = false;
            preview.hidden = true;

            await video.play();

            openButton.hidden = true;
            captureButton.hidden = false;
            cancelButton.hidden = false;
            retakeButton.hidden = true;

            showMessage("Camera ready. Position your ID clearly.");

        } catch (error) {
            console.error("CAMERA ERROR NAME:", error.name);
            console.error("CAMERA ERROR MESSAGE:", error.message);
            console.error("CAMERA ERROR DETAILS:", error);

            stopCamera();
            video.hidden = true;
            resetButtons();

            let explanation = error.message || "Unknown camera error.";

            if (error.name === "NotAllowedError" ||
                error.name === "PermissionDeniedError") {
                explanation =
                    "Camera permission was denied or blocked. Check the browser and phone settings.";
            } else if (error.name === "NotFoundError") {
                explanation =
                    "No available camera was found by the browser.";
            } else if (error.name === "NotReadableError") {
                explanation =
                    "The camera may be busy or blocked by another app. Close other apps using the camera and retry.";
            } else if (error.name === "OverconstrainedError") {
                explanation =
                    "The requested camera settings are unavailable. Try the default camera.";
            } else if (error.name === "AbortError") {
                explanation =
                    "Camera startup was interrupted. Please try again.";
            } else if (error.name === "SecurityError") {
                explanation =
                    "The browser blocked camera access for security reasons.";
            }

            showMessage("Camera error: " + explanation);

        } finally {
            openingCamera = false;
            openButton.disabled = false;
        }
    });

    // CAPTURE PHOTO
    captureButton.addEventListener("click", () => {
        if (!video.videoWidth || !video.videoHeight) {
            showMessage("Camera is starting. Please wait and try again.");
            return;
        }

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const context = canvas.getContext("2d");

        if (!context) {
            showMessage("Unable to capture the photo. Please try again.");
            return;
        }

        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        captureButton.disabled = true;

        canvas.toBlob(blob => {
            if (!blob) {
                captureButton.disabled = false;
                showMessage("Photo capture failed. Please try again.");
                return;
            }

            const file = new File([blob], "visitor-id.jpg", {
                type: "image/jpeg"
            });

            const transfer = new DataTransfer();
            transfer.items.add(file);
            cameraInput.files = transfer.files;

            uploadInput.value = "";

            if (photoUrl) URL.revokeObjectURL(photoUrl);
            photoUrl = URL.createObjectURL(file);

            preview.src = photoUrl;
            preview.hidden = false;
            video.hidden = true;

            stopCamera();

            openButton.hidden = true;
            captureButton.hidden = true;
            cancelButton.hidden = false;
            retakeButton.hidden = false;

            showMessage("Photo captured. Check your ID before registering.");
        }, "image/jpeg", 0.92);
    });

    // CANCEL CAMERA
    cancelButton.addEventListener("click", () => {
        stopCamera();
        clearPreview();

        video.hidden = true;
        canvas.width = 0;
        canvas.height = 0;

        resetButtons();
        showMessage("Camera closed. You can reopen it or upload an ID.");
    });

    // RETAKE PHOTO
    retakeButton.addEventListener("click", () => {
        stopCamera();
        clearPreview();

        video.hidden = true;
        canvas.width = 0;
        canvas.height = 0;

        resetButtons();
        showMessage("Tap Open Camera to take another photo.");
    });

    // UPLOAD ID INSTEAD
    uploadInput.addEventListener("change", () => {
        if (!uploadInput.files.length) return;

        stopCamera();
        clearPreview();

        video.hidden = true;
        resetButtons();

        showMessage("ID file selected.");
    });

    // VALIDATE ID
    form.addEventListener("submit", event => {
        const selectedFile =
            cameraInput.files[0] || uploadInput.files[0];

        if (!selectedFile) {
            event.preventDefault();
            showMessage("Please capture or upload your ID.");
            return;
        }

        if (!["image/jpeg", "image/png"].includes(selectedFile.type)) {
            event.preventDefault();
            showMessage("JPG or PNG images only.");
            return;
        }

        if (selectedFile.size > 5 * 1024 * 1024) {
            event.preventDefault();
            showMessage("The ID image must not exceed 5 MB.");
        }
    });

    window.addEventListener("pagehide", stopCamera);

    console.log("CAMERA.JS IS LOADED");
});

