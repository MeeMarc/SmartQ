# SmartQ — Site Flowchart

This file contains a Mermaid flowchart that represents the main pages, authentication flow, admin features, and dynamic queue flow for the SmartQ site.

<!-- Render this block with a Mermaid renderer (VS Code extension or mermaid.live) -->
```mermaid
flowchart TD
  Start([User hits site /]) --> RootRedirect[/redirect to /admin/]
  RootRedirect --> AdminPage["/admin\n(Admin/admin.html)"]

  AdminPage --> Signup["/signup\n(Admin/SignUp.html)"]
  AdminPage --> Login["/login\n(Admin/login.html)"]
  Login -->|success| Homepage["/homepage\n(Admin2/Homepage.html)"]
  Login -->|fail| Signup

  Homepage --> CreateQ["/createq\n(Admin2/CreateQ.html)"]
  Homepage --> AddCandidate["/addcandidate\n(Admin2/AddCandidate.html)"]
  Homepage --> ScanTracking["/scantracking\n(Admin2/Scantracking.html)"]
  Homepage --> AdminSettings["/admin_settings\n(Admin2/AdminSettings.html)"]
  AdminSettings --> Logout["/logout"]

  CreateQ -->|POST /generate_qr_db| QRCreated["QR saved (qr_history / temp_qr)"]
  QRCreated --> QRImage["QR image (base64) returned to UI"]
  CreateQ --> QRHistory["/qr_history_data\n(list of historical QRs)"]
  CreateQ --> TempQR["/temp_qr_data\n(active QRs)"]

  %% User-facing area
  subgraph User_Area [User-facing pages]
    UserPage["/user\n(User/User.html)"]
    QueuePage["/queue/:slug/:number\n(User/User.html)"]
    QueueSubmit[[POST form -> create queue entry]]
    WaitingPage["/queue/:slug/:num/waiting/:entry_id\n(User/Waiting.html)"]
    Download["/download_ticket/:slug/:num/:entry_id"]

    QueuePage -->|POST form| QueueSubmit
    QueueSubmit --> WaitingPage
    WaitingPage --> Download
  end

  %% Admin tools interacting with user queues
  Homepage -->|manage| QRCreated
  Homepage -->|view scans| QRScans["/get_qr_scans/:qr_id"]
  QRScans --> UpdateStatus["/update_queue_status (POST)"]

  %% Misc utilities
  AdminPage --> GenerateSiteQR["/generate_site_qr"]
  AdminPage --> GenerateQR["/generate_qr (quick)\n/ generate_qr_db (save)"]

  %% Entry links
  AdminPage --> UserPage["link: /user or direct queue links"]

  classDef admin fill:#f9f,stroke:#333,stroke-width:1px;
  class AdminPage,Homepage,CreateQ,AddCandidate,ScanTracking,AdminSettings admin;

``` 

## How to view this diagram

- Option A (quick): Open this file in VS Code and install "Markdown Preview Mermaid Support" or any Mermaid extension, then open Markdown preview (Ctrl+Shift+V).
- Option B (web): Copy the mermaid code block and paste into https://mermaid.live to render and export PNG/SVG.
- Option C (CLI): Install mermaid-cli (npm i -g @mermaid-js/mermaid-cli) and run:

```powershell
mmdc -i docs\flowchart.md -o docs\flowchart.svg
```

(If your `docs\flowchart.md` contains extra markdown, extract only the ```mermaid block for `mmdc`.)

## Notes & next steps

- I included the major routes and where they render templates found in `templates/`.
- Queue numbering for `/queue/:slug/:number` is based on normalized slug matching, so names that only differ by case (like `Test` and `test`) get different queue numbers.
- If you'd like a different layout or a more detailed flow (e.g., database interactions, form fields, or modal flows), tell me which area to expand.
- I can also export an SVG/PNG for you and add it to `docs/flowchart.svg`.
