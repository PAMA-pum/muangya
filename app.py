from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# เริ่มต้นสร้างแอปพลิเคชัน Flask
app = Flask(__name__)

# ตั้งค่า Secret Key สำหรับความปลอดภัยของ Session (ควรเปลี่ยนเป็นคีย์ที่ซับซ้อนและเป็นความลับ)
app.config['SECRET_KEY'] = 'your-secret-key-here' 

# ตั้งค่าการเชื่อมต่อฐานข้อมูล SQLite ชื่อ 'database.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# เริ่มต้นใช้งาน SQLAlchemy และ LoginManager
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # กำหนดหน้า Login เริ่มต้นหากผู้ใช้ยังไม่ได้เข้าสู่ระบบ

# --------------------------------------------------------------------------------
# Models (โครงสร้างฐานข้อมูล)
# --------------------------------------------------------------------------------

# Model สำหรับผู้ใช้งาน (User)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True) # รหัสผู้ใช้ (Primary Key)
    username = db.Column(db.String(150), unique=True, nullable=False) # ชื่อผู้ใช้ (ต้องไม่ซ้ำ)
    password = db.Column(db.String(150), nullable=False) # รหัสผ่าน (เก็บแบบ Hashed)

# Model สำหรับกิจกรรม (Activity)
class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True) # รหัสกิจกรรม
    title = db.Column(db.String(200), nullable=False) # ชื่อกิจกรรม
    date = db.Column(db.String(100), nullable=False) # วันที่จัดกิจกรรม
    description = db.Column(db.Text, nullable=False) # รายละเอียดกิจกรรม
    location = db.Column(db.String(300), nullable=False) # สถานที่จัด
    map_link = db.Column(db.String(500), nullable=False) # ลิงก์แผนที่ (Google Maps)
    image = db.Column(db.String(500), nullable=False) # ลิงก์รูปภาพ

    # ความสัมพันธ์กับ Comment (One-to-Many): หนึ่งกิจกรรมมีหลายความคิดเห็น
    comments = db.relationship('Comment', backref='activity', lazy=True)

# Model สำหรับความคิดเห็น (Comment)
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True) # รหัสความคิดเห็น
    content = db.Column(db.Text, nullable=False) # เนื้อหาความคิดเห็น
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # วันที่และเวลาที่โพสต์
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # รหัสผู้ใช้ที่โพสต์ (Foreign Key)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=False) # รหัสกิจกรรมที่เกี่ยวข้อง (Foreign Key)

    # ความสัมพันธ์กับ User (Many-to-One): หลายความคิดเห็นมาจากผู้ใช้คนเดียว
    user = db.relationship('User', backref=db.backref('comments', lazy=True))

# ฟังก์ชันสำหรับโหลดข้อมูลผู้ใช้จาก Session
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --------------------------------------------------------------------------------
# Seed Data (ข้อมูลเริ่มต้น)
# --------------------------------------------------------------------------------

# ข้อมูลกิจกรรมสำหรับเพิ่มลงฐานข้อมูลครั้งแรก
# activities_data_seed = [...] (code hidden for brevity as it was commented out in user's version)

def seed_activities():
    # ตรวจสอบว่ามีข้อมูลในตาราง Activity หรือไม่
    if Activity.query.first() is None:
        # หากไม่มี ให้เพิ่มข้อมูลจาก activities_data_seed (จำเป็นต้องมีตัวแปรนี้ถ้าจะใช้)
        # หมายเหตุ: โค้ดส่วนนี้จะทำงานถ้ามีการ Uncomment ตัวแปร activities_data_seed ด้านบน
        pass 
        # for item in activities_data_seed:
        #     activity = Activity(...)
        #     db.session.add(activity)
        # db.session.commit()
        # print("Activities seeded!")

# สร้างตารางฐานข้อมูลทั้งหมดเมื่อเริ่มแอป
with app.app_context():
    db.create_all()
    seed_activities()

# --------------------------------------------------------------------------------
# Routes (เส้นทาง URL)
# --------------------------------------------------------------------------------

@app.route("/")
def hello_world():
    return render_template('index.html') # แสดงหน้าแรก

@app.route("/places")
def places():
    return render_template('places.html') # แสดงหน้าสถานที่น่าไป

@app.route("/shopping")
def shopping():
    return render_template('shopping.html') # แสดงหน้าแหล่งช้อปปิ้ง

@app.route("/restaurants")
def restaurants():
    return render_template('restaurants.html') # แสดงหน้าร้านอาหารแนะนำ

@app.route("/accommodation")
def accommodation():
    return render_template('accommodation.html') # แสดงหน้าที่พัก

@app.route("/government")
def government():
    return render_template('index.html') # ยังไม่มีหน้าเฉพาะ ให้กลับไปหน้าแรกก่อน

@app.route("/activities")
def activities():
    # ดึงข้อมูลกิจกรรมทั้งหมดจากฐานข้อมูล
    activities = Activity.query.all()
    return render_template('activities.html', activities=activities)

@app.route("/activity/<int:activity_id>", methods=['GET', 'POST'])
def activity_detail(activity_id):
    # ดึงข้อมูลกิจกรรมตาม ID หากไม่เจอให้แสดง 404
    activity = Activity.query.get_or_404(activity_id)

    # จัดการกรณีมีการส่งแบบฟอร์ม (POST request) คือการคอมเมนต์
    if request.method == 'POST':
        # ตรวจสอบว่าผู้ใช้ล็อกอินหรือยัง
        if not current_user.is_authenticated:
            flash('คุณต้องเข้าสู่ระบบก่อนแสดงความคิดเห็น', 'danger')
            return redirect(url_for('login'))
        
        # รับข้อมูลจากฟอร์ม
        content = request.form.get('content')
        if content:
            # สร้าง Comment ใหม่และบันทึกลงฐานข้อมูล
            comment = Comment(content=content, user_id=current_user.id, activity_id=activity.id)
            db.session.add(comment)
            db.session.commit()
            flash('ความคิดเห็นของคุณถูกบันทึกแล้ว', 'success')
            return redirect(url_for('activity_detail', activity_id=activity.id))

    # ดึงความคิดเห็นทั้งหมดของกิจกรรมนี้ เรียงจากใหม่ไปเก่า
    comments = Comment.query.filter_by(activity_id=activity.id).order_by(Comment.date_posted.desc()).all()
    return render_template('activity_detail.html', activity=activity, comments=comments)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # ค้นหาผู้ใช้จากฐานข้อมูล
        user = User.query.filter_by(username=username).first()
        
        # ตรวจสอบรหัสผ่าน
        if user and check_password_hash(user.password, password):
            login_user(user) # เข้าสู่ระบบสำเร็จ
            return redirect(url_for('hello_world'))
        else:
            flash('Login Failed. Please check username and password', 'danger') # แจ้งเตือนเมื่อผิดพลาด
            
    return render_template('login.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # ตรวจสอบว่ามีชื่อผู้ใช้นี้อยู่แล้วหรือไม่
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username already exists.', 'danger')
        else:
            # สร้างรหัสผ่านแบบ Hashed เพื่อความปลอดภัย
            hashed_password = generate_password_hash(password, method='scrypt')
            new_user = User(username=username, password=hashed_password)
            
            # บันทึกผู้ใช้ใหม่ลงฐานข้อมูล
            db.session.add(new_user)
            db.session.commit()
            
            flash('Account created!', 'success')
            return redirect(url_for('login'))
            
    return render_template('register.html')

@app.route("/logout")
@login_required # ต้องล็อกอินก่อนถึงจะกด Logout ได้
def logout():
    logout_user() # ออกจากระบบ
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True) # รันแอปในโหมด Debug