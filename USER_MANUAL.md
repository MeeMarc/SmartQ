# SmartQ User Manual

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [For Queue Users](#for-queue-users)
4. [For Administrators](#for-administrators)
5. [Troubleshooting](#troubleshooting)
6. [FAQs](#faqs)

---

## Introduction

### What is SmartQ?

SmartQ is a digital queue management system that helps organizations streamline their customer service process. It eliminates physical queues by allowing customers to register online and wait for their turn remotely.

### Key Features

- ✅ **QR Code Registration** - Easy queue registration via QR code scanning
- 📱 **Mobile-Friendly** - Works on any device with a web browser
- 🎫 **Digital Tickets** - Downloadable queue tickets with reference numbers
- 🔄 **Reschedule Option** - Customers can reschedule to the next available queue
- 📊 **Admin Dashboard** - Real-time queue monitoring and management
- 🕒 **Auto-Calculation** - Smart queue limit calculation based on service time

---

## Getting Started

### System Requirements

- **For Users:** Any device with a web browser and internet connection
- **For Admins:** Desktop or laptop with modern web browser (Chrome, Firefox, Edge, Safari)

### Accessing SmartQ

**Production URL:** https://smartq-vd9k.onrender.com

---

## For Queue Users

### 1. Scanning the QR Code

**Step 1:** Use your phone's camera or QR code scanner app to scan the QR code provided by the service provider.

![Screenshot: QR Code Example]
*[Insert screenshot of a sample QR code]*

**Step 2:** You'll be automatically redirected to the queue registration page.

![Screenshot: Queue Landing Page]
*[Insert screenshot of the queue landing page showing the queue name and instructions]*

---

### 2. Registering for a Queue

**Step 1:** On the registration page, you'll see information about the queue:
- Queue name/type
- Purpose/description
- Queue number

![Screenshot: Registration Form Top Section]
*[Insert screenshot showing queue information]*

**Step 2:** Fill out the registration form with the following details:

Required Fields (marked with *):
- **Last Name** - Your family name
- **First Name** - Your given name
- **Phone Number** - Your contact number (format: 09XXXXXXXXX)

Optional Fields:
- **Middle Initial** - Your middle name initial
- **Suffix** - Jr., Sr., III, etc. (if applicable)
- **Purpose** - Specific reason for your visit

![Screenshot: Registration Form]
*[Insert screenshot of the complete registration form]*

**Step 3:** Click the **"Submit"** button.

**Step 4:** You'll receive a confirmation with your queue ticket.

![Screenshot: Success Message]
*[Insert screenshot of the successful registration confirmation]*

---

### 3. Your Queue Ticket

After successful registration, you'll see your digital ticket with:

- ✅ **Ticket Confirmed!** message
- **Queue Number** - Your position reference (e.g., Queue #1)
- **Ticket Reference** - Unique identifier for your registration
- **Status Badge** - Current status (Waiting, Completed, Cancelled, Rescheduled)
- **Ticket Holder Name** - Your full name
- **Important Instructions** - What to bring and when to proceed

![Screenshot: Queue Ticket]
*[Insert screenshot of a complete queue ticket]*

---

### 4. Downloading Your Ticket

**Step 1:** Click the **"📥 Download Ticket"** button on your ticket page.

**Step 2:** The ticket will be saved as a PDF file to your device.

**Step 3:** Present this ticket along with your documents at the registrar desk.

![Screenshot: Download Button]
*[Insert screenshot highlighting the download button]*

---

### 5. Cancelling Your Registration

⚠️ **Important:** Cancellation is permanent and cannot be undone.

**Step 1:** On your ticket page, click the **"Cancel Registration"** button.

![Screenshot: Cancel Button Location]
*[Insert screenshot showing the cancel button]*

**Step 2:** A confirmation dialog will appear asking you to confirm.

![Screenshot: Cancel Confirmation Dialog]
*[Insert screenshot of the cancel confirmation modal]*

**Step 3:** Click **"Yes, Proceed"** to confirm or **"Cancel"** to go back.

**Step 4:** If confirmed, your registration will be cancelled and your ticket status will change to "Cancelled".

![Screenshot: Cancelled Ticket]
*[Insert screenshot of a ticket with cancelled status]*

---

### 6. Rescheduling Your Appointment

Need to move to a different queue? Use the reschedule feature!

**Step 1:** On your ticket page, click the **"Reschedule"** button.

![Screenshot: Reschedule Button]
*[Insert screenshot showing the reschedule button]*

**Step 2:** Read the important information in the confirmation dialog:
- Your current slot will be freed for another person
- You'll be moved to the next queue of the same type
- You can only reschedule once per 24 hours

![Screenshot: Reschedule Confirmation Dialog]
*[Insert screenshot of the reschedule confirmation modal]*

**Step 3:** Click **"Yes, Proceed"** to confirm.

**Two Possible Outcomes:**

#### A. Next Queue Exists
- ✅ Success message appears
- You're automatically moved to the next queue
- You'll be redirected to your new ticket page

![Screenshot: Reschedule Success]
*[Insert screenshot of successful reschedule message]*

#### B. Next Queue Doesn't Exist Yet
- ⏳ Pending message appears
- You'll be automatically enrolled when the next queue is created
- Your current slot is freed immediately

![Screenshot: Reschedule Pending]
*[Insert screenshot of pending reschedule message]*

---

### 7. Understanding Status Badges

Your ticket will display one of these status badges:

| Status | Color | Meaning |
|--------|-------|---------|
| **Waiting** | 🟡 Yellow | You're in the queue, waiting for your turn |
| **Completed** | 🟢 Green | Your service has been completed |
| **Cancelled** | 🔴 Red | Your registration was cancelled |
| **Rescheduled** | 🔵 Blue | You've been moved to another queue |

![Screenshot: Status Badges]
*[Insert screenshot showing all different status badges]*

---

## For Administrators

### 1. Creating an Account

**Step 1:** Go to the login page and click **"Sign Up"**.

![Screenshot: Login Page with Sign Up Link]
*[Insert screenshot of login page]*

**Step 2:** Fill out the registration form:
- Full Name
- Email Address
- Password
- Confirm Password
- Agree to Terms and Conditions

![Screenshot: Sign Up Form]
*[Insert screenshot of the sign-up form]*

**Step 3:** Click **"Create Account"**.

**Step 4:** You'll receive a success message. Click **"Log in"** to proceed.

![Screenshot: Account Created Success]
*[Insert screenshot of success message]*

---

### 2. Logging In

**Step 1:** Enter your email and password.

**Step 2:** (Optional) Check **"Remember Me"** to save your email for next time.

![Screenshot: Login Form]
*[Insert screenshot of login form]*

**Step 3:** Click **"Log in"**.

**Error Handling:**
- ❌ If you see "Invalid credentials" - Check your email and password
- ❌ If you see "Account not found" - You need to sign up first

![Screenshot: Login Error Example]
*[Insert screenshot of error message modal]*

---

### 3. Admin Dashboard

After logging in, you'll see the navigation menu with access to:

- **Home** - Dashboard overview
- **Create Queue** - Generate new QR codes and queues
- **Scan Tracking** - Monitor and manage queue entries
- **Profile** - Update your account settings
- **Logout** - Sign out of your account

![Screenshot: Admin Navigation]
*[Insert screenshot of the admin navigation bar]*

---

### 4. Creating a New Queue

**Step 1:** Click **"Create Queue"** in the navigation menu.

**Step 2:** Fill out the form with three sections:

#### Section 1: Basic Information

- **Queue Type** - Name of the service (e.g., "Requirements Submission")
- **Queue Purpose** - Description (e.g., "Submit documents or claim ID")

![Screenshot: Basic Information Section]
*[Insert screenshot of basic information fields]*

#### Section 2: Queue Capacity Settings

Configure your service parameters:

**a) Average Service Time per Customer**
- Enter minutes and seconds (e.g., 15 minutes 30 seconds)
- Format: MM:SS

![Screenshot: Service Time Input]
*[Insert screenshot of service time fields]*

**b) Total Available Service Time**
- **Morning Start** - When service begins (default: 08:00)
- **Morning End** - Lunch break time (default: 12:00)
- **Afternoon Start** - When service resumes (default: 13:00)
- **Afternoon End** - When service ends (default: 17:00)

![Screenshot: Time Slots]
*[Insert screenshot of time slot inputs]*

**c) Number of Staff/Windows**
- Enter how many service windows/staff are available

![Screenshot: Staff Count]
*[Insert screenshot of staff count field]*

#### Section 3: Auto-Calculated Queue Limit

The system automatically calculates the maximum customers per day using this formula:

```
Queue Limit = (Total Available Time ÷ Average Service Time) × Number of Staff
```

This field is **read-only** and updates automatically.

![Screenshot: Queue Limit Display]
*[Insert screenshot showing the calculated queue limit]*

**Step 3:** Click **"Generate QR"**.

**Step 4:** Your new queue will appear on the right side with:
- QR Code image
- Queue details
- Queue URL
- Action buttons (Download QR, Delete)

![Screenshot: Generated Queue]
*[Insert screenshot of a newly generated queue with QR code]*

---

### 5. Managing Generated Queues

On the right side of the Create Queue page, you'll see all your generated queues.

#### Downloading QR Codes

**Step 1:** Find the queue you want to download.

**Step 2:** Click the **"Download QR"** button.

**Step 3:** The QR code will be saved as a PNG image file.

![Screenshot: Download QR Button]
*[Insert screenshot showing download button]*

#### Deleting Queues

⚠️ **Warning:** Deletion is permanent!

**Step 1:** Click the **"Delete"** button on the queue you want to remove.

**Step 2:** A confirmation dialog will appear.

![Screenshot: Delete Confirmation]
*[Insert screenshot of delete confirmation modal]*

**Step 3:** Click **"Yes, Proceed"** to confirm or **"Cancel"** to go back.

**Step 4:** Upon successful deletion, you'll see a success message.

![Screenshot: Delete Success]
*[Insert screenshot of deletion success message]*

---

### 6. Viewing Queue History

Want to see all queues you've ever created (including deleted ones)?

**Step 1:** On the Create Queue page, click **"View QR History"**.

![Screenshot: View History Button]
*[Insert screenshot of the history button]*

**Step 2:** The display will switch to show your complete history with:
- All created queues
- Creation dates
- Queue settings
- Status indicators (Active/Removed)

![Screenshot: Queue History View]
*[Insert screenshot of the history view]*

**Step 3:** Click **"View Generated Queues"** to return to active queues.

---

### 7. Scan Tracking - Monitoring Queue Entries

**Step 1:** Click **"Scan Tracking"** in the navigation menu.

![Screenshot: Scan Tracking Page]
*[Insert screenshot of the scan tracking page layout]*

#### Left Panel: Generated Queues

This shows all your queues (active and removed) with:
- Queue type and purpose
- Creation date and time
- QR code
- Queue URL
- Status (active or removed)
- Action buttons

![Screenshot: Queue List Panel]
*[Insert screenshot of the left panel with queue list]*

#### Right Panel: Scan Details

Initially shows: **"Select a QR to see scans"**

**Step 2:** Click **"View Scans"** on any queue to see registered users.

![Screenshot: View Scans Button]
*[Insert screenshot highlighting the view scans button]*

**Step 3:** The right panel will display:
- Queue number identifier
- Search bar to filter entries
- List of all registered users

![Screenshot: Scan Details Panel]
*[Insert screenshot of scan details with entries]*

---

### 8. Managing Queue Entries

#### Viewing Entry Details

Each entry shows:
- **Full Name** - Customer's name
- **Phone Number** - Contact information
- **Purpose** - Reason for visit (if provided)
- **Scanned At** - Registration timestamp
- **Status Badge** - Current status (color-coded)
- **Action Buttons** - Available actions based on status

![Screenshot: Entry Card]
*[Insert screenshot of a single entry card with all details]*

#### Marking Entries as Done

**Step 1:** Find the entry you want to mark as complete.

**Step 2:** Click the **"Done"** button next to the entry.

![Screenshot: Done Button]
*[Insert screenshot showing the done button on an entry]*

**Step 3:** A confirmation dialog appears asking: *"Are you sure you want to mark this user as served/completed?"*

![Screenshot: Done Confirmation Dialog]
*[Insert screenshot of the mark as done confirmation]*

**Step 4:** Click **"Yes, Proceed"** to confirm.

**Step 5:** Success message appears: *"✓ User marked as completed!"*

![Screenshot: Mark Complete Success]
*[Insert screenshot of success message]*

**Step 6:** The entry's status badge changes to **"Completed"** (green) and the Done button disappears.

![Screenshot: Completed Entry]
*[Insert screenshot of an entry with completed status]*

#### Searching/Filtering Entries

Use the search bar to quickly find specific entries by:
- Name
- Phone number
- Purpose
- Status

![Screenshot: Search Bar]
*[Insert screenshot demonstrating the search feature]*

---

### 9. Adding Candidates Manually

Can't wait for users to scan? Add them directly!

**Step 1:** In the queue list (left panel), click **"Add Candidate"** on the desired queue.

![Screenshot: Add Candidate Button]
*[Insert screenshot showing add candidate button]*

**Step 2:** Fill out the candidate form:
- **Last Name** (required)
- **First Name** (required)
- **Middle Initial** (optional)
- **Suffix** (optional)
- **Phone** (required)

![Screenshot: Add Candidate Modal]
*[Insert screenshot of the add candidate form]*

**Step 3:** Click **"Submit"**.

**Step 4:** Success message appears and the candidate is added to the queue.

![Screenshot: Candidate Added Success]
*[Insert screenshot of success message]*

---

### 10. Profile Settings

**Step 1:** Click **"Profile"** in the navigation menu.

**Step 2:** You can update:
- **Full Name** - Your display name
- **Old Password** - Current password (required if changing password)
- **New Password** - Your new password
- **Confirm Password** - Re-enter new password for verification

![Screenshot: Profile Page]
*[Insert screenshot of profile settings page]*

**Step 3:** Click **"Update Profile"** to save changes.

**Step 4:** You'll see a success message confirming your updates.

---

### 11. Logging Out

**Step 1:** Click **"Logout"** in the navigation menu.

**Step 2:** You'll be redirected to the login page with a confirmation message: *"Logged out successfully."*

![Screenshot: Logout Success]
*[Insert screenshot of logout confirmation message]*

---

## Troubleshooting

### Common Issues for Users

#### Issue: Can't Submit Registration Form
**Possible Causes:**
- Missing required fields (marked with *)
- Invalid phone number format
- Network connection issues

**Solution:**
1. Check all required fields are filled
2. Ensure phone number starts with 09 and has 11 digits
3. Check your internet connection
4. Try refreshing the page

#### Issue: Can't Download Ticket
**Solution:**
1. Ensure pop-ups are not blocked in your browser
2. Check your download folder
3. Try using a different browser

#### Issue: Can't Reschedule
**Possible Causes:**
- Already rescheduled within the last 24 hours
- Ticket status is not "Waiting"

**Solution:**
- Wait 24 hours from your last reschedule
- Check your ticket status
- Contact the administrator if issue persists

---

### Common Issues for Administrators

#### Issue: Can't Login
**Possible Causes:**
- Incorrect email or password
- Account doesn't exist

**Solution:**
1. Double-check your credentials
2. Use "Remember Me" feature to avoid typos
3. Create an account if you haven't already

#### Issue: Queue Limit Shows Incorrect Number
**Possible Causes:**
- Invalid service time input
- Invalid schedule times
- Missing staff count

**Solution:**
1. Verify all capacity settings are filled correctly
2. Ensure time format is valid (MM:SS for service time)
3. Check that morning/afternoon times don't overlap
4. Ensure there's a break between sessions

#### Issue: Generated Queue Doesn't Show Entries
**Possible Causes:**
- No one has registered yet
- Wrong queue selected
- Database connection issue

**Solution:**
1. Wait for users to register via QR code
2. Verify you're viewing the correct queue
3. Try refreshing the page
4. Check the debug endpoint: `/debug_queue_entries/[slug]/[number]`

#### Issue: Can't Delete Queue
**Possible Causes:**
- Network error
- Queue already deleted

**Solution:**
1. Check your internet connection
2. Refresh the page and try again
3. Check if the queue appears in History

---

## FAQs

### For Users

**Q: Do I need to download an app?**
A: No! SmartQ works directly in your web browser. Just scan the QR code.

**Q: What if I lose my ticket reference number?**
A: Your phone number is linked to your registration. Contact the service desk with your phone number and name.

**Q: Can I reschedule multiple times?**
A: You can only reschedule once every 24 hours per queue type.

**Q: What happens if I don't show up?**
A: Your registration remains active until you cancel it or it expires. However, it's courteous to cancel if you can't make it.

**Q: Is my data secure?**
A: Yes! SmartQ only collects necessary information and follows data protection best practices.

---

### For Administrators

**Q: How many queues can I create?**
A: There's no limit! Create as many queues as you need for different services.

**Q: Can I edit a queue after creating it?**
A: Currently, you cannot edit existing queues. You can delete and create a new one if needed.

**Q: How long are deleted queues kept in history?**
A: Queue history is permanent and serves as a record of all queues you've created.

**Q: What happens to entries when I delete a queue?**
A: Entries are preserved in the database. The QR code becomes inactive but historical data remains accessible via Scan Tracking.

**Q: Can multiple admins manage the same queues?**
A: Currently, each admin account manages their own queues independently.

**Q: How do I know when a user reschedules?**
A: Check the Scan Tracking page - you'll see entries with "Rescheduled" status badges (blue).

**Q: What's the difference between temp_qr and qr_history?**
A: 
- **temp_qr** - Currently active queues
- **qr_history** - Permanent record of all queues (active and deleted)

---

## Support & Contact

For technical support or questions about SmartQ, please contact your system administrator.

### Debug Tools for Administrators

If you encounter issues, you can use these debug endpoints:

- View entries for a specific queue:
  ```
  /debug_queue_entries/[queue-slug]/[queue-number]
  ```
  Example: `/debug_queue_entries/test/1`

This will show you all entries with detailed status information.

---

## Quick Reference Guide

### User Workflow
1. Scan QR Code → 2. Fill Form → 3. Submit → 4. Download Ticket → 5. Wait for Turn → 6. Proceed to Counter

### Admin Workflow
1. Login → 2. Create Queue → 3. Share QR Code → 4. Monitor via Scan Tracking → 5. Mark as Done

---

## Appendix: Keyboard Shortcuts

### For Administrators (Web Interface)

- **F5** - Refresh page to see latest entries
- **Ctrl + F** - Find text on page (useful for searching entries)
- **Ctrl + P** - Print QR code or queue details

---

*Last Updated: November 2025*
*Version: 1.0*

---

**Note:** This user manual is designed to be printed or distributed as a PDF. Make sure to add actual screenshots from your SmartQ deployment at the indicated placeholders for the best user experience.

