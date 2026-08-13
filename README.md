# Pipeline AI — Integrations Technical Assessment

This repository contains the implementation of the **HubSpot integration assessment** for Pipeline AI. It consists of:

- **Backend** (`/backend`): Python / FastAPI server that handles OAuth flows for HubSpot (and Airtable / Notion) and loads integration items from the connected accounts.
- **Frontend** (`/frontend`): JavaScript / React (Create React App) UI to connect integrations via OAuth and display the loaded data.
- **Redis**: used to store OAuth state and credentials temporarily (with 10-minute expiry).

All OAuth state, credentials, and tokens are exchanged and stored in Redis; the frontend never sees client secrets.

---

## 1. Prerequisites

| Tool     | Version      | Check         |
|----------|--------------|---------------|
| Python   | 3.8+         | `python3 --version` |
| Node.js  | 14+          | `node --version` |
| npm      | 6+           | `npm --version` |
| Redis    | any recent   | `redis-server --version` |

> The backend uses a virtual environment (`backend/.venv`, git-ignored) and a pinned `requirements.txt`.

---

## 2. Start Redis

Redis must be running before starting the backend:

```bash
redis-server
```

By default the backend connects to `localhost:6379`. Override with the `REDIS_HOST` environment variable if needed.

---

## 3. Backend Setup

```bash
cd backend

# create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# install dependencies
pip install -r requirements.txt
```

### Backend environment variables

Copy the demo file and fill in your own HubSpot credentials:

```bash
cp .env.demo .env
```

| Variable                | Required | Description |
|-------------------------|----------|-------------|
| `HUBSPOT_CLIENT_ID`     | Yes*     | Your HubSpot app's Client ID (from the HubSpot developer portal). Falls back to the placeholder `xxx`. |
| `HUBSPOT_CLIENT_SECRET` | Yes*     | Your HubSpot app's Client Secret. Falls back to the placeholder `xxx`. |
| `HUBSPOT_REDIRECT_URI`  | No       | OAuth redirect URI. Defaults to `http://localhost:8000/integrations/hubspot/oauth2callback`. Must match the redirect URI configured in your HubSpot app. |
| `REDIS_HOST`            | No       | Redis host. Defaults to `localhost`. |

\* Required for the HubSpot OAuth flow to actually work — the assessment expects you to create your own HubSpot app and supply these.

> The backend auto-loads `.env` via `python-dotenv` (`load_dotenv()` in `main.py`) on startup, so no manual exporting is needed.

### Run the backend

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000` (docs at `http://localhost:8000/docs`).

---

## 4. Frontend Setup

```bash
cd frontend

npm install
```

### Frontend environment variables

Copy the demo file and adjust if your backend is not on localhost:

```bash
cp .env.demo .env
```

| Variable                 | Required | Description |
|--------------------------|----------|-------------|
| `REACT_APP_BACKEND_URL`  | No       | Base URL of the FastAPI backend. Defaults to `http://localhost:8000`. Set this to your deployed/codespace backend URL if you are not running locally. |

### Run the frontend

```bash
npm run start
```

The app will be available at `http://localhost:3000`.

> Create React App only exposes variables prefixed with `REACT_APP_` to the browser. You must restart `npm run start` after changing `.env`.

---

## 5. Create a HubSpot App

To test the HubSpot integration end-to-end:

1. Go to the [HubSpot Developer Portal](https://developers.hubspot.com/) → **Create an app**.
2. Add the following **scopes**:
   - `crm.objects.contacts.read`
   - `crm.objects.companies.read`
   - `crm.objects.deals.read`
3. Set the **Redirect URI** to exactly match `HUBSPOT_REDIRECT_URI` (default: `http://localhost:8000/integrations/hubspot/oauth2callback`).
4. Copy the **Client ID** and **Client Secret** into `backend/.env`.
5. Restart the backend with the new variables exported.

---

## 6. Testing the Integration

1. Start Redis, the backend, and the frontend (steps 2–4).
2. Open the frontend at `http://localhost:3000`.
3. Enter a **User** and **Organization** (any values, e.g. `TestUser` / `TestOrg`).
4. Select **HubSpot** from the Integration Type dropdown.
5. Click **Connect to HubSpot** — an OAuth window opens against HubSpot.
6. After authorizing, the window closes and the button turns green (**HubSpot Connected**).
7. Click **Load Data** to fetch contacts, companies, and deals from HubSpot. The `IntegrationItem` list is rendered in a table and also printed to the backend console.

> Airtable and Notion integrations are included but will not work out of the box because their client credentials are redacted. You may optionally create your own Notion/Airtable credentials to test them.

---

## 7. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/` | Health check (`{"Ping": "Pong"}`) |
| POST | `/integrations/hubspot/authorize` | Starts the HubSpot OAuth flow, returns the authorization URL (form: `user_id`, `org_id`) |
| GET  | `/integrations/hubspot/oauth2callback` | HubSpot OAuth callback — exchanges the code for tokens, stores credentials in Redis |
| POST | `/integrations/hubspot/credentials` | Returns (and deletes) the stored credentials for a user/org |
| POST | `/integrations/hubspot/get_hubspot_items` | Loads contacts/companies/deals as `IntegrationItem` objects (form: `credentials`) |
| POST | `/integrations/airtable/authorize` | Airtable OAuth (same flow) |
| GET  | `/integrations/airtable/oauth2callback` | Airtable OAuth callback |
| POST | `/integrations/airtable/credentials` | Airtable credentials lookup |
| POST | `/integrations/airtable/load` | Loads Airtable bases/tables |
| POST | `/integrations/notion/authorize` | Notion OAuth (same flow) |
| GET  | `/integrations/notion/oauth2callback` | Notion OAuth callback |
| POST | `/integrations/notion/credentials` | Notion credentials lookup |
| POST | `/integrations/notion/load` | Loads Notion pages/databases |

---

## 8. Project Structure

```
.
├── backend/
│   ├── main.py                      # FastAPI app + routes
│   ├── redis_client.py              # Redis helpers
│   ├── requirements.txt             # pinned Python dependencies
│   ├── .env.demo                    # backend env var template
│   └── integrations/
│       ├── integration_item.py      # IntegrationItem model
│       ├── hubspot.py               # HubSpot OAuth + item loading
│       ├── airtable.py              # Airtable integration (complete)
│       └── notion.py                # Notion integration (complete)
└── frontend/
    ├── package.json                 # React (CRA) app
    ├── .env.demo                    # frontend env var template
    └── src/
        ├── App.js
        ├── integration-form.js      # integration selector + connect UI
        ├── data-form.js             # Load Data table
        ├── config.js                # API_BASE_URL from REACT_APP_BACKEND_URL
        └── integrations/
            ├── hubspot.js           # HubSpot connect UI
            ├── airtable.js          # Airtable connect UI
            └── notion.js            # Notion connect UI
```

---

## 9. Assessment Checklist

- [x] `authorize_hubspot` — builds OAuth URL, stores CSRF state in Redis
- [x] `oauth2callback_hubspot` — validates state, exchanges code for tokens, stores credentials in Redis
- [x] `get_hubspot_credentials` — retrieves and clears credentials
- [x] `get_items_hubspot` — queries contacts/companies/deals (paginated), returns `IntegrationItem` list, prints to console
- [x] `frontend/src/integrations/hubspot.js` — full connect UI (OAuth popup + polling)
- [x] HubSpot wired into `integration-form.js`, `data-form.js`, and `backend/main.py`
- [x] Backend base URL configurable via `REACT_APP_BACKEND_URL`