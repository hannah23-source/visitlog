    const video = document.getElementById("cameraPreview");
    const canvas = document.getElementById("cameraCanvas");
    const uploadInput = document.getElementById("id_document");
    const cameraInput = document.getElementById("camera_capture");
    const preview = document.getElementById("capturedPreview");

    const openButton = document.getElementById("openCamera");
    const captureButton = document.getElementById("capturePhoto");
    const retakeButton = document.getElementById("retakePhoto");
    const message = document.getElementById("cameraMessage");
    const form = document.getElementById("visitorForm");

    let stream = null;
    let photoUrl = null;

    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }

        video.srcObject = null;
    }

    function clearCapturedPhoto() {
        cameraInput.value = "";

        if (photoUrl) {
            URL.revokeObjectURL(photoUrl);
            photoUrl = null;
        }

        preview.removeAttribute("src");
        preview.hidden = true;
        retakeButton.hidden = true;
    }

    openButton.addEventListener("click", async () => {
        try {
            if (!navigator.mediaDevices?.getUserMedia) {
                throw new Error("Camera requires HTTPS or localhost.");
            }

            stopCamera();

            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: { ideal: "environment" }
                },
                audio: false
            });

            video.srcObject = stream;
            video.hidden = false;
            preview.hidden = true;

            await video.play();

            openButton.hidden = true;
            captureButton.disabled = false;
            retakeButton.hidden = true;
            message.textContent = "Camera is ready. Position your ID clearly.";

        } catch (error) {
            console.error(error);
            message.textContent =
                "Unable to open camera. Allow camera permission and try again.";
        }
    });

    captureButton.addEventListener("click", () => {
        if (!video.videoWidth || !video.videoHeight) {
            message.textContent = "Please wait for the camera to start.";
            return;
        }

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        canvas.getContext("2d").drawImage(
            video, 0, 0, canvas.width, canvas.height
        );

        canvas.toBlob(blob => {
            if (!blob) {
                message.textContent = "Photo capture failed. Please try again.";
                return;
            }

            const file = new File(
                [blob],
                "visitor-id.jpg",
                { type: "image/jpeg" }
            );

            const transfer = new DataTransfer();
            transfer.items.add(file);
            cameraInput.files = transfer.files;

            // Use either the uploaded image or the camera photo, not both.
            uploadInput.value = "";

            clearPreviewUrlOnly();

            photoUrl = URL.createObjectURL(file);
            preview.src = photoUrl;
            preview.hidden = false;
            video.hidden = true;

            captureButton.disabled = true;
            retakeButton.hidden = false;
            stopCamera();

            message.textContent =
                "Photo captured. Check that your ID is clear before registering.";
        }, "image/jpeg", 0.92);
    });

    function clearPreviewUrlOnly() {
        if (photoUrl) {
            URL.revokeObjectURL(photoUrl);
            photoUrl = null;
        }
    }

    retakeButton.addEventListener("click", () => {
        clearCapturedPhoto();

        video.hidden = true;
        captureButton.disabled = true;
        openButton.hidden = false;
        message.textContent = "Click Open Camera to take another photo.";
    });

    uploadInput.addEventListener("change", () => {
        if (uploadInput.files.length > 0) {
            cameraInput.value = "";
            clearPreviewUrlOnly();
            preview.removeAttribute("src");
            preview.hidden = true;
            retakeButton.hidden = true;
            message.textContent = "ID file selected.";
        }
    });

    form.addEventListener("submit", event => {
        const uploadedFile = uploadInput.files[0];
        const capturedFile = cameraInput.files[0];
        const selectedFile = capturedFile || uploadedFile;

        if (!selectedFile) {
            event.preventDefault();
            message.textContent =
                "Please upload an ID image or capture one with the camera.";
            return;
        }

        const allowedTypes = ["image/jpeg", "image/png"];
        const maxSize = 5 * 1024 * 1024;

        if (!allowedTypes.includes(selectedFile.type)) {
            event.preventDefault();
            message.textContent = "JPG or PNG images only.";
            return;
        }

        if (selectedFile.size > maxSize) {
            event.preventDefault();
            message.textContent = "The ID image must not exceed 5 MB.";
        }
    });

    window.addEventListener("pagehide", stopCamera);

    console.log("CAMERA.JS IS LOADED");