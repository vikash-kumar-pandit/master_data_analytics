from datetime import datetime, timezone, timedelta
from database import SessionLocal
from models import UserActivity

ACTION_MAP = {
    "/upload": "upload",
    "/clean": "clean",
    "/arrange": "arrange",
    "/api/analytics/query": "question",
    "/api/analytics/forecast": "forecast",
    "/api/analytics/compare": "compare",
    "/api/analytics/report": "report",
    "/automl": "automl",
    "/api/clean-background": "clean_background",
    "/api/predict-background": "predict_background",
    "/generate-insights": "insights",
    "/api/export-results": "export",
    "/api/explain-automl": "explainability",
    "/api/run-clustering": "clustering",
    "/api/apply-nlp": "nlp",
    "/api/workflows": "workflow",
    "/api/catalog": "catalog",
}

def _infer_action(path: str) -> str:
    for prefix, action in ACTION_MAP.items():
        if path.startswith(prefix):
            return action
    return "other"


def track_activity(username: str, action: str, resource: str | None = None, metadata_info: dict = None):
    with SessionLocal() as db:
        activity = UserActivity(
            username=username,
            action=action,
            resource=resource,
            metadata_info=metadata_info or {}
        )
        db.add(activity)
        db.commit()


def record_activity(
    username: str | None,
    role: str | None,
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    client_ip: str,
):
    if method == "OPTIONS":
        return
    action = _infer_action(path)
    track_activity(
        username=username,
        action=action,
        resource=path,
        metadata_info={
            "method": method,
            "status_code": int(status_code),
            "duration_ms": int(duration_ms),
            "client_ip": client_ip,
        },
    )


def build_activity_summary(current_user: dict, days: int = 30, recent_limit: int = 20) -> dict:
    username = current_user.get("username")
    role = current_user.get("role")
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    with SessionLocal() as db:
        query = db.query(UserActivity).filter(UserActivity.timestamp >= cutoff_date)

        if role != "admin":
            query = query.filter(UserActivity.username == username)

        recent_activities = query.order_by(UserActivity.timestamp.desc()).limit(recent_limit).all()
        total_count = query.count()

        formatted_recent = [{
            "id": act.id,
            "action": act.action,
            "resource": act.resource,
            "username": act.username,
            "metadata_info": act.metadata_info,
            "timestamp": act.timestamp.isoformat() if act.timestamp else None
        } for act in recent_activities]

    return {
        "summary": {
            "total_actions_in_period": total_count,
            "days_analyzed": days
        },
        "recent_activity": formatted_recent
    }
