
    const form = document.getElementById("qrForm");
    const container = document.getElementById("qrContainer");
    const qrContainerTitle = document.getElementById("qrContainerTitle");
    const viewHistoryBtn = document.getElementById("viewHistoryBtn");
    const loadPreviousBtn = document.getElementById("loadPreviousBtn");
    const generateQrBtn = document.getElementById("generateQrBtn");

    const GENERATED_TITLE = "Generated Queues";
    const HISTORY_TITLE = "QR History";
    let qrList = JSON.parse(localStorage.getItem("queues")) || [];
    let qrHistoryList = [];
    let isHistoryView = false;
    let isGenerating = false;
    let generateCooldownUntil = 0;
    let generateCooldownTimer = null;

    function getMissingConfigFields() {
      const configFields = [
        { id: "processingMethod", label: "Service Channel" },
        { id: "releaseType", label: "Release Format" },
        { id: "studentId", label: "Applicant ID Requirement" },
        { id: "validId", label: "Valid ID Upload Requirement" },
        { id: "supportingDoc", label: "Supporting Document Upload Requirement" },
        { id: "esignRequired", label: "E-Signature Requirement" }
      ];

      return configFields
        .filter(field => {
          const element = document.getElementById(field.id);
          return !element || !element.value || element.value.trim() === "";
        })
        .map(field => field.label);
    }

    /* ================= CONFIRMATION MODAL ================= */
    function showConfirmation(title, message, onConfirm) {
      const modal = document.getElementById('confirmationModal');
      const titleEl = document.getElementById('confirmationTitle');
      const messageEl = document.getElementById('confirmationMessage');
      const yesBtn = document.getElementById('confirmYes');
      const noBtn = document.getElementById('confirmNo');

      titleEl.textContent = title;
      messageEl.textContent = message;
      modal.style.display = 'flex';

      const newYesBtn = yesBtn.cloneNode(true);
      const newNoBtn = noBtn.cloneNode(true);
      yesBtn.parentNode.replaceChild(newYesBtn, yesBtn);
      noBtn.parentNode.replaceChild(newNoBtn, noBtn);

      document.getElementById('confirmYes').onclick = () => {
        modal.style.display = 'none';
        onConfirm();
      };

      document.getElementById('confirmNo').onclick = () => {
        modal.style.display = 'none';
      };
    }

    /* ================= ALERT MODAL ================= */
    function showAlert(message, type = 'success') {
      const modal = document.getElementById('alertModal');
      const messageEl = document.getElementById('alertMessage');
      const iconEl = document.getElementById('alertIcon');
      const okBtn = document.getElementById('alertOk');

      messageEl.textContent = message;

      if (type === 'success') {
        iconEl.textContent = 'OK';
        iconEl.style.background = 'linear-gradient(135deg, #28a745, #20c997)';
      } else if (type === 'warning') {
        iconEl.textContent = '!';
        iconEl.style.background = 'linear-gradient(135deg, #ffc107, #ff9800)';
      } else {
        iconEl.textContent = 'X';
        iconEl.style.background = 'linear-gradient(135deg, #dc3545, #c82333)';
      }

      modal.style.display = 'flex';
      okBtn.onclick = () => modal.style.display = 'none';
    }

    function setGenerateButtonState(disabled, label) {
      if (!generateQrBtn) return;
      generateQrBtn.disabled = disabled;
      generateQrBtn.innerText = label;
    }

    function startGenerateCooldown(seconds = 10) {
      generateCooldownUntil = Date.now() + (seconds * 1000);

      if (generateCooldownTimer) {
        clearInterval(generateCooldownTimer);
      }

      const updateCooldownLabel = () => {
        const remainingMs = generateCooldownUntil - Date.now();

        if (remainingMs <= 0) {
          clearInterval(generateCooldownTimer);
          generateCooldownTimer = null;
          setGenerateButtonState(false, "Generate QR");
          return;
        }

        const remainingSeconds = Math.ceil(remainingMs / 1000);
        setGenerateButtonState(true, `Please wait... ${remainingSeconds}s`);
      };

      updateCooldownLabel();
      generateCooldownTimer = setInterval(updateCooldownLabel, 250);
    }

    function escapeHtml(value) {
      return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function formatCreatedAt(value) {
      if (!value || value === "N/A") {
        return "N/A";
      }
      try {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
          return value;
        }
        return date.toLocaleDateString("en-US", {
          year: "numeric",
          month: "long",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
      } catch (_) {
        return value;
      }
    }

    function extractQueueNumberFromLink(link) {
      const match = String(link || "").match(/\/queue\/[^/]+\/(\d+)/);
      return match ? match[1] : "N/A";
    }

    function showGeneratedQueueView() {
      isHistoryView = false;
      qrContainerTitle.textContent = GENERATED_TITLE;
      if (viewHistoryBtn) {
        viewHistoryBtn.textContent = "View QR History";
      }
      if (loadPreviousBtn) {
        loadPreviousBtn.style.display = "none";
      }
      renderQRs();
    }

    function renderQRHistory(historyRows) {
      container.innerHTML = "";

      if (!Array.isArray(historyRows) || historyRows.length === 0) {
        container.innerHTML = "<p style=\"color:#666; text-align:center; width:100%;\">No QR history found.</p>";
        return;
      }

      historyRows.forEach((item, index) => {
        const queueType = item.queue_type || "Unknown";
        const queuePurpose = item.queue_purpose || "N/A";
        const queueLink = (item.queue_link || "").trim() || "#";
        const queueNumber = extractQueueNumberFromLink(queueLink);
        const createdAt = formatCreatedAt(item.created_at);
        const processingMethod = item.processing_method || "Online";
        const releaseType = item.release_type || "Digital Copy";

        const box = document.createElement("div");
        box.className = "qr-box";

        box.innerHTML = `
        <div class="queue-type-slot">
          <h4 class="queue-type-title" title="${escapeHtml(queueType)}">${escapeHtml(queueType)}</h4>
        </div>
        <p class="queue-purpose">${escapeHtml(queuePurpose)}</p>
        <p><strong>Queue #:</strong> ${escapeHtml(queueNumber)}</p>
        <p><strong>Service Channel:</strong> ${escapeHtml(processingMethod)}</p>
        <p><strong>Release Format:</strong> ${escapeHtml(releaseType)}</p>
        <p><strong>Created:</strong> ${escapeHtml(createdAt)}</p>
        <div id="historyQr${index}"></div>
        <div class="qr-url-container">
          <p><small><strong>URL:</strong></small></p>
          <a target="_blank" rel="noopener noreferrer" class="qr-url-link history-link"></a>
        </div>
      `;

        const linkEl = box.querySelector(".history-link");
        linkEl.href = queueLink;
        linkEl.textContent = queueLink;

        container.appendChild(box);

        if (queueLink && queueLink !== "#") {
          new QRCode(document.getElementById(`historyQr${index}`), {
            text: queueLink,
            width: 128,
            height: 128
          });
        }
      });
    }

    async function checkDatabaseConnection() {
      try {
        const res = await fetch("/test_db");
        const data = await res.json();
        if (!res.ok || data.status !== "success") {
          const diagnosticError = String(data.error || `DB diagnostic failed (${res.status}).`);
          const normalized = diagnosticError.toLowerCase();
          const connectionErrorMarkers = [
            "database connection failed",
            "could not connect",
            "connection refused",
            "timeout",
            "server closed the connection",
            "could not translate host name",
            "network is unreachable",
            "name or service not known"
          ];
          const isConnectionError = connectionErrorMarkers.some(marker => normalized.includes(marker));

          if (!isConnectionError) {
            return {
              status: "success",
              message: `Database reachable (schema diagnostic warning: ${diagnosticError})`
            };
          }

          return {
            status: "error",
            message: diagnosticError
          };
        }
        return { status: "success", message: "Database connection successful." };
      } catch (err) {
        return {
          status: "error",
          message: err.message || "Unable to run database diagnostic."
        };
      }
    }

    async function fetchQRHistory() {
      if (viewHistoryBtn) {
        viewHistoryBtn.disabled = true;
      }

      try {
        const response = await fetch("/qr_history_data");
        let payload = null;
        try {
          payload = await response.json();
        } catch (_) {
          payload = null;
        }

        if (!response.ok) {
          const serverError = payload && payload.error ? payload.error : `Request failed (${response.status})`;
          const dbDiagnostic = await checkDatabaseConnection();
          const dbHint = dbDiagnostic.status === "error"
            ? ` Database diagnostic: ${dbDiagnostic.message}`
            : "";
          throw new Error(`${serverError}.${dbHint}`);
        }

        qrHistoryList = Array.isArray(payload) ? payload : [];
        isHistoryView = true;
        qrContainerTitle.textContent = HISTORY_TITLE;
        if (viewHistoryBtn) {
          viewHistoryBtn.textContent = "Back to Generated";
        }
        if (loadPreviousBtn) {
          loadPreviousBtn.style.display = "none";
        }
        renderQRHistory(qrHistoryList);
      } catch (err) {
        console.error("Error loading QR history:", err);
        showAlert(`Failed to load QR history: ${err.message}`, "error");
      } finally {
        if (viewHistoryBtn) {
          viewHistoryBtn.disabled = false;
        }
      }
    }

    /* ================= RENDER QRS ================= */
    function renderQRs() {
      container.innerHTML = "";

      qrList.forEach((item, index) => {
        const box = document.createElement("div");
        box.className = "qr-box";

        box.innerHTML = `
        <div class="queue-type-slot">
          <h4 class="queue-type-title" title="${item.type}">${item.type}</h4>
        </div>
        <p class="queue-purpose">${item.purpose}</p>

        <p><strong>Queue #:</strong> ${item.queueNumber}</p>
        <p><strong>Processing Time:</strong> ${item.processingDays} day(s)</p>
        <p><strong>Service Channel:</strong> ${item.processingMethod || 'N/A'}</p>
        <p><strong>Release Format:</strong> ${item.releaseType || 'N/A'}</p>
        <p><strong>Student/Client ID:</strong> ${item.studentId || 'Yes'}</p>
        <p><strong>Valid ID:</strong> ${item.validId || 'Yes'}</p>
        <p><strong>Supporting Doc:</strong> ${item.supportingDoc || 'Yes'}</p>
        <p><strong>E-Signature Required:</strong> ${item.esignRequired}</p>

        <p><strong>Created:</strong> ${item.created_at}</p>

        <div id="qr${index}"></div>

        <div class="qr-url-container">
          <p><small><strong>URL:</strong></small></p>
          <a href="${item.link}" target="_blank" class="qr-url-link">${item.link}</a>
        </div>

        <div class="qr-actions">
          <button onclick="downloadQR(${index})">Download QR</button>
          <button onclick="deleteQR(${index})">Delete</button>
        </div>
      `;

        container.appendChild(box);

        new QRCode(document.getElementById(`qr${index}`), {
          text: item.link,
          width: 128,
          height: 128
        });
      });
    }

    showGeneratedQueueView();

    if (viewHistoryBtn) {
      viewHistoryBtn.addEventListener("click", async () => {
        if (isHistoryView) {
          showGeneratedQueueView();
          return;
        }
        await fetchQRHistory();
      });
    }

    /* ================= CREATE QUEUE ================= */
  form.addEventListener("submit", (e) => {
      e.preventDefault();

      if (isGenerating) {
        showAlert("Please wait, generating queue...", "warning");
        return;
      }

      if (Date.now() < generateCooldownUntil) {
        const remainingSeconds = Math.ceil((generateCooldownUntil - Date.now()) / 1000);
        showAlert(`Please wait ${remainingSeconds} second(s) before generating another queue.`, "warning");
        return;
      }

      const type = document.getElementById("queueType").value.trim();
      const purpose = document.getElementById("queuePurpose").value.trim();
      const processingDays = document.getElementById("processingDays").value.trim();

      const processingMethod = document.getElementById("processingMethod").value;
      const releaseType = document.getElementById("releaseType").value;
      const esignRequired = document.getElementById("esignRequired").value;
      const studentId = document.getElementById("studentId").value;
      const validId = document.getElementById("validId").value;
      const supportingDoc = document.getElementById("supportingDoc").value;

      const missingConfigFields = getMissingConfigFields();
      if (missingConfigFields.length > 0) {
        showAlert(`Please select values for: ${missingConfigFields.join(", ")}.`, "error");
        return;
      }

      if (!type || !purpose) {
        showAlert("Please fill in Queue Type and Purpose fields.", "error");
        return;
      }

      const formData = new URLSearchParams();
      formData.append('type', type);
      formData.append('purpose', purpose);

      if (processingDays) formData.append('processingDays', processingDays);
      formData.append('processingMethod', processingMethod);
      formData.append('releaseType', releaseType);
      formData.append('studentId', studentId);
      formData.append('validId', validId);
      formData.append('supportingDoc', supportingDoc);
      formData.append('esignRequired', esignRequired);

      isGenerating = true;
      setGenerateButtonState(true, "Please wait, generating queue...");

      fetch("/generate_qr_db", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData.toString()
      })
        .then(res => res.json())
        .then(data => {
          if (data.error) throw new Error(data.error);

          const now = new Date();
          const formattedDate = now.toLocaleDateString('en-US', {
            year: 'numeric', month: 'long', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
          });

          const newQR = {
            type,
            purpose,
            processingDays,
            processingMethod,
            releaseType,
            esignRequired,
            studentId,
            validId,
            supportingDoc,
            link: data.queue_link,
            queueNumber: data.queue_number || 1,
            qrId: data.qr_id,
            created_at: formattedDate
          };

          qrList.push(newQR);
          localStorage.setItem("queues", JSON.stringify(qrList));

          showGeneratedQueueView();
          form.reset();
          showAlert("Queue created successfully!", "success");
          startGenerateCooldown(10);
        })
        .catch(err => {
          console.error(err);
          showAlert(`Error generating QR: ${err.message}`, "error");
          setGenerateButtonState(false, "Generate QR");
        })
        .finally(() => {
          isGenerating = false;
          if (Date.now() >= generateCooldownUntil) {
            setGenerateButtonState(false, "Generate QR");
          }
        });
    });


    /* ================= DELETE QR ================= */
    async function deleteQR(index) {
      const qr = qrList[index];

      showConfirmation(
        "Delete Queue",
        `Are you sure you want to delete "${qr.type}"?`,
        async () => {
          try {
            // Remove from active queue list in the backend (temp_qr / active queues)
            if (qr.qrId) {
              await fetch("/delete_qr", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: qr.qrId })
              });
            }

            // Remove from local storage / UI list
            qrList.splice(index, 1);
            localStorage.setItem("queues", JSON.stringify(qrList));
            showGeneratedQueueView();
            showAlert("Queue removed from active list.", "success");
          } catch (err) {
            console.error(err);
            showAlert("Error deleting queue. Please try again.", "error");
          }
        }
      );
    }

    /* ================= DOWNLOAD QR ================= */
    function downloadQR(index) {
      const canvas = document.querySelector(`#qr${index} canvas`);
      if (!canvas) return;

      const link = document.createElement("a");
      link.href = canvas.toDataURL("image/png");
      link.download = `QR_${qrList[index].type}.png`;
      link.click();
    }
  