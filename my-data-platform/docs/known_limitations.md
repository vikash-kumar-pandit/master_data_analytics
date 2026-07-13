# DataSaaS Pro Platform Known Limitations (v1.0.0-rc3)

This document outlines the design boundaries, performance limits, and dependency behaviors of the DataSaaS Pro platform release.

---

## ⚡ Performance & Dataset Limits

### 1. In-Memory Container Limits
* **Limit**: The Celery worker has a memory ceiling of **4 GB** in the production Docker compose setup.
* **Impact**: Training AutoML models on datasets larger than **300 MB** (approx. 3 million rows with many columns) may result in Out-Of-Memory (OOM) worker restarts.
* **Mitigation**: Users are advised to downsample datasets or reduce features before triggering complex AutoML models. For datasets > 500MB, Polars automatically utilizes lazy query streaming (`collect(streaming=True)`).

### 2. File Upload Ceiling
* **Limit**: Nginx configuration defines `client_max_body_size 100M`.
* **Impact**: Trying to upload single datasets larger than 100MB directly via the HTTP gateway will fail with code `413 Payload Too Large`.
* **Mitigation**: Expand limit in `nginx/nginx.conf` if required, or upload via chunked REST APIs.

---

## ⚙️ Dependencies & Package Limitations

### 1. PyCaret Compatibility (Python 3.12)
* **Limit**: PyCaret requires strict legacy libraries (e.g. `numpy < 1.24`) which are incompatible with modern Python 3.12 runtimes.
* **Solution**: The backend automatically bypasses PyCaret when run on Python 3.12 and calls our custom Scikit-Learn-based Random Forest classification/regression engines. This maintains identical API compatibility with high training stability.

### 2. WeasyPrint GTK+ Dependencies (Windows local dev only)
* **Limit**: Running the backend locally on Windows outside of Docker requires manual installation of the GTK3 runtime environment and registry bin updates.
* **Impact**: If GTK3 is missing, PDF generation will raise an `OSError: cannot load library 'gobject-2.0-0'`.
* **Mitigation**: This is completely bypassed in Docker. The container image automatically compiles all Pango, Cairo, and Fontconfig system packages natively.

---

## 📧 Mail Delivery & Simulated Mode

* **Limit**: By default, SMTP settings (`SMTP_HOST`) are empty in the template configurations.
* **Behavior**: If no SMTP server is configured, the platform falls back to **simulated email delivery**.
* **Verification**: Account registration confirmation templates and password resets are printed directly to the FastAPI API stdout logs rather than sent, allowing developers to copy links and test the application flow instantly without setup.
