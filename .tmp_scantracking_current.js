
const qrListContainer = document.getElementById("qrListContainer");
const qrDetailContainer = document.getElementById("qrDetailContainer");
const modal = document.getElementById("candidateModal");
const candidateForm = document.getElementById("candidateForm");
const modalQRLink = document.getElementById("modalQRLink");
const documentsModal = document.getElementById("documentsModal");
const notificationModal = document.getElementById("notificationModal");
const notificationForm = document.getElementById("notificationForm");

let currentScans = [];
let currentQRId = null;

// EmailJS configuration.
// Update these values and variable keys to match your EmailJS templates.
const EMAILJS_CONFIG = {
  PUBLIC_KEY: "jpZBXk-dH8pr1YLy4",
  SERVICE_ID: "service_t9g8qmw",
  TEMPLATE_STATUS_ID: "template_hnn5wpo",
  TEMPLATE_DOCUMENT_ID: "template_smlzhta"
};

const EMAILJS_VARS = {
  STATUS: {
    EMAIL: "email",
    USER_NAME: "user_name",
    CREATED_AT: "created_at",
    APPLICATION_STATUS: "application_status",
    TICKET_STATUS: "ticket_status",
    ADMIN_STATUS: "admin_status",
    STATUS_MESSAGE: "status_message",
    STATUS_BG: "status_bg",
    STATUS_COLOR: "status_color",
    APP_NAME: "app_name"
  },
  DOCUMENT: {
    EMAIL: "email",
    APPLICANT_ID: "applicant_id",
    USER_NAME: "user_name",
    USER_MESSAGE: "user_message",
    QUEUE_TYPE: "queue_type",
    DOWNLOAD_LINK: "download_link"
  }
};

function extractFirstName(fullName) {
  const raw = (fullName || "").trim();
  if (!raw) return "Applicant";

  if (raw.includes(",")) {
    const parts = raw.split(",", 2);
    const given = (parts[1] || "").trim();
    if (given) {
      return given.split(/\s+/)[0];
    }
  }

  return raw.split(/\s+/)[0];
}

function buildStatusEmailParams(payload, applicationStatus, statusMessage, palette = {}) {
  const resolvedName = extractFirstName(payload.user_name || payload.fullname || payload.name || "");
  const resolvedDate = payload.created_at || new Date().toLocaleString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
  const resolvedStatus = applicationStatus || payload.application_status || payload.ticket_status || payload.status || "Waiting";
  const resolvedAdminStatus = payload.admin_status || "";
  const resolvedEmail = payload.email || "";

  return {
    [EMAILJS_VARS.STATUS.EMAIL]: resolvedEmail,
    [EMAILJS_VARS.STATUS.USER_NAME]: resolvedName,
    [EMAILJS_VARS.STATUS.APPLICATION_STATUS]: resolvedStatus,
    [EMAILJS_VARS.STATUS.TICKET_STATUS]: resolvedStatus,
    [EMAILJS_VARS.STATUS.ADMIN_STATUS]: resolvedAdminStatus,
    [EMAILJS_VARS.STATUS.STATUS_MESSAGE]: statusMessage || "",
    [EMAILJS_VARS.STATUS.CREATED_AT]: resolvedDate,
    [EMAILJS_VARS.STATUS.STATUS_BG]: palette.bg || "#e7f3ff",
    [EMAILJS_VARS.STATUS.STATUS_COLOR]: palette.color || "#0b5ed7",
    [EMAILJS_VARS.STATUS.APP_NAME]: "SmartQ",
    // Alias variables so templates still work if names differ.
    email: resolvedEmail,
    name: resolvedName,
    fullname: resolvedName,
    date: resolvedDate,
    submitted_at: resolvedDate,
    ticket_status: resolvedStatus,
    admin_status: resolvedAdminStatus
  };
}

function sendEmailJs(templateId, params) {
  if (typeof emailjs === "undefined") {
    return Promise.reject(new Error("EmailJS library is not loaded."));
  }
  return emailjs.send(EMAILJS_CONFIG.SERVICE_ID, templateId, params);
}

// Custom Confirmation Dialog
function showConfirmation(title, message, onConfirm) {
  const modal = document.getElementById('confirmationModal');
  const titleEl = document.getElementById('confirmationTitle');
  const messageEl = document.getElementById('confirmationMessage');
  const yesBtn = document.getElementById('confirmYes');
  const noBtn = document.getElementById('confirmNo');
  
  titleEl.textContent = title;
  messageEl.textContent = message;
  modal.style.display = 'flex';
  
  // Remove existing listeners
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

// Custom Alert Dialog
function showAlert(message, type = 'success') {
  const modal = document.getElementById('alertModal');
  const messageEl = document.getElementById('alertMessage');
  const iconEl = document.getElementById('alertIcon');
  const okBtn = document.getElementById('alertOk');
  
  messageEl.textContent = message;
  
  // Set icon based on type
  if (type === 'success') {
    iconEl.textContent = '✓';
    iconEl.style.background = 'linear-gradient(135deg, #28a745, #20c997)';
  } else {
    iconEl.textContent = '✕';
    iconEl.style.background = 'linear-gradient(135deg, #dc3545, #c82333)';
  }
  
  modal.style.display = 'flex';
  
  okBtn.onclick = () => {
    modal.style.display = 'none';
  };
}

// Mark entry as done
function markAsDone(entryId, buttonElement) {
  showConfirmation(
    'Mark as Complete',
    'Are you sure you want to mark this user as served/completed?',
    () => {
      fetch('/update_queue_status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entry_id: entryId,
          status: 'completed'
        })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          showAlert('User marked as completed!', 'success');
          // Refresh the scan list
          if (currentQRId) {
            viewScans(currentQRId);
          }
        } else {
          showAlert('Error: ' + data.message, 'error');
        }
      })
      .catch(err => {
        console.error('Error marking as done:', err);
        showAlert('Failed to update status', 'error');
      });
    }
  );
}


function acceptEntry(entryId) {
  const message = prompt(
    'Enter notification message (optional):',
    'Your application has been accepted.'
  );
  if (message === null) return;

  showConfirmation(
    'Accept Entry',
    'Are you sure you want to accept this entry?',
    () => {
      fetch(`/accept_queue_entry/${entryId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notification_message: message })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          const emailParams = buildStatusEmailParams(
            data,
            data.application_status || "Waiting",
            message,
            { bg: "#e8f7ee", color: "#198754" }
          );

          sendEmailJs(EMAILJS_CONFIG.TEMPLATE_STATUS_ID, emailParams)
            .then(response => {
              console.log("Status email sent", response);
            })
            .catch(error => {
              console.error("Status email failed", error);
              alert("Status updated, but email sending failed. Check console.");
            });
          showAlert('Entry accepted successfully!', 'success');
          if (currentQRId) viewScans(currentQRId);

        } else {
          showAlert('Error: ' + data.message, 'error');
        }
      })
      .catch(err => {
        console.error(err);
        showAlert('Failed to accept entry', 'error');
      });
    }
  );
}

function rejectEntry(entryId) {
  const message = prompt(
    'Enter notification message (optional):',
    'Your application has been rejected.'
  );
  if (message === null) return;

  showConfirmation(
    'Reject Entry',
    'Are you sure you want to reject this entry?',
    () => {
      fetch(`/reject_queue_entry/${entryId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notification_message: message })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          const emailParams = buildStatusEmailParams(
            data,
            data.application_status || "Waiting",
            message,
            { bg: "#fdecea", color: "#dc3545" }
          );

          sendEmailJs(EMAILJS_CONFIG.TEMPLATE_STATUS_ID, emailParams)
            .then(response => {
              console.log("Status email sent", response);
            })
            .catch(error => {
              console.error("Status email failed", error);
              alert("Status updated, but email sending failed. Check console.");
            });
          showAlert('Entry rejected successfully!', 'success');
          if (currentQRId) viewScans(currentQRId);

        } else {
          showAlert('Error: ' + data.message, 'error');
        }
      })
      .catch(err => {
        console.error(err);
        showAlert('Failed to reject entry', 'error');
      });
    }
  );
}




// Fetch QR List - shows only ACTIVE queues (not deleted ones)
function fetchQRList() {
  // First get active queues from temp_qr
  fetch("/temp_qr_data")
    .then(res => res.json())
    .then(activeQRs => {
      qrListContainer.innerHTML = "<h3>Active Queues</h3>";
      
      if (activeQRs.length === 0) {
        qrListContainer.innerHTML += "<p>No active queues found. Create one in Create Queue page.</p>";
        return;
      }
      
      // Only show active queues (those in temp_qr)
      activeQRs.forEach(qr => {
        const box = document.createElement("div");
        box.className = "qr-box";
            
        // Format date from database (YYYY-MM-DD HH:MM:SS) to readable format
        let formattedDate = 'N/A';
        if (qr.created_at && qr.created_at !== 'N/A') {
          try {
            const date = new Date(qr.created_at);
            formattedDate = date.toLocaleDateString('en-US', { 
              year: 'numeric', 
              month: 'long', 
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            });
          } catch (e) {
            formattedDate = qr.created_at; // Fallback to original if parsing fails
          }
        }
        
        box.innerHTML = `
          <h4>${qr.queue_type}</h4>
          <p>${qr.queue_purpose}</p>
          <p><strong>Service Channel:</strong> ${qr.processing_method || 'Online'}</p>
          <p><strong>Release Format:</strong> ${qr.release_type || 'Digital Copy'}</p>
          <p><strong>Created:</strong> ${formattedDate}</p>
          <div id="qr${qr.id}"></div>
          <p><small><a href="${qr.queue_link}" target="_blank" style="color: #0066cc; text-decoration: underline;">${qr.queue_link}</a></small></p>
          <button onclick="openModal('${qr.queue_link}')">Add Candidate</button>
          <button onclick="viewScans(${qr.id})">View Scans</button>
        `;
        qrListContainer.appendChild(box);

        new QRCode(document.getElementById(`qr${qr.id}`), {
          text: qr.queue_link,
          width: 100,
          height: 100
        });
      });
    })
    .catch(err => {
      console.error("Error fetching active QR list:", err);
      qrListContainer.innerHTML = "<h3>Active Queues</h3><p>Error loading active queues.</p>";
    });
}

// Auto-refresh QR list every 60 seconds to show newly created queues
fetchQRList();
setInterval(fetchQRList, 60000);

// Modal functions
function openModal(link) {
  modal.style.display = "flex";
  modalQRLink.value = link;
}
function closeModal() {
  modal.style.display = "none";
  candidateForm.reset();
}

function openDocumentsModal(entryId) {
  documentsModal.style.display = "flex";
  document.getElementById("documentsContent").innerHTML = "<p>Loading documents...</p>";
  
  // Fetch document URLs
  fetch(`/view_entry_documents/${entryId}`)
    .then(res => res.json())
    .then(data => {
      if (data.status === 'error') {
        document.getElementById("documentsContent").innerHTML = `<p style="color: red;">Error: ${data.message}</p>`;
        return;
      }
      
      const documents = data.documents || {};
      const fullname = data.fullname || "Unknown";
      const applicantId = data.applicant_id || "N/A";
      
      // Update modal title
      document.getElementById("documentsModalTitle").textContent = `Documents - ${fullname}`;
      
      let content = `
        <div style="margin-bottom: 20px; padding: 15px; background: #f8faff; border-radius: 8px;">
          <p style="margin: 5px 0;"><strong>Name:</strong> ${fullname}</p>
          <p style="margin: 5px 0;"><strong>Applicant ID:</strong> ${applicantId}</p>
        </div>
      `;
      
      if (documents.id_doc) {
        const isPdf = documents.id_doc.toLowerCase().endsWith('.pdf');
        content += `
          <div style="margin-bottom: 25px; padding: 15px; background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;">
            <h4 style="color: #003366; margin-bottom: 15px; font-size: 1.1rem;">📄 ID Document</h4>
            ${isPdf ? 
              `<iframe src="${documents.id_doc}" style="width: 100%; height: 500px; border: 1px solid #ccc; border-radius: 8px; margin-bottom: 10px;"></iframe>
               <a href="${documents.id_doc}" target="_blank" style="display: inline-block; padding: 8px 15px; background: #003366; color: white; text-decoration: none; border-radius: 6px; font-size: 0.9rem;">📥 Open PDF in new tab</a>` :
              `<div style="text-align: center;">
                <img src="${documents.id_doc}" alt="ID Document" style="max-width: 100%; max-height: 500px; border: 1px solid #ccc; border-radius: 8px; cursor: pointer; margin-bottom: 10px;" onclick="window.open('${documents.id_doc}', '_blank')">
                <p style="color: #666; font-size: 0.85rem; margin-top: 5px;">Click image to view full size</p>
              </div>`
            }
          </div>
        `;
      }
      
      if (documents.req_doc) {
        const isPdf = documents.req_doc.toLowerCase().endsWith('.pdf');
        content += `
          <div style="margin-bottom: 25px; padding: 15px; background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;">
            <h4 style="color: #003366; margin-bottom: 15px; font-size: 1.1rem;">📋 Required Document</h4>
            ${isPdf ? 
              `<iframe src="${documents.req_doc}" style="width: 100%; height: 500px; border: 1px solid #ccc; border-radius: 8px; margin-bottom: 10px;"></iframe>
               <a href="${documents.req_doc}" target="_blank" style="display: inline-block; padding: 8px 15px; background: #003366; color: white; text-decoration: none; border-radius: 6px; font-size: 0.9rem;">📥 Open PDF in new tab</a>` :
              `<div style="text-align: center;">
                <img src="${documents.req_doc}" alt="Required Document" style="max-width: 100%; max-height: 500px; border: 1px solid #ccc; border-radius: 8px; cursor: pointer; margin-bottom: 10px;" onclick="window.open('${documents.req_doc}', '_blank')">
                <p style="color: #666; font-size: 0.85rem; margin-top: 5px;">Click image to view full size</p>
              </div>`
            }
          </div>
        `;
      }
      
      if (documents.signature) {
        content += `
          <div style="margin-bottom: 25px; padding: 15px; background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;">
            <h4 style="color: #003366; margin-bottom: 15px; font-size: 1.1rem;">✍️ Signature</h4>
            <div style="text-align: center;">
              <img src="${documents.signature}" alt="Signature" style="max-width: 100%; max-height: 300px; border: 1px solid #ccc; border-radius: 8px; cursor: pointer; margin-bottom: 10px;" onclick="window.open('${documents.signature}', '_blank')">
              <p style="color: #666; font-size: 0.85rem; margin-top: 5px;">Click image to view full size</p>
            </div>
          </div>
        `;
      }
      
      if (!documents.id_doc && !documents.req_doc && !documents.signature) {
        content = '<p style="color: #666;">No documents uploaded for this entry.</p>';
      }
      
      document.getElementById("documentsContent").innerHTML = content;
    })
    .catch(err => {
      console.error('Error loading documents:', err);
      document.getElementById("documentsContent").innerHTML = '<p style="color: red;">Failed to load documents. Please try again.</p>';
    });
}

function closeDocumentsModal() {
  documentsModal.style.display = "none";
}

// Close documents modal when clicking outside
documentsModal.addEventListener('click', function(e) {
  if (e.target === documentsModal) {
    closeDocumentsModal();
  }
});

// Notification Modal Functions
function openNotificationModal(qrId) {
  notificationModal.style.display = "flex";
  document.getElementById("notificationQRId").value = qrId;
  document.getElementById("notificationMessage").value = "";
  populateEntryCheckboxes();
}

function closeNotificationModal() {
  notificationModal.style.display = "none";
  notificationForm.reset();
}



function populateEntryCheckboxes() {
  const container = document.getElementById("entryCheckboxes");
  container.innerHTML = "";
  
  if (currentScans.length === 0) {
    container.innerHTML = "<p style='color: #666;'>No entries available.</p>";
    return;
  }
  
  currentScans.forEach(scan => {
    const div = document.createElement("div");
    div.style.marginBottom = "8px";
    div.innerHTML = `
      <label style="display: flex; align-items: center; cursor: pointer;">
        <input type="checkbox" value="${scan.id}" style="margin-right: 8px;">
        <span>${scan.fullname} (${scan.phone || 'N/A'})</span>
      </label>
    `;
    container.appendChild(div);
  });
}

// Handle notification form submission (only selected entries; no "notify all")
notificationForm.addEventListener("submit", function(e) {
  e.preventDefault();
  
  const qrId = document.getElementById("notificationQRId").value;
  const message = document.getElementById("notificationMessage").value.trim();

  
  if (!message) {
    showAlert("Please enter a notification message.", "error");
    return;
  }
  
  const checkboxes = document.querySelectorAll("#entryCheckboxes input[type='checkbox']:checked");
  const entryIds = Array.from(checkboxes).map(cb => parseInt(cb.value));
  
  if (entryIds.length === 0) {
    showAlert("Please select at least one entry to notify.", "error");
    return;
  }
  
  fetch("/send_notification", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      qr_id: parseInt(qrId),
      entry_ids: entryIds,
      message: message
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === "success") {
      showAlert(data.message, "success");
      closeNotificationModal();
      // Refresh scans to show updated notification status
      if (currentQRId) {
        viewScans(currentQRId);
      }
    } else {
      showAlert("Error: " + data.message, "error");
    }
  })
  .catch(err => {
    console.error(err);
    showAlert("Failed to send notification. Please try again.", "error");
  });
});

// Close notification modal when clicking outside
notificationModal.addEventListener('click', function(e) {
  if (e.target === notificationModal) {
    closeNotificationModal();
  }
});

// Handle Add Candidate submission
candidateForm.addEventListener("submit", function(e) {
  e.preventDefault();
  
  // Get individual name fields
  const lastname = document.getElementById("lastname").value.trim();
  const firstname = document.getElementById("firstname").value.trim();
  const middleinitial = document.getElementById("middleinitial").value.trim();
  const suffix = document.getElementById("suffix").value.trim();
  const phone = document.getElementById("phone").value.trim();
  const email = document.getElementById("candidateEmail").value.trim();
  
  // Validate required fields
  if (!lastname || !firstname || !phone || !email) {
    showAlert("Please provide Last Name, First Name, Phone Number, and Email.", "error");
    return;
  }

  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailPattern.test(email)) {
    showAlert("Please enter a valid email address.", "error");
    return;
  }
  
  // Construct fullname from separate fields (same format as registration form)
  // Format: "Lastname, Firstname M.I. Suffix"
  const name_parts = [lastname, firstname];
  if (middleinitial) {
    name_parts.push(middleinitial);
  }
  if (suffix) {
    name_parts.push(suffix);
  }
  
  let fullname = name_parts.slice(0, 2).join(', '); // "Lastname, Firstname"
  if (name_parts.length > 2) {
    fullname += ' ' + name_parts.slice(2).join(' '); // Add middle initial and suffix
  }
  
  const data = {
    fullname: fullname,
    phone: phone,
    email: email,
    link: modalQRLink.value
  };

  fetch("/add_candidate_modal", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  })
  .then(res => res.json())
  .then(resp => {
    if(resp.status === "success") {
      showAlert("Candidate added successfully!", "success");
      closeModal();
      // Refresh scans if currently viewing the QR
      if (currentQRId) {
        viewScans(currentQRId);
      }
    } else {
      showAlert("Error: " + resp.message, "error");
    }
  })
  .catch(err => {
    console.error(err);
    showAlert("Failed to add candidate. Please try again.", "error");
  });
});

// View scans for a specific QR — focus right panel on the scan list (mga nag-scan)
function viewScans(qrId) {
  const normalizedQrId = Number(qrId);
  if (!Number.isInteger(normalizedQrId) || normalizedQrId <= 0) {
    showAlert("Invalid QR ID. Please refresh and try again.", "error");
    return;
  }

  currentQRId = normalizedQrId;
  fetch(`/get_qr_scans/${normalizedQrId}`)
    .then(res => {
      if (!res.ok) {
        throw new Error(`Request failed (${res.status})`);
      }
      return res.json();
    })
    .then(data => {
      const scans = Array.isArray(data) ? data : [];
      currentScans = scans;
      const queueModeLabel = scans.length
        ? `${scans[0].queue_processing_method || 'Online'} / ${scans[0].queue_release_type || 'Digital Copy'}`
        : '';
      qrDetailContainer.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px;">
          <h3 style="margin: 0;">Scans for QR #${normalizedQrId}${queueModeLabel ? ` <span style="font-size: 0.9rem; color: #666; font-weight: 500;">(${queueModeLabel})</span>` : ''}</h3>
          <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <button onclick="openNotificationModal(${normalizedQrId})" style="background: #17a2b8; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600;">Send Notification</button>
            <button onclick="downloadScans(${normalizedQrId})" style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600;">Download Scans</button>
          </div>
        </div>
        <input type="text" id="scanSearch" placeholder="Search by name, phone, purpose, status, or admin status">
        <div class="scan-list" id="scanList"></div>
      `;

      const scanSearch = document.getElementById("scanSearch");
      if (scanSearch) {
        scanSearch.addEventListener("input", filterScans);
      }
      renderScans(currentScans);
      
            // Focus the right panel (scan list) so view is on "mga nag-scan"
      qrDetailContainer.scrollIntoView({ behavior: "smooth", block: "start" });
      if (qrDetailContainer.querySelector("#scanList")) {
        qrDetailContainer.querySelector("#scanList").focus({ preventScroll: true });
      }
    })
    .catch(err => {
      console.error("Error loading scans:", err);
      currentScans = [];
      qrDetailContainer.innerHTML = `
        <h3>Scans for QR #${normalizedQrId}</h3>
        <p style="color: #b00020; margin-top: 10px;">Unable to load scans right now. Please try again.</p>
      `;
      showAlert("Failed to load scans. Please try again.", "error");
    });
}

function downloadScans(qrId) {
  const normalizedQrId = Number(qrId);
  if (!Number.isInteger(normalizedQrId) || normalizedQrId <= 0) {
    showAlert("Invalid QR ID for download.", "error");
    return;
  }
  window.location.href = `/download_scans/${normalizedQrId}`;
}

// Render scans
function renderScans(scans) {
  const scanList = document.getElementById("scanList");
  if (!scanList) return;

  if (!Array.isArray(scans)) {
    scanList.innerHTML = "<p>No scans found.</p>";
    return;
  }

  scanList.innerHTML = "";

  if (scans.length === 0) {
    scanList.innerHTML = "<p>No scans found.</p>";
    return;
  }

  scans.forEach(user => {
    const card = document.createElement("div");
    card.className = "scan-card";

    const phone = user.phone ? ` • ${user.phone}` : "";
    const purpose = user.purpose ? ` • ${user.purpose}` : "";
    const scannedAt = user.scanned_at ? ` • ${user.scanned_at}` : "";
    const status = user.status ? user.status.charAt(0).toUpperCase() + user.status.slice(1) : "Waiting";
    const statusClass = user.status === 'completed' ? 'status-completed' :
                        user.status === 'cancelled' ? 'status-cancelled' :
                        user.status === 'rescheduled' ? 'status-rescheduled' : 'status-waiting';

    const adminStatus = user.admin_status || 'pending';
    const adminStatusText = adminStatus.charAt(0).toUpperCase() + adminStatus.slice(1);
    const adminStatusClass = adminStatus === 'accepted' ? 'status-accepted' :
                             adminStatus === 'rejected' ? 'status-rejected' : 'status-pending';

    const showAdminActions = adminStatus === 'pending' && !['completed','cancelled','rescheduled'].includes(user.status);
    const hasDocuments = user.has_documents || (user.id_doc_url || user.req_doc_url || user.signature_url);
    const hasNotification = user.notification_message && user.notification_message.trim() !== '';
    const canMarkDone = adminStatus !== 'pending' && !['completed','cancelled','rescheduled'].includes(user.status);
    const releaseType = (user.queue_release_type || '').toLowerCase();
    const canSendDocument = releaseType ? releaseType.includes('digital') : true;

    card.innerHTML = `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; gap: 15px;">
          <div style="flex: 1;">
            <strong>${user.fullname}</strong>${phone}${purpose}${scannedAt}
          </div>
          <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
            <span class="status-badge ${statusClass}">${status}</span>
            <span class="status-badge ${adminStatusClass}">${adminStatusText}</span>
            ${hasDocuments ? `<button class="view-docs-btn" onclick="openDocumentsModal(${user.id})">View Docs</button>` : ''}
            ${showAdminActions ? `
<button class="accept-btn" onclick="acceptEntry(${user.id})">
  Accept
</button>

<button class="reject-btn" onclick="rejectEntry(${user.id})">
  Reject
</button>

            ` : ''}
            ${canMarkDone ? `<button class="done-btn" onclick="markAsDone(${user.id}, this)">Done</button>` : ''}

            <!-- Send Document button -->
            ${canSendDocument ? `
            <button class="send-doc-btn"
                    data-applicant-id="${user.applicant_id || ''}"
                    data-fullname="${user.fullname || ''}"
                    data-queue-type="${user.queue_type || 'Document'}"
                    data-email="${user.email || ''}">
              Send Document
            </button>
            ` : ''}
          </div>
        </div>

        ${hasNotification ? `
          <div style="margin-top: 10px; padding: 10px; background: #e7f3ff; border-left: 3px solid #007bff; border-radius: 4px;">
            <strong style="color: #003366;">📢 Notification:</strong>
            <p style="margin: 5px 0 0 0; color: #004085;">${user.notification_message}</p>
          </div>
        ` : ''}
      </div>
    `;

    scanList.appendChild(card);

// Attach Send Document listener immediately
const sendBtn = card.querySelector(".send-doc-btn");
if (sendBtn) {
  sendBtn.addEventListener("click", function() {
    openSendDocumentModal(
      this.dataset.applicantId,
      this.dataset.fullname,
      this.dataset.queueType || "Document",
      this.dataset.email || ""
    );
  });
}

  });
}

// Filter scans by search
function filterScans() {
  const query = document.getElementById("scanSearch").value.toLowerCase();
  const filtered = currentScans.filter(user =>
    (user.fullname && user.fullname.toLowerCase().includes(query)) ||
    (user.phone && user.phone.toLowerCase().includes(query)) ||
    (user.purpose && user.purpose.toLowerCase().includes(query)) ||
    (user.status && user.status.toLowerCase().includes(query)) ||
    (user.admin_status && user.admin_status.toLowerCase().includes(query))
  );

  // ✅ Render filtered scans (listeners attached automatically inside renderScans)
  renderScans(filtered);
}



  // Initialize EmailJS
  (function() {
    emailjs.init(EMAILJS_CONFIG.PUBLIC_KEY);
  })();

// Open modal and set template variables
function openSendDocumentModal(applicantId, userName, documenttype, email) {
  const modal = document.getElementById("sendDocumentModal");

  document.getElementById("sendDocApplicantId").value = applicantId;
  document.getElementById("sendDocUserName").value = userName;
  document.getElementById("sendDocDocumenttype").value = documenttype || "Document"; // fallback
  document.getElementById("sendDocEmail").value = email || "";

  document.getElementById("sendDocFile").value = "";
  document.getElementById("sendDocMessage").value = "";

  modal.style.display = "flex";
}


// Close modal
function closeSendDocumentModal() {
  document.getElementById("sendDocumentModal").style.display = "none";
}

// Send document
async function sendDocumentModal(e) {
  e.preventDefault();

  const applicantId = document.getElementById("sendDocApplicantId").value;
  const userName = document.getElementById("sendDocUserName").value;
  const documenttype = document.getElementById("sendDocDocumenttype").value;
  const email = document.getElementById("sendDocEmail").value;
  const message = document.getElementById("sendDocMessage").value;
  const fileInput = document.getElementById("sendDocFile");

  if (!fileInput.files.length) {
    alert("Please attach a document.");
    return;
  }

  try {
    // Upload file
    const formData = new FormData();
    formData.append("applicant_id", applicantId); // ✅ backend expects applicant_id
    formData.append("document", fileInput.files[0]);

    const uploadResponse = await fetch("/upload_document", {
      method: "POST",
      body: formData
    });

    if (!uploadResponse.ok) throw new Error("Upload failed");

    const data = await uploadResponse.json();

    // EmailJS payload
    const resolvedName = extractFirstName(userName);
    const resolvedDate = new Date().toLocaleString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });

    const emailParams = {
      [EMAILJS_VARS.DOCUMENT.EMAIL]: email,
      [EMAILJS_VARS.DOCUMENT.APPLICANT_ID]: applicantId,
      [EMAILJS_VARS.DOCUMENT.USER_NAME]: resolvedName,
      [EMAILJS_VARS.DOCUMENT.USER_MESSAGE]: message,
      [EMAILJS_VARS.DOCUMENT.QUEUE_TYPE]: documenttype,
      [EMAILJS_VARS.DOCUMENT.DOWNLOAD_LINK]: data.download_url,
      // Alias variables for template flexibility.
      name: resolvedName,
      fullname: resolvedName,
      created_at: resolvedDate,
      date: resolvedDate,
      document_name: documenttype
    };

    await sendEmailJs(EMAILJS_CONFIG.TEMPLATE_DOCUMENT_ID, emailParams);

    alert("Document sent successfully!");
    closeSendDocumentModal();
    document.getElementById("sendDocumentForm").reset();

  } catch (err) {
    console.error(err);
    alert("Failed to send document.");
  }
}


