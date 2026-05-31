from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)

# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///complaints.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
CORS(app)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    complaint_type = db.Column(db.String(50), nullable=False)
    custom_reason = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(500))
    upvotes = db.Column(db.Integer, default=0)

# HOME - Beautiful template
@app.route('/')
def home():
    return render_template('home.html')

# MAP PAGE
@app.route('/map')
def map_view():
    return render_template('map.html')

# API ROUTES
@app.route('/api/complaints')
def api_complaints():
    complaints = Complaint.query.all()
    return jsonify([{
        'id': c.id, 'lat': c.lat, 'lng': c.lng, 'complaint_type': c.complaint_type,
        'custom_reason': c.custom_reason, 'timestamp': c.timestamp.isoformat(),
        'description': c.description, 'upvotes': c.upvotes
    } for c in complaints])

@app.route('/report', methods=['POST'])
def report():
    data = request.json
    complaint = Complaint(
        lat=float(data['lat']), lng=float(data['lng']),
        complaint_type=data['complaint_type'], description=data['description']
    )
    db.session.add(complaint)
    db.session.commit()
    return jsonify({'id': complaint.id})

@app.route('/upvote/<int:complaint_id>', methods=['POST'])
def upvote(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    complaint.upvotes += 1
    db.session.commit()
    return jsonify({'upvotes': complaint.upvotes})

@app.route('/delete/<int:complaint_id>', methods=['POST'])
def delete_complaint(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    db.session.delete(complaint)
    db.session.commit()
    return jsonify({'status': 'deleted'})

# ADMIN DASHBOARD - Real stats
@app.route('/admin')
def admin_dashboard():
    total_complaints = Complaint.query.count()
    high_priority = Complaint.query.filter(Complaint.upvotes > 2).count()
    resolved_pct = (high_priority / total_complaints * 100) if total_complaints > 0 else 0
    latest_complaints = Complaint.query.order_by(Complaint.timestamp.desc()).limit(10).all()
    
    table_rows = ''.join(f'''
        <tr>
            <td><strong>{c.id}</strong></td>
            <td>({c.lat:.4f}, {c.lng:.4f})</td>
            <td><span class="badge bg-danger">{c.complaint_type}</span></td>
            <td>{c.description[:50]}{"..." if len(c.description) > 50 else ""}</td>
            <td><span class="badge bg-success">{c.upvotes}</span></td>
            <td>{c.timestamp.strftime("%H:%M %d/%m")}</td>
            <td><button class="btn btn-sm btn-danger" onclick="deleteComplaint({c.id})">Delete</button></td>
        </tr>''' for c in latest_complaints)
    
    return f'''
    <!DOCTYPE html>
    <html><head><title>Admin Dashboard - Blackout Map</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body{{background:linear-gradient(135deg,#0c0c2f 0%,#2d1b69 100%);color:white;font-family:Arial;}}
        .stat-card{{background:rgba(255,255,255,0.1);backdrop-filter:blur(15px);border-radius:20px;padding:30px;text-align:center;border:1px solid rgba(255,255,255,0.2);margin:15px 0;}}
        .stat-number{{font-size:3rem;font-weight:bold;color:#00d4ff;}}
        .table-dark th{{background:rgba(0,212,255,0.2);border:none;color:#00d4ff;font-weight:bold;}}
    </style></head>
    <body><div class="container mt-4">
        <h1 class="text-center mb-4">📊 Admin Dashboard</h1>
        <div class="row mb-5">
            <div class="col-md-4"><div class="stat-card"><h2 class="stat-number">{total_complaints}</h2><p>Total Complaints</p></div></div>
            <div class="col-md-4"><div class="stat-card"><h2 class="stat-number">{high_priority}</h2><p>High Priority</p></div></div>
            <div class="col-md-4"><div class="stat-card"><h2 class="stat-number">{resolved_pct:.0f}%</h2><p>Resolved Rate</p></div></div>
        </div>
        <h3>Latest 10 Complaints <span class="badge bg-light text-dark">Live</span></h3>
        <div class="table-responsive">
            <table class="table table-dark table-hover">
                <thead><tr><th>ID</th><th>Location</th><th>Type</th><th>Description</th><th>Upvotes</th><th>Time</th><th>Action</th></tr></thead>
                <tbody>{table_rows}</tbody>
            </table>
        </div>
        <div class="text-center mt-4">
            <a href="/" class="btn btn-primary btn-lg me-3">🏠 Home</a>
            <a href="/map" class="btn btn-info btn-lg">🗺️ Map</a>
        </div>
    </div>
    <script>
        async function deleteComplaint(id) {{
            if(confirm('Delete complaint #'+id+'?')) {{
                await fetch(`/delete/${{id}}`, {{method:'POST'}});
                location.reload();
            }}
        }}
    </script></body></html>'''

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
