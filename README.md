# NetGear Switch Configurator

A comprehensive web application for configuring and selecting network switches based on specific requirements.

## Features

- **Interactive Web Interface**: Easy-to-use form with dropdowns and radio buttons
- **Switch Specifications**: Configure port counts, PoE requirements, SFP interfaces, and speeds
- **Multi-Brand Support**: NetGear, Cisco, HP, Extreme, Juniper, Dell, Luxul, Blackbox
- **Distributor Integration**: Check availability from TD SYNNEX, Ingram Micro, and Q360
- **VLAN Configuration**: Support for various VLAN types (Control, Audio, Video, IPTV, etc.)
- **Distance Requirements**: MDF and IDF distance calculations
- **Media Connector Types**: SFP, LC-LC, LC-ST, LC-SC support

## Quick Start

1. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

2. **Access the application:**
   - Open your browser to `http://localhost:5000`

3. **Configure your requirements:**
   - Select port counts (8, 10, 12, 24, 26, 28, 30, 40, 48, 50, 52)
   - Choose PoE requirements (PoE, PoE+, PoE++)
   - Set SFP interface needs (1, 2, 4, 8, 12, 24, 48)
   - Select minimum speeds (1GB, 2.5GB, 10GB, 40GB, 100GB, 400GB, 800GB)
   - Configure VLAN requirements

## Architecture

- **Backend**: Flask API with SQLAlchemy ORM
- **Database**: SQLite (easily configurable to PostgreSQL/MySQL)
- **Frontend**: Bootstrap-based responsive interface
- **Caching**: Redis for distributor API responses
- **Containerization**: Docker with multi-service setup

## API Endpoints

- `GET /` - Main application interface
- `POST /api/switches/search` - Search switches by requirements
- `POST /api/distributors/availability` - Check distributor availability
- `POST /api/vlan/configure` - Configure VLAN settings
- `GET /api/brands` - Get available brands

## Configuration

The application supports the following environment variables:

- `DATABASE_URL` - Database connection string (default: sqlite:///data/switches.db)
- `FLASK_ENV` - Flask environment (development/production)
- `SECRET_KEY` - Flask secret key

## Database Schema

### Switch Model
- Brand, Model, Port Count
- PoE specifications (standard, plus, plus-plus)
- SFP port count and speeds
- Stacking support
- Price and availability data

### VLAN Configuration
- Switch association
- VLAN count and types
- Configuration timestamps

## Development

1. **Local development without Docker:**
   ```bash
   pip install -r requirements.txt
   python app.py
   ```

2. **Database initialization:**
   The application automatically creates tables and seeds initial data on first run.

## Distributor Integration

The application includes placeholder integration for:
- **TD SYNNEX**: Pricing and availability
- **Ingram Micro**: Stock levels and pricing
- **Q360**: Availability status

*Note: Replace mock API calls with actual distributor API endpoints.*

## VLAN Types Supported

- Control VLAN
- Audio VLAN
- Video VLAN
- IPTV VLAN
- Broadcast VLAN
- Dante VLAN
- AVB VLAN
- QLAN VLAN
- QSC VLAN
- Lighting VLAN
- DS VLAN

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - See LICENSE file for details