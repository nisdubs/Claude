# NetGear Switch Configurator - Deployment Guide

## Quick Setup for Company Testing

### Option 1: Docker (Recommended for Technical Users)

**Prerequisites**: Docker installed on your machine

**Steps**:
1. Clone the repository:
   ```bash
   git clone https://github.com/nisdubs/Claude.git
   cd "NetGear Switch Configurator"
   ```

2. Start the application:
   ```bash
   docker-compose up -d
   ```

3. Access the app at: **http://localhost:5001**

4. To stop the application:
   ```bash
   docker-compose down
   ```

### Option 2: Cloud Deployment (Best for Easy Sharing)

#### Deploy to Render.com (Free Tier Available)

1. Go to [render.com](https://render.com) and sign up
2. Connect your GitHub account
3. Create a new "Web Service"
4. Select the repository: `nisdubs/Claude`
5. Use these settings:
   - **Name**: `netgear-switch-configurator`
   - **Environment**: `Docker`
   - **Build Command**: (leave empty)
   - **Start Command**: (leave empty)
   - **Instance Type**: `Free` or `Starter`
6. Click "Create Web Service"
7. Share the generated URL with your team

#### Deploy to Railway (Alternative)

1. Go to [railway.app](https://railway.app) and sign up
2. Click "Deploy from GitHub repo"
3. Select the repository: `nisdubs/Claude`
4. Railway will auto-detect the Docker setup
5. Click "Deploy"
6. Share the generated URL

### Option 3: Local Python Setup (For Developers)

**Prerequisites**: Python 3.11+ installed

**Steps**:
1. Clone the repository:
   ```bash
   git clone https://github.com/nisdubs/Claude.git
   cd "NetGear Switch Configurator"
   ```

2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python app.py
   ```

5. Access the app at: **http://localhost:5000**

## Testing the Search Feature

### Key Features to Test:

1. **Text Search**:
   - Search for "M4250" to find NetGear M4250 series switches
   - Search for "PoE+" to find switches with PoE+ support
   - Search for "Cisco" to find Cisco switches

2. **Autocomplete**:
   - Type "Net" in the search box - should show NetGear suggestions
   - Type "M42" - should show M4250 series suggestions

3. **Advanced Filters**:
   - Select "NetGear" from brand dropdown
   - Set minimum/maximum port counts
   - Check "PoE Required" checkbox
   - Check "Stacking Required" checkbox

4. **Switch Details**:
   - Results show detailed specifications
   - Copper/fiber port breakdowns
   - PoE types and power ratings
   - Use cases and management options

### Sample Test Queries:

- Search: "M4250" → Should find 13 NetGear M4250 switches
- Search: "PoE++" → Should find switches with PoE++ support
- Search: "AV over IP" → Should find switches designed for AV applications
- Search: "Catalyst" → Should find Cisco Catalyst switches

## Configuration

### Environment Variables (Optional)

Create a `.env` file for additional configuration:

```bash
# Notion Integration (optional)
NOTION_TOKEN=your-notion-token
NOTION_DATABASE_ID=your-database-id

# Distributor APIs (optional)
INGRAM_API_KEY=your-ingram-key
SYNNEX_API_KEY=your-synnex-key

# Database
DATABASE_URL=sqlite:///switches.db
```

## Troubleshooting

### Common Issues:

1. **Port 5001 already in use**: 
   - Stop other services using port 5001
   - Or modify `docker-compose.yml` to use different port

2. **Search not working**:
   - Check if database is populated (search for "NetGear" should return results)
   - Verify API endpoints: `/api/switches/search-text` and `/api/switches/quick-search`

3. **No switches found**:
   - Database auto-populates on first run
   - Check console logs for CSV loading errors

### Support

For technical support, contact the development team or check the GitHub repository issues.