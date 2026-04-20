# ECI e-Voting System Prototype

A robust, secure, and modern online voting system prototype developed for the Election Commission of India (ECI) for the state of Madhya Pradesh. The system provides separate portals for Election Administrators and Registered Voters.

## 🚀 Features

### Admin Portal
- **Campaign Management:** Create multiple election campaigns (e.g., MLA elections, local body elections) by specifying constituency, start, and end dates.
- **Candidate Registration:** Add multiple candidates to specific campaigns, including details like party name, party symbol, and candidate ID.
- **Live Monitoring & Results:** View live voting statistics and securely publish final results to voters.
- **Security:** Built-in lockout mechanism after 3 unsuccessful login attempts.

### Voter Portal
- **Secure Authentication:** Log in using predefined credentials from the Voter Dataset (Excel file).
- **Campaign Participation:** Browse and participate only in active, ongoing campaigns based on real-time scheduling.
- **One Voter, One Vote:** Strict enforcement mechanism ensuring registered voters can only cast a single vote per campaign.
- **Vote Confirmation & Receipt:** Review vote selection before final submission and get a secure digital receipt.

---

## 🛠️ Tech Stack
- **Backend:** Python 3.x, Flask (Web Framework)
- **Database:** SQLite3 (`voting.db` for campaigns, candidates, votes, and security logs)
- **Data Storage:** Pandas and OpenPyxl (for handling pre-defined voter dataset `voter_data.xlsx`)
- **Frontend:** HTML5, modern Vanilla CSS with custom theming (Dark Navy/Blue for Admin, Deep Teal for Voter)

---

## 💻 Prerequisites

Ensure you have Python 3.x installed on your system.

Install the required Python packages by running:
```bash
pip install flask pandas openpyxl
```

---

## 🏃 Getting Started

1. **Clone or Download** the project repository.
2. **Navigate** to the project directory:
   ```bash
   cd "e_voting website2"
   ```
3. **Run the Application:**
   ```bash
   python app.py
   ```
   *Note: Upon successful execution, the required `voting.db` database and `voter_data.xlsx` dataset will be initialized automatically if they do not exist.*

4. **Access the App:** 
   Open your browser and navigate to: `http://127.0.0.1:5000`

---

## 🔐 System Credentials

### Admin Login 
*Hardcoded for security per prototype requirements*
- **Username:** `admin`
- **Password:** `Admin@ECI2024`

### Voter Login
*Stored in the auto-generated `voter_data.xlsx` file. Sample voters:*
| Voter ID | Password | Name |
| :--- | :--- | :--- |
| **MP001** | `pass123` | Ravi Sharma |
| **MP002** | `mypass` | Sunita Patel |
| **MP003** | `vote2024` | Arjun Singh |

*(You can edit `voter_data.xlsx` using Excel to add or remove voters. Ensure the columns remain: VoterID, Name, Password)*

---

## 🛡️ Security Measures
- **3-Attempt Lockout:** Accounts (both Admin and Voter) will be locked after 3 consecutive failed login attempts.
- **Session Guards:** Secure routing ensuring authenticated access.
- **Time-bound Voting:** Voters can only cast votes between the active Start and End dates defined by the Admin.

---

*Project developed for the Election Commission of India (Prototype)*
