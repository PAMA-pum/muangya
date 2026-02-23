# นำเข้าไลบรารีที่จำเป็น
from flask import Flask, render_template, request, redirect, url_for, flash  # ฟังก์ชันพื้นฐานของ Flask
from flask_sqlalchemy import SQLAlchemy  # ORM สำหรับจัดการฐานข้อมูล (SQLAlchemy)
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user  # จัดการการล็อกอิน
from werkzeug.security import generate_password_hash, check_password_hash  # ฟังก์ชันเข้ารหัสรหัสผ่าน
from datetime import datetime  # ใช้เก็บ/จัดการวันที่-เวลา

# เริ่มต้นสร้างแอปพลิเคชัน Flask
app = Flask(__name__)  # สร้างแอป Flask

# กำหนดคอนฟิกพื้นฐาน
# `SECRET_KEY` ใช้สำหรับ session/flash และควรเก็บเป็นความลับ (ไม่ควรเป็นค่าเริ่มต้นแบบนี้ใน production)
app.config['SECRET_KEY'] = 'your-secret-key-here'
# กำหนดฐานข้อมูลเป็นไฟล์ SQLite ชื่อ database.db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # ปิดการติดตามการเปลี่ยนแปลงเพื่อประหยัดทรัพยากร

# สร้าง instance ของ SQLAlchemy และ LoginManager
db = SQLAlchemy(app)  # ใช้สร้าง model และจัดการ session กับฐานข้อมูล
login_manager = LoginManager()  # จัดการการล็อกอินและ session ของผู้ใช้
login_manager.init_app(app)
login_manager.login_view = 'login'  # กำหนดเส้นทางหน้า login เมื่อยังไม่ได้ล็อกอิน

# --------------------------------------------------------------------------------
# Models (โครงสร้างฐานข้อมูล)
# --------------------------------------------------------------------------------

# Model สำหรับผู้ใช้งาน (User)
class User(UserMixin, db.Model):
    # Model สำหรับเก็บข้อมูลผู้ใช้
    id = db.Column(db.Integer, primary_key=True)  # รหัสผู้ใช้ (Primary Key)
    username = db.Column(db.String(150), unique=True, nullable=False)  # ชื่อผู้ใช้ ต้องไม่ซ้ำ
    password = db.Column(db.String(150), nullable=False)  # รหัสผ่าน เก็บแบบ hashed
    is_admin = db.Column(db.Boolean, default=False)  # ถ้าเป็น True แปลว่าเป็นแอดมิน (สิทธิ์พิเศษ)

# Model สำหรับกิจกรรม (Activity)
class Activity(db.Model):
    # Model สำหรับเก็บข้อมูลกิจกรรม/อีเวนต์
    id = db.Column(db.Integer, primary_key=True)  # รหัสกิจกรรม
    title = db.Column(db.String(200), nullable=False)  # หัวข้อ/ชื่อกิจกรรม
    date = db.Column(db.String(100), nullable=False)  # วันที่ (เก็บเป็นสตริงตามต้นฉบับ)
    description = db.Column(db.Text, nullable=False)  # รายละเอียด
    location = db.Column(db.String(300), nullable=False)  # สถานที่จัด
    map_link = db.Column(db.String(500), nullable=False)  # ลิงก์แผนที่ (เช่น Google Maps)
    image = db.Column(db.String(500), nullable=False)  # เส้นทางหรือ URL รูปภาพ

    # ความสัมพันธ์ One-to-Many กับ Comment: Activity มีหลาย Comment
    comments = db.relationship('Comment', backref='activity', lazy=True)

# Model สำหรับความคิดเห็น (Comment)
class Comment(db.Model):
    # Model สำหรับเก็บความคิดเห็นของผู้ใช้ต่อกิจกรรม
    id = db.Column(db.Integer, primary_key=True)  # รหัสความคิดเห็น
    content = db.Column(db.Text, nullable=False)  # ข้อความความคิดเห็น
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # เวลาที่โพสต์
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # FK ไปยังตาราง user
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=False)  # FK ไปยัง activity

    # ความสัมพันธ์ Many-to-One กับ User: comment แต่ละอันมีผู้ใช้เป็นเจ้าของ
    user = db.relationship('User', backref=db.backref('comments', lazy=True))

# --------------------------------------------------------------------------------
# Admin Setup
# --------------------------------------------------------------------------------
def create_admin_user():
    # ฟังก์ชันตรวจสอบและสร้างผู้ใช้แอดมินเริ่มต้น
    # ถ้าไม่มีผู้ใช้ชื่อ 'pum' จะสร้างขึ้นพร้อมรหัสผ่าน 'Patthama' (hashed)
    admin_user = User.query.filter_by(username='pum').first()
    if not admin_user:
        hashed_password = generate_password_hash('Patthama', method='pbkdf2:sha256')  # เข้ารหัสรหัสผ่าน
        new_admin = User(username='pum', password=hashed_password, is_admin=True)
        db.session.add(new_admin)
        db.session.commit()
        print("Admin user created: username='pum', password='Patthama'")
    else:
        # ถ้าพบผู้ใช้ แต่ยังไม่ถูกตั้งเป็น admin ให้ตั้งค่านี้เพื่อให้มีสิทธิ์
        if not admin_user.is_admin:
            admin_user.is_admin = True
            db.session.commit()

# ฟังก์ชันสำหรับโหลดข้อมูลผู้ใช้จาก Session
@login_manager.user_loader
def load_user(user_id):
    # ใช้สำหรับโหลดข้อมูลผู้ใช้จาก session (Flask-Login จะเรียกฟังก์ชันนี้)
    return User.query.get(int(user_id))

# --------------------------------------------------------------------------------
# Seed Data (ข้อมูลเริ่มต้น)
# --------------------------------------------------------------------------------

# ข้อมูลกิจกรรมสำหรับเพิ่มลงฐานข้อมูลครั้งแรก
# activities_data_seed = [...] (code hidden for brevity as it was commented out in user's version)

def seed_activities():
    # ฟังก์ชันสำหรับเพิ่มข้อมูลกิจกรรมตัวอย่าง (seed)
    # ปัจจุบันยังไม่ได้เปิดใช้งาน เพราะ activities_data_seed ถูกคอมเมนต์ไว้
    if Activity.query.first() is None:
        pass

# สร้างตารางฐานข้อมูลทั้งหมดเมื่อเริ่มแอป
with app.app_context():
    # เมื่อรันแอป จะสร้างตารางฐานข้อมูล (ถ้ายังไม่มี) และเรียกฟังก์ชันเตรียมข้อมูล
    db.create_all()  # สร้างตารางตาม Model ที่นิยาม
    create_admin_user()  # สร้าง admin user หากยังไม่มี
    seed_activities()  # (ไม่ทำอะไรในสถานะปัจจุบัน) เพิ่มข้อมูลกิจกรรมตัวอย่าง

# --------------------------------------------------------------------------------
# Routes (เส้นทาง URL)
# --------------------------------------------------------------------------------

@app.route("/")
def hello_world():
    # เส้นทางหน้าแรกของเว็บ แสดง template index.html
    return render_template('index.html')

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
        # ถ้าผู้ใช้ยังไม่ได้ล็อกอิน ห้ามโพสต์ความคิดเห็น
        if not current_user.is_authenticated:
            flash('คุณต้องเข้าสู่ระบบก่อนแสดงความคิดเห็น', 'danger')
            return redirect(url_for('login'))

        # รับข้อความจากฟอร์มและบันทึกเป็น Comment ใหม่
        content = request.form.get('content')
        if content:
            comment = Comment(content=content, user_id=current_user.id, activity_id=activity.id)
            db.session.add(comment)
            db.session.commit()
            flash('ความคิดเห็นของคุณถูกบันทึกแล้ว', 'success')
            return redirect(url_for('activity_detail', activity_id=activity.id))

    # ดึงความคิดเห็นทั้งหมดของกิจกรรมนี้ เรียงจากใหม่ไปเก่า
    comments = Comment.query.filter_by(activity_id=activity.id).order_by(Comment.date_posted.desc()).all()
    return render_template('activity_detail.html', activity=activity, comments=comments)

    # ดึงความคิดเห็นทั้งหมดของกิจกรรมนี้ เรียงจากใหม่ไปเก่า
    comments = Comment.query.filter_by(activity_id=activity.id).order_by(Comment.date_posted.desc()).all()
    return render_template('activity_detail.html', activity=activity, comments=comments)

# --------------------------------------------------------------------------------
# Admin Routes
# --------------------------------------------------------------------------------

from functools import wraps  # ใช้สร้าง decorator
from flask import abort

# Decorator สำหรับตรวจสอบว่าเป็น Admin หรือไม่
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # ตรวจสอบสิทธิ์: ต้องล็อกอินและต้องเป็น admin เท่านั้น
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    # สำหรับหน้าแดชบอร์ดของแอดมิน ดึงข้อมูลทั้งหมดเพื่อบริหารจัดการ
    users = User.query.all()
    activities = Activity.query.all()
    comments = Comment.query.all()
    return render_template('admin_dashboard.html', users=users, activities=activities, comments=comments)

@app.route("/admin/user/delete/<int:user_id>")
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin: # ป้องกันการลบ Admin ด้วยกันเอง (หรือลบตัวเอง)
        flash('ไม่สามารถลบผู้ดูแลระบบได้', 'danger')
    else:
        # ลบความคิดเห็นของผู้ใช้นี้ก่อน เพื่อป้องกัน error (FK Constraint)
        # จริงๆ set cascade delete ได้ แต่ทำแบบ manual เพื่อความชัดเจน
        Comment.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        flash('ลบผู้ใช้เรียบร้อยแล้ว', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/activity/add", methods=['GET', 'POST'])
@login_required
@admin_required
def add_activity():
    if request.method == 'POST':
        title = request.form.get('title')
        date = request.form.get('date')
        description = request.form.get('description')
        location = request.form.get('location')
        map_link = request.form.get('map_link')
        image = request.form.get('image')

        # สร้าง Activity ใหม่จากข้อมูลฟอร์ม
        new_activity = Activity(
            title=title,
            date=date,
            description=description,
            location=location,
            map_link=map_link,
            image=image
        )
        db.session.add(new_activity)
        db.session.commit()
        flash('เพิ่มกิจกรรมใหม่เรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('activity_form.html', form_title="เพิ่มกิจกรรมใหม่")

@app.route("/admin/activity/edit/<int:activity_id>", methods=['GET', 'POST'])
@login_required
@admin_required
def edit_activity(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    if request.method == 'POST':
        # อัพเดตฟิลด์ของ Activity จากฟอร์มแล้วบันทึก
        activity.title = request.form.get('title')
        activity.date = request.form.get('date')
        activity.description = request.form.get('description')
        activity.location = request.form.get('location')
        activity.map_link = request.form.get('map_link')
        activity.image = request.form.get('image')

        db.session.commit()
        flash('แก้ไขกิจกรรมเรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('activity_form.html', activity=activity, form_title="แก้ไขกิจกรรม")

@app.route("/admin/activity/delete/<int:activity_id>")
@login_required
@admin_required
def delete_activity(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    # ลบความคิดเห็นที่เกี่ยวข้องก่อน
    Comment.query.filter_by(activity_id=activity.id).delete()
    db.session.delete(activity)
    db.session.commit()
    flash('ลบกิจกรรมเรียบร้อยแล้ว', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/comment/delete/<int:comment_id>")
@login_required
@admin_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    flash('ลบความคิดเห็นเรียบร้อยแล้ว', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # ค้นหาผู้ใช้จากฐานข้อมูล
        user = User.query.filter_by(username=username).first()
        
        # ตรวจสอบรหัสผ่าน
        if user and check_password_hash(user.password, password):
            login_user(user)  # บันทึกสถานะผู้ใช้ว่าเข้าสู่ระบบแล้ว (Flask-Login)
            # ถ้าเป็นแอดมิน ให้ไปแดชบอร์ดแอดมิน
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            # หากเป็นผู้ใช้ปกติ ให้กลับหน้าหลัก
            return redirect(url_for('hello_world'))
        else:
            flash('Login Failed. Please check username and password', 'danger')  # แจ้งเตือนเมื่อ username/รหัสผ่านไม่ถูกต้อง
            
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
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
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
    # ออกจากระบบโดยลบ session ของผู้ใช้
    logout_user()
    return redirect(url_for('login'))

if __name__ == "__main__":
    # รันเซิร์ฟเวอร์ Flask ในโหมด Debug (สำหรับการพัฒนา)
    app.run(debug=True)