# Screenshot Capture Guide for SmartQ User Manual

This guide tells you exactly which screenshots to capture for the user manual.

## 📸 Screenshot Requirements

### General Tips:
- Use **1920x1080** resolution or similar for clarity
- Capture on a clean browser window (close unnecessary tabs)
- Use actual data (not lorem ipsum) for realistic examples
- Consider using tools like:
  - **Windows:** Snipping Tool, Snip & Sketch (Win + Shift + S)
  - **Mac:** Command + Shift + 4
  - **Browser Extensions:** Awesome Screenshot, Lightshot

---

## For Queue Users Section

### 1. QR Code Example
**What to capture:** A sample QR code (can be generated from Create Queue)
**Page:** Admin Create Queue page
**Highlight:** The QR code image itself

### 2. Queue Landing Page
**What to capture:** The main registration page users see after scanning
**URL:** `/queue/[slug]/[number]`
**Example:** `/queue/test/1`
**Show:** 
- Queue name/type at the top
- Queue purpose
- Queue number display
- "How It Works" section with steps

### 3. Registration Form Top Section
**What to capture:** The upper part of the registration form
**Show:**
- Queue information banner
- Document type label
- Form instructions

### 4. Complete Registration Form
**What to capture:** Full form with all fields visible
**Show:**
- Phone Number field
- Last Name field
- First Name field
- Middle Initial field
- Suffix field
- Purpose field
- Submit button

### 5. Success Message
**What to capture:** The moment after successful registration
**Show:** The redirect to waiting page with confirmation

### 6. Queue Ticket - Waiting Status
**What to capture:** Complete ticket view with waiting status
**URL:** `/queue/[slug]/[number]/waiting/[entry_id]`
**Show:**
- "🎉 Ticket Confirmed!" header
- Queue #[number] large display
- Ticket reference number
- Status badge (yellow "Waiting")
- Ticket holder name
- Instructions text
- Download button
- Cancel and Reschedule buttons

### 7. Download Button
**What to capture:** Close-up of the download ticket button
**Highlight:** The "📥 Download Ticket" button

### 8. Cancel Button Location
**What to capture:** The action buttons at bottom of ticket
**Show:** Both "Cancel Registration" and "Reschedule" buttons

### 9. Cancel Confirmation Dialog
**What to capture:** The custom modal that appears when clicking Cancel
**Show:**
- Warning icon (⚠️)
- "Cancel Registration" title
- Confirmation message
- "Yes, Proceed" button (green)
- "Cancel" button (gray)

### 10. Cancelled Ticket
**What to capture:** Ticket page after cancellation
**Show:**
- "❌ Ticket Cancelled" header
- Red "Cancelled" status badge
- No action buttons visible

### 11. Reschedule Button
**What to capture:** The reschedule button on ticket page
**Highlight:** "Reschedule" button

### 12. Reschedule Confirmation Dialog
**What to capture:** The custom modal for reschedule confirmation
**Show:**
- Warning icon (⚠️)
- "Reschedule Registration" title
- Detailed message with bullet points
- Action buttons

### 13. Reschedule Success
**What to capture:** Success modal after successful reschedule
**Show:**
- Green checkmark icon (✓)
- Success message
- "OK" button

### 14. Reschedule Pending
**What to capture:** Pending modal when next queue doesn't exist
**Show:**
- Alert icon
- Pending message
- "OK" button

### 15. Status Badges - All Four
**What to capture:** Create a composite image showing all four status badges
**Method:** Take 4 tickets with different statuses and crop just the status badges
**Show:**
- Yellow "Waiting" badge
- Green "Completed" badge  
- Red "Cancelled" badge
- Blue "Rescheduled" badge

---

## For Administrators Section

### 16. Login Page with Sign Up Link
**What to capture:** Login page
**URL:** `/login`
**Show:**
- SmartQ logo
- "Welcome Back!" text
- Email and Password fields
- "Remember Me" checkbox
- "Log in" button
- "Don't have an account? Sign UP" link

### 17. Sign Up Form
**What to capture:** Registration form for new admins
**URL:** `/signup`
**Show:**
- Full Name field
- Email field
- Password fields
- Terms and Conditions checkbox
- "Create Account" button

### 18. Account Created Success
**What to capture:** Flash message after successful registration
**Show:** The centered green success modal

### 19. Login Form
**What to capture:** Filled login form (before submission)
**Show:** Form with sample data entered

### 20. Login Error Example
**What to capture:** Error modal for invalid credentials
**Show:**
- Red X icon
- "Incorrect password" or similar error message
- "OK" button

### 21. Admin Navigation
**What to capture:** Top navigation bar after login
**URL:** Any admin page (homepage, create queue, etc.)
**Show:** 
- SmartQ logo
- All navigation links (Home, Create Queue, Scan Tracking, Profile, Logout)
- Active link highlighted

### 22. Basic Information Section
**What to capture:** First section of Create Queue form
**URL:** `/createq`
**Show:**
- "📋 Basic Information" header
- Queue Type field
- Queue Purpose field
- Auto-generated URL note

### 23. Service Time Input
**What to capture:** Service time section with MM:SS fields
**Show:**
- Service time label
- Minutes input (e.g., "15")
- Seconds input (e.g., "30")
- Format indicator (MM:SS)

### 24. Time Slots
**What to capture:** The schedule time picker section
**Show:**
- Morning Start/End time pickers
- Afternoon Start/End time pickers
- All four time fields visible

### 25. Staff Count
**What to capture:** Staff/Windows input field
**Show:** Number input with sample value (e.g., "3")

### 26. Queue Limit Display
**What to capture:** Auto-calculated queue limit section
**Show:**
- "📊 Calculated Queue Limit" header
- Read-only queue limit field with calculated number
- Formula box explaining calculation
- Information note

### 27. Generated Queue
**What to capture:** Right side panel showing a newly created queue
**Show:**
- Queue title
- Purpose description
- Created date
- Service time info
- Staff count
- Queue limit
- QR code image
- Queue URL link
- "Download QR" and "Delete" buttons

### 28. Download QR Button
**What to capture:** Close-up of action buttons on queue card
**Highlight:** "Download QR" button

### 29. Delete Confirmation
**What to capture:** Custom delete confirmation modal
**Show:**
- Warning icon (⚠️)
- "Delete Queue" title
- Confirmation message
- "Yes, Proceed" and "Cancel" buttons

### 30. Delete Success
**What to capture:** Success modal after deletion
**Show:**
- Green checkmark icon
- "QR deleted successfully!" message
- "OK" button

### 31. View History Button
**What to capture:** The toggle button to switch views
**Highlight:** "View QR History" button

### 32. Queue History View
**What to capture:** Right panel showing historical queues
**Show:**
- "QR History (All History)" title
- Multiple queue cards (both active and removed)
- "(Removed)" indicators on deleted queues
- Preservation message for deleted queues

### 33. Scan Tracking Page
**What to capture:** Full page with both panels
**URL:** `/scantracking`
**Show:**
- Left panel with queue list
- Right panel with "Select a QR to see scans" message

### 34. Queue List Panel
**What to capture:** Left side with generated queues
**Show:**
- "Generated Queues" title
- Multiple queue cards
- QR codes
- "Add Candidate" and "View Scans" buttons

### 35. View Scans Button
**What to capture:** Close-up of a queue card
**Highlight:** "View Scans" button

### 36. Scan Details Panel
**What to capture:** Right panel after clicking View Scans
**Show:**
- "Scans for QR #[number]" title
- Search bar
- List of entries with various statuses
- Entry cards with details

### 37. Entry Card
**What to capture:** Single entry card with all details
**Show:**
- Full name in bold
- Phone number (bullet point)
- Purpose (bullet point)
- Scanned at timestamp (bullet point)
- Status badge (colored)
- "Done" button (if status is waiting)

### 38. Done Button
**What to capture:** Close-up of an entry with Done button
**Highlight:** Green "Done" button

### 39. Done Confirmation Dialog
**What to capture:** Custom modal for marking as done
**Show:**
- Warning icon (⚠️)
- "Mark as Complete" title
- Confirmation message
- "Yes, Proceed" and "Cancel" buttons

### 40. Mark Complete Success
**What to capture:** Success modal after marking done
**Show:**
- Green checkmark icon
- "User marked as completed!" message
- "OK" button

### 41. Completed Entry
**What to capture:** Entry card after being marked complete
**Show:**
- Green "Completed" status badge
- No "Done" button visible

### 42. Search Bar
**What to capture:** Entries with search bar in use
**Show:**
- Search bar with sample query
- Filtered results below

### 43. Add Candidate Button
**What to capture:** Queue card in left panel
**Highlight:** "Add Candidate" button

### 44. Add Candidate Modal
**What to capture:** The candidate form modal
**Show:**
- "Add Candidate" title
- All name fields (Last, First, M.I., Suffix)
- Phone field
- Required field indicators (*)
- Submit button
- Close (×) button

### 45. Candidate Added Success
**What to capture:** Success modal after adding candidate
**Show:** Success message confirmation

### 46. Profile Page
**What to capture:** Profile settings page
**URL:** `/admin_settings`
**Show:**
- Current email display
- Full Name field
- Password change fields (Old, New, Confirm)
- "Update Profile" button

### 47. Logout Success
**What to capture:** Login page after logout
**Show:** The flash message "Logged out successfully."

---

## Additional Screenshots (Optional but Recommended)

### 48. Mobile View - Registration Form
**What to capture:** Registration form on mobile device
**Tool:** Use browser DevTools (F12) → Toggle device toolbar
**Show:** Responsive design on mobile screen

### 49. Mobile View - Queue Ticket
**What to capture:** Ticket page on mobile device
**Show:** Mobile-optimized layout

### 50. Admin Dashboard - Homepage
**What to capture:** Initial landing page after admin login
**URL:** `/homepage`
**Show:** Any welcome or dashboard content

---

## Organizing Your Screenshots

### Recommended File Naming:
```
01_qr_code_example.png
02_queue_landing_page.png
03_registration_form_top.png
... etc
```

### Recommended Folder Structure:
```
screenshots/
├── user_section/
│   ├── 01_qr_code_example.png
│   ├── 02_queue_landing_page.png
│   └── ...
├── admin_section/
│   ├── 16_login_page.png
│   ├── 17_signup_form.png
│   └── ...
└── modals/
    ├── cancel_confirmation.png
    ├── reschedule_confirmation.png
    └── ...
```

---

## Tools for Screenshot Annotation

If you want to add arrows, highlights, or text to screenshots:

1. **Windows:** Paint, Paint 3D, Snip & Sketch
2. **Mac:** Preview (Markup tools)
3. **Cross-platform:** 
   - GIMP (free)
   - Photoshop
   - Figma
   - Canva

---

## Tips for Better Screenshots

1. **Clear Background:** Close unnecessary browser tabs and applications
2. **Full Screen:** Capture in fullscreen mode for professional look
3. **Consistent Browser:** Use the same browser for all screenshots
4. **Sample Data:** Use realistic names like "Juan Dela Cruz" instead of "Test User"
5. **Anonymize:** Blur out any real personal information if using production data
6. **Lighting:** Ensure good screen brightness and contrast
7. **Resolution:** Capture at least 1920x1080 or higher for print quality

---

## Creating the Final Document

### Converting to PDF:
1. Open USER_MANUAL.md in a Markdown editor
2. Replace all `![Screenshot: Description]` placeholders with actual image files
3. Use a tool to convert Markdown to PDF:
   - **Online:** Dillinger.io, MarkdownToPDF.com
   - **Desktop:** Typora, Visual Studio Code with Markdown PDF extension
   - **Command Line:** pandoc

### Adding Images in Markdown:
Replace:
```markdown
![Screenshot: QR Code Example]
*[Insert screenshot of a sample QR code]*
```

With:
```markdown
![Screenshot: QR Code Example](screenshots/user_section/01_qr_code_example.png)
```

---

*Good luck with your documentation! 📸*

