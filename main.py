from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
from app.core.database import engine, SessionLocal
from app.core.config import settings
from app.core.security import get_password_hash
from app import models
from app.api import auth, admin, employee_a, employee_b, queries


def init_db():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.Department).count() == 0:
            depts = [
                models.Department(name="技术部", description="技术研发部门"),
                models.Department(name="产品部", description="产品设计部门"),
                models.Department(name="市场部", description="市场营销部门"),
                models.Department(name="人力资源部", description="人力资源部门"),
                models.Department(name="财务部", description="财务部门"),
            ]
            db.add_all(depts)
            db.flush()
            dept_map = {d.name: d.id for d in depts}
        else:
            dept_map = {d.name: d.id for d in db.query(models.Department).all()}

        if db.query(models.Equipment).count() == 0:
            equips = [
                models.Equipment(name="投影仪", description="高清投影仪"),
                models.Equipment(name="白板", description="可擦写白板"),
                models.Equipment(name="视频会议系统", description="远程视频会议设备"),
                models.Equipment(name="麦克风", description="无线麦克风"),
                models.Equipment(name="显示器", description="大屏显示器"),
            ]
            db.add_all(equips)
            db.flush()
            equip_map = {e.name: e.id for e in equips}
        else:
            equip_map = {e.name: e.id for e in db.query(models.Equipment).all()}

        if db.query(models.MeetingRoom).count() == 0:
            rooms = [
                models.MeetingRoom(name="会议室A", capacity=10, location="3楼东侧", description="小型会议室"),
                models.MeetingRoom(name="会议室B", capacity=20, location="3楼西侧", description="中型会议室"),
                models.MeetingRoom(name="大会议室", capacity=50, location="5楼", description="大型多功能会议室"),
                models.MeetingRoom(name="培训室", capacity=30, location="2楼", description="培训专用室"),
            ]
            db.add_all(rooms)
            db.flush()
            room_equips = [
                models.RoomEquipment(room_id=rooms[0].id, equipment_id=equip_map["投影仪"], quantity=1),
                models.RoomEquipment(room_id=rooms[0].id, equipment_id=equip_map["白板"], quantity=1),
                models.RoomEquipment(room_id=rooms[1].id, equipment_id=equip_map["投影仪"], quantity=1),
                models.RoomEquipment(room_id=rooms[1].id, equipment_id=equip_map["白板"], quantity=1),
                models.RoomEquipment(room_id=rooms[1].id, equipment_id=equip_map["视频会议系统"], quantity=1),
                models.RoomEquipment(room_id=rooms[2].id, equipment_id=equip_map["投影仪"], quantity=2),
                models.RoomEquipment(room_id=rooms[2].id, equipment_id=equip_map["视频会议系统"], quantity=1),
                models.RoomEquipment(room_id=rooms[2].id, equipment_id=equip_map["麦克风"], quantity=4),
                models.RoomEquipment(room_id=rooms[3].id, equipment_id=equip_map["投影仪"], quantity=1),
                models.RoomEquipment(room_id=rooms[3].id, equipment_id=equip_map["显示器"], quantity=1),
            ]
            db.add_all(room_equips)

        if db.query(models.User).count() == 0:
            users = [
                models.User(
                    username="admin",
                    hashed_password=get_password_hash("admin123"),
                    full_name="系统管理员",
                    role="admin",
                    department_id=dept_map.get("技术部"),
                    is_active=True
                ),
                models.User(
                    username="employee_a",
                    hashed_password=get_password_hash("123456"),
                    full_name="张三（员工A）",
                    role="employee_a",
                    department_id=dept_map.get("技术部"),
                    is_active=True
                ),
                models.User(
                    username="employee_b",
                    hashed_password=get_password_hash("123456"),
                    full_name="李四（员工B）",
                    role="employee_b",
                    department_id=dept_map.get("人力资源部"),
                    is_active=True
                ),
            ]
            db.add_all(users)

        if db.query(models.BookingRule).count() == 0:
            default_rule = models.BookingRule(
                rule_name="默认预约规则",
                max_booking_days=30,
                min_booking_hours=0,
                max_booking_hours=8,
                require_approval=True,
                allow_weekend=False,
                start_time_limit="08:00",
                end_time_limit="20:00",
                max_attendees_per_room=None,
                description="系统默认预约规则",
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(default_rule)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"初始化数据时出错: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="会议室预约管理系统 API",
    description="公司会议室预约、参会部门、设备需求和临时占用管理系统",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(employee_a.router, prefix=settings.API_V1_STR)
app.include_router(employee_b.router, prefix=settings.API_V1_STR)
app.include_router(queries.router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "message": "会议室预约管理系统 API",
        "version": "1.0.0",
        "docs": "/docs",
        "api_prefix": settings.API_V1_STR
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8023, reload=True)
