from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
import requests
import json
import csv
from datetime import datetime
from notion_client import Client

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///switches.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

db = SQLAlchemy(app)

# Database Models
class Switch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    port_count = db.Column(db.Integer, nullable=False)
    poe_ports = db.Column(db.Integer, default=0)
    poe_plus_ports = db.Column(db.Integer, default=0)
    poe_plus_plus_ports = db.Column(db.Integer, default=0)
    total_poe_watts = db.Column(db.Integer, default=0)
    sfp_ports = db.Column(db.Integer, default=0)
    max_speed_gbps = db.Column(db.Float, nullable=False)
    stacking_support = db.Column(db.Boolean, default=False)
    port_types = db.Column(db.String(200))  # JSON string
    connector_types = db.Column(db.String(200))  # JSON string
    price = db.Column(db.Float)
    availability = db.Column(db.String(50))
    
    def to_dict(self):
        return {
            'id': self.id,
            'brand': self.brand,
            'model': self.model,
            'port_count': self.port_count,
            'poe_ports': self.poe_ports,
            'poe_plus_ports': self.poe_plus_ports,
            'poe_plus_plus_ports': self.poe_plus_plus_ports,
            'total_poe_watts': self.total_poe_watts,
            'sfp_ports': self.sfp_ports,
            'max_speed_gbps': self.max_speed_gbps,
            'stacking_support': self.stacking_support,
            'port_types': json.loads(self.port_types) if self.port_types else [],
            'connector_types': json.loads(self.connector_types) if self.connector_types else [],
            'price': self.price,
            'availability': self.availability
        }

class VLANConfiguration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    switch_id = db.Column(db.Integer, db.ForeignKey('switch.id'), nullable=False)
    vlan_count = db.Column(db.Integer, nullable=False)
    vlan_types = db.Column(db.String(500))  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SyncHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sync_type = db.Column(db.String(50), nullable=False)  # 'notion', 'distributors', 'full'
    status = db.Column(db.String(20), nullable=False)  # 'success', 'failed', 'partial'
    items_updated = db.Column(db.Integer, default=0)
    items_added = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    sync_duration = db.Column(db.Float)  # in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'sync_type': self.sync_type,
            'status': self.status,
            'items_updated': self.items_updated,
            'items_added': self.items_added,
            'error_message': self.error_message,
            'sync_duration': self.sync_duration,
            'created_at': self.created_at.isoformat()
        }

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/switches/search', methods=['POST'])
def search_switches():
    data = request.get_json()
    
    # Build query based on requirements
    query = Switch.query
    
    if data.get('port_count'):
        query = query.filter(Switch.port_count >= data['port_count'])
    
    if data.get('poe_requirements'):
        poe_req = data['poe_requirements']
        if poe_req.get('poe_ports'):
            query = query.filter(Switch.poe_ports >= poe_req['poe_ports'])
        if poe_req.get('poe_plus_ports'):
            query = query.filter(Switch.poe_plus_ports >= poe_req['poe_plus_ports'])
        if poe_req.get('poe_plus_plus_ports'):
            query = query.filter(Switch.poe_plus_plus_ports >= poe_req['poe_plus_plus_ports'])
        if poe_req.get('total_watts'):
            query = query.filter(Switch.total_poe_watts >= poe_req['total_watts'])
    
    if data.get('sfp_ports'):
        query = query.filter(Switch.sfp_ports >= data['sfp_ports'])
    
    if data.get('min_speed_gbps'):
        query = query.filter(Switch.max_speed_gbps >= data['min_speed_gbps'])
    
    if data.get('stacking_required'):
        query = query.filter(Switch.stacking_support == True)
    
    if data.get('brands'):
        query = query.filter(Switch.brand.in_(data['brands']))
    
    switches = query.all()
    return jsonify([switch.to_dict() for switch in switches])

# Distributor API Integration Functions
def check_ingram_micro_availability(part_number):
    """
    Check availability with Ingram Micro API
    Requires API key and authentication
    """
    # Configuration - add these to environment variables
    ingram_api_key = os.getenv('INGRAM_API_KEY')
    ingram_api_secret = os.getenv('INGRAM_API_SECRET')
    
    if not ingram_api_key or not ingram_api_secret:
        return {'error': 'Ingram Micro API credentials not configured'}
    
    # Ingram Micro API endpoint for product availability
    url = f"https://api.ingrammicro.com/sandbox/resellers/v6/catalog/priceandavailability"
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'IM-CustomerNumber': os.getenv('INGRAM_CUSTOMER_NUMBER'),
        'IM-CountryCode': 'US',
        'IM-CorrelationID': 'switch-lookup-001',
        'Authorization': f'Bearer {ingram_api_key}'
    }
    
    payload = {
        'products': [{'ingramPartNumber': part_number}]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get('products'):
                product = data['products'][0]
                return {
                    'available': product.get('availability', {}).get('available', False),
                    'quantity': product.get('availability', {}).get('totalAvailability', 0),
                    'price': product.get('pricing', {}).get('retailPrice', None)
                }
        return {'error': f'API call failed with status {response.status_code}'}
    except requests.RequestException as e:
        return {'error': f'Request failed: {str(e)}'}

def check_td_synnex_availability(part_number):
    """
    Check availability with TD SYNNEX API
    Requires API access and authentication
    """
    synnex_api_key = os.getenv('SYNNEX_API_KEY')
    synnex_api_secret = os.getenv('SYNNEX_API_SECRET')
    
    if not synnex_api_key or not synnex_api_secret:
        return {'error': 'TD SYNNEX API credentials not configured'}
    
    # TD SYNNEX StreamOne Ion API endpoint
    url = "https://api.tdsynnex.com/ion/v3/products/search"
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Basic {synnex_api_key}'
    }
    
    payload = {
        'manufacturerPartNumber': part_number,
        'includeAvailability': True,
        'includePricing': True
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get('products'):
                product = data['products'][0]
                return {
                    'available': product.get('availability', {}).get('isAvailable', False),
                    'quantity': product.get('availability', {}).get('quantity', 0),
                    'price': product.get('pricing', {}).get('customerPrice', None)
                }
        return {'error': f'API call failed with status {response.status_code}'}
    except requests.RequestException as e:
        return {'error': f'Request failed: {str(e)}'}

@app.route('/api/distributors/availability', methods=['POST'])
def check_availability():
    data = request.get_json()
    switch_ids = data.get('switch_ids', [])
    
    availability_data = {}
    
    for switch_id in switch_ids:
        switch = Switch.query.get(switch_id)
        if switch:
            # Create a manufacturer part number for API calls
            part_number = f"{switch.brand}-{switch.model}"
            
            # Check availability with distributors
            ingram_result = check_ingram_micro_availability(part_number)
            synnex_result = check_td_synnex_availability(part_number)
            
            availability_data[switch_id] = {
                'ingram_micro': ingram_result,
                'td_synnex': synnex_result,
                # Mock data for demonstration if APIs not configured
                'mock_data': {
                    'available': True,
                    'quantity': 25,
                    'price': switch.price * 0.85 if switch.price else None
                }
            }
    
    return jsonify(availability_data)

def update_switch_pricing(switch, distributor_data):
    """
    Update switch pricing from distributor data
    """
    updated = False
    
    # Update pricing from distributor APIs
    for distributor, data in distributor_data.items():
        if not data.get('error') and data.get('price'):
            # Use the lowest price or most recent price
            if not switch.price or data['price'] < switch.price:
                switch.price = data['price']
                updated = True
            
            # Update availability status
            if data.get('available'):
                switch.availability = 'In Stock'
                updated = True
            elif data.get('quantity', 0) == 0:
                switch.availability = 'Out of Stock'
                updated = True
    
    return updated

@app.route('/api/sync/full', methods=['POST'])
def full_sync():
    """
    Full sync: Update from Notion + refresh pricing from distributors
    """
    import time
    start_time = time.time()
    
    try:
        # Sync from Notion
        notion_result = sync_notion_data_internal()
        
        # Update pricing from distributors
        distributor_result = sync_distributor_pricing()
        
        # Calculate totals
        total_added = notion_result['added'] + distributor_result['added']
        total_updated = notion_result['updated'] + distributor_result['updated']
        
        # Log sync history
        duration = time.time() - start_time
        sync_log = SyncHistory(
            sync_type='full',
            status='success',
            items_added=total_added,
            items_updated=total_updated,
            sync_duration=duration
        )
        db.session.add(sync_log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Full sync completed: {total_added} added, {total_updated} updated',
            'notion_result': notion_result,
            'distributor_result': distributor_result,
            'duration': duration
        })
        
    except Exception as e:
        duration = time.time() - start_time
        sync_log = SyncHistory(
            sync_type='full',
            status='failed',
            error_message=str(e),
            sync_duration=duration
        )
        db.session.add(sync_log)
        db.session.commit()
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync/notion', methods=['POST'])
def sync_notion_data():
    """
    Manually sync data from Notion - useful for testing or manual updates
    """
    import time
    start_time = time.time()
    
    try:
        result = sync_notion_data_internal()
        
        # Log sync history
        duration = time.time() - start_time
        sync_log = SyncHistory(
            sync_type='notion',
            status='success',
            items_added=result['added'],
            items_updated=result['updated'],
            sync_duration=duration
        )
        db.session.add(sync_log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Notion sync completed: {result["added"]} added, {result["updated"]} updated',
            'duration': duration,
            **result
        })
        
    except Exception as e:
        duration = time.time() - start_time
        sync_log = SyncHistory(
            sync_type='notion',
            status='failed',
            error_message=str(e),
            sync_duration=duration
        )
        db.session.add(sync_log)
        db.session.commit()
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def sync_notion_data_internal():
    """
    Internal function to sync from Notion
    """
    notion_switches = load_notion_data()
    
    added_count = 0
    updated_count = 0
    
    for switch in notion_switches:
        existing = Switch.query.filter_by(brand=switch.brand, model=switch.model).first()
        
        if existing:
            # Update existing switch with new data from Notion
            updated = False
            if existing.port_count != switch.port_count:
                existing.port_count = switch.port_count
                updated = True
            if existing.poe_ports != switch.poe_ports:
                existing.poe_ports = switch.poe_ports
                updated = True
            if existing.total_poe_watts != switch.total_poe_watts:
                existing.total_poe_watts = switch.total_poe_watts
                updated = True
            if existing.sfp_ports != switch.sfp_ports:
                existing.sfp_ports = switch.sfp_ports
                updated = True
            if existing.max_speed_gbps != switch.max_speed_gbps:
                existing.max_speed_gbps = switch.max_speed_gbps
                updated = True
            if existing.stacking_support != switch.stacking_support:
                existing.stacking_support = switch.stacking_support
                updated = True
            if existing.port_types != switch.port_types:
                existing.port_types = switch.port_types
                updated = True
            if existing.connector_types != switch.connector_types:
                existing.connector_types = switch.connector_types
                updated = True
            if switch.price and existing.price != switch.price:
                existing.price = switch.price
                updated = True
                
            if updated:
                updated_count += 1
        else:
            # Add new switch
            db.session.add(switch)
            added_count += 1
    
    db.session.commit()
    
    return {
        'added': added_count,
        'updated': updated_count,
        'total_switches': len(notion_switches)
    }

@app.route('/api/sync/distributors', methods=['POST'])
def sync_distributor_pricing():
    """
    Update pricing from all distributors for existing switches
    """
    import time
    start_time = time.time()
    
    try:
        result = sync_distributor_pricing_internal()
        
        # Log sync history
        duration = time.time() - start_time
        sync_log = SyncHistory(
            sync_type='distributors',
            status='success',
            items_updated=result['updated'],
            sync_duration=duration
        )
        db.session.add(sync_log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Distributor sync completed: {result["updated"]} switches updated',
            'duration': duration,
            **result
        })
        
    except Exception as e:
        duration = time.time() - start_time
        sync_log = SyncHistory(
            sync_type='distributors',
            status='failed',
            error_message=str(e),
            sync_duration=duration
        )
        db.session.add(sync_log)
        db.session.commit()
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def sync_distributor_pricing_internal():
    """
    Internal function to update pricing from distributors
    """
    switches = Switch.query.all()
    updated_count = 0
    
    for switch in switches:
        part_number = f"{switch.brand}-{switch.model}"
        
        # Get current pricing from distributors
        ingram_result = check_ingram_micro_availability(part_number)
        synnex_result = check_td_synnex_availability(part_number)
        
        distributor_data = {
            'ingram_micro': ingram_result,
            'td_synnex': synnex_result
        }
        
        # Update switch with new pricing
        if update_switch_pricing(switch, distributor_data):
            updated_count += 1
    
    db.session.commit()
    
    return {
        'updated': updated_count,
        'total_switches': len(switches),
        'added': 0
    }

@app.route('/api/vlan/configure', methods=['POST'])
def configure_vlan():
    data = request.get_json()
    
    vlan_config = VLANConfiguration(
        switch_id=data['switch_id'],
        vlan_count=data['vlan_count'],
        vlan_types=json.dumps(data['vlan_types'])
    )
    
    db.session.add(vlan_config)
    db.session.commit()
    
    return jsonify({'success': True, 'config_id': vlan_config.id})

@app.route('/api/brands', methods=['GET'])
def get_brands():
    brands = db.session.query(Switch.brand).distinct().all()
    return jsonify([brand[0] for brand in brands])

@app.route('/api/sync/history', methods=['GET'])
def get_sync_history():
    """
    Get sync history for tracking changes
    """
    limit = request.args.get('limit', 10, type=int)
    history = SyncHistory.query.order_by(SyncHistory.created_at.desc()).limit(limit).all()
    return jsonify([record.to_dict() for record in history])

@app.route('/api/sync/status', methods=['GET'])
def get_sync_status():
    """
    Get current sync status and last sync times
    """
    last_full_sync = SyncHistory.query.filter_by(sync_type='full').order_by(SyncHistory.created_at.desc()).first()
    last_notion_sync = SyncHistory.query.filter_by(sync_type='notion').order_by(SyncHistory.created_at.desc()).first()
    last_distributor_sync = SyncHistory.query.filter_by(sync_type='distributors').order_by(SyncHistory.created_at.desc()).first()
    
    return jsonify({
        'last_full_sync': last_full_sync.to_dict() if last_full_sync else None,
        'last_notion_sync': last_notion_sync.to_dict() if last_notion_sync else None,
        'last_distributor_sync': last_distributor_sync.to_dict() if last_distributor_sync else None,
        'total_switches': Switch.query.count()
    })

# Initialize database
def create_tables():
    with app.app_context():
        db.create_all()
        seed_database()

def load_csv_data():
    csv_path = os.path.join(os.path.dirname(__file__), 'data', 'netgear_switches.csv')
    if not os.path.exists(csv_path):
        return []
    
    switches = []
    with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            switch = Switch(
                brand=row['brand'],
                model=row['model'],
                port_count=int(row['port_count']),
                poe_ports=int(row['poe_ports']),
                poe_plus_ports=int(row['poe_plus_ports']),
                poe_plus_plus_ports=int(row['poe_plus_plus_ports']),
                total_poe_watts=int(row['total_poe_watts']),
                sfp_ports=int(row['sfp_ports']),
                max_speed_gbps=float(row['max_speed_gbps']),
                stacking_support=row['stacking_support'].lower() == 'true',
                port_types=row['port_types'],
                connector_types=row['connector_types'],
                price=float(row['price']),
                availability=row['availability']
            )
            switches.append(switch)
    return switches

def load_notion_data():
    """
    Load switch data from Notion database/pages
    """
    notion_token = os.getenv('NOTION_TOKEN')
    if not notion_token:
        print("Notion token not configured, skipping Notion data load")
        return []
    
    notion = Client(auth=notion_token)
    switches = []
    
    try:
        # Get page ID from URL - extract from your Notion URL
        page_id = os.getenv('NOTION_PAGE_ID', '2771032fea0148d69e6bd585e21ba9c9')
        
        # If it's a database, use database query
        database_id = os.getenv('NOTION_DATABASE_ID')
        if database_id:
            response = notion.databases.query(database_id=database_id)
            
            for page in response.get('results', []):
                properties = page.get('properties', {})
                
                # Extract switch data from Notion properties
                # Adapt these field names to match your Notion database structure
                switch_data = {
                    'brand': get_notion_property(properties, 'Brand', 'NetGear'),
                    'model': get_notion_property(properties, 'Model', ''),
                    'port_count': get_notion_property(properties, 'Port Count', 0, 'number'),
                    'poe_ports': get_notion_property(properties, 'PoE Ports', 0, 'number'),
                    'poe_plus_ports': get_notion_property(properties, 'PoE+ Ports', 0, 'number'),
                    'poe_plus_plus_ports': get_notion_property(properties, 'PoE++ Ports', 0, 'number'),
                    'total_poe_watts': get_notion_property(properties, 'Total PoE Watts', 0, 'number'),
                    'sfp_ports': get_notion_property(properties, 'SFP Ports', 0, 'number'),
                    'max_speed_gbps': get_notion_property(properties, 'Max Speed (Gbps)', 1.0, 'number'),
                    'stacking_support': get_notion_property(properties, 'Stacking Support', False, 'checkbox'),
                    'port_types': json.dumps(get_notion_property(properties, 'Port Types', ['copper'], 'multi_select')),
                    'connector_types': json.dumps(get_notion_property(properties, 'Connector Types', ['RJ45'], 'multi_select')),
                    'price': get_notion_property(properties, 'Price', 0.0, 'number'),
                    'availability': get_notion_property(properties, 'Availability', 'Unknown')
                }
                
                if switch_data['model']:  # Only add if model exists
                    switch = Switch(**switch_data)
                    switches.append(switch)
        
        else:
            # Handle page content instead of database
            # This would require parsing the page content blocks
            print("Page-based parsing not implemented yet - use database format")
            
    except Exception as e:
        print(f"Error loading Notion data: {str(e)}")
        return []
    
    return switches

def get_notion_property(properties, prop_name, default_value, prop_type='title'):
    """
    Extract property value from Notion page properties
    """
    if prop_name not in properties:
        return default_value
    
    prop = properties[prop_name]
    
    if prop_type == 'title' and prop.get('title'):
        return prop['title'][0]['text']['content'] if prop['title'] else default_value
    elif prop_type == 'rich_text' and prop.get('rich_text'):
        return prop['rich_text'][0]['text']['content'] if prop['rich_text'] else default_value
    elif prop_type == 'number' and prop.get('number') is not None:
        return prop['number']
    elif prop_type == 'checkbox':
        return prop.get('checkbox', default_value)
    elif prop_type == 'select' and prop.get('select'):
        return prop['select']['name']
    elif prop_type == 'multi_select' and prop.get('multi_select'):
        return [item['name'] for item in prop['multi_select']]
    
    return default_value

def seed_database():
    # Check if data already exists
    if Switch.query.count() > 0:
        return
    
    # Load NetGear switches from CSV
    csv_switches = load_csv_data()
    
    # Load switches from Notion
    notion_switches = load_notion_data()
    
    # Additional sample switches from other brands
    other_switches = [
        # Cisco switches
        Switch(brand='Cisco', model='SG350-28', port_count=24, poe_ports=0, sfp_ports=4, 
               max_speed_gbps=1.0, stacking_support=True, port_types='["copper", "fiber"]', 
               connector_types='["RJ45", "SFP"]', price=699.99),
        Switch(brand='Cisco', model='SG350-28P', port_count=24, poe_ports=24, poe_plus_ports=24, 
               total_poe_watts=195, sfp_ports=4, max_speed_gbps=1.0, stacking_support=True, 
               port_types='["copper", "fiber"]', connector_types='["RJ45", "SFP"]', price=999.99),
        
        # HP switches
        Switch(brand='HP', model='1950-24G', port_count=24, poe_ports=0, sfp_ports=4, 
               max_speed_gbps=1.0, stacking_support=True, port_types='["copper", "fiber"]', 
               connector_types='["RJ45", "SFP"]', price=549.99),
        Switch(brand='HP', model='1950-48G-2SFP+', port_count=48, poe_ports=0, sfp_ports=2, 
               max_speed_gbps=10.0, stacking_support=True, port_types='["copper", "fiber"]', 
               connector_types='["RJ45", "SFP+"]', price=1299.99),
    ]
    
    # Add all switches to database
    for switch in csv_switches + notion_switches + other_switches:
        db.session.add(switch)
    
    db.session.commit()

if __name__ == '__main__':
    create_tables()
    app.run(host='0.0.0.0', port=5000, debug=True)