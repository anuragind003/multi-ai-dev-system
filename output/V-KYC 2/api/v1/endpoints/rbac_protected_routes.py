from fastapi import APIRouter, Depends, status
from models import User, UserRole
from auth_middleware import requires_team_lead, requires_process_manager, requires_any_vkyc_role
from utils.logger import logger

router = APIRouter(prefix="/data", tags=["Protected Data"])

@router.get("/team_lead_dashboard", summary="Access Team Lead Dashboard Data")
async def get_team_lead_dashboard_data(current_user: User = Depends(requires_team_lead)):
    """
    Endpoint accessible only by users with the 'Team Lead' role.
    Returns dummy data for a team lead dashboard.
    """
    logger.info(f"User {current_user.username} (Role: {current_user.role.name.value}) accessed Team Lead Dashboard.")
    return {
        "message": f"Welcome, Team Lead {current_user.username}! Here is your dashboard data.",
        "data": {
            "pending_reviews": 15,
            "team_performance": "Good",
            "recent_activities": ["User A reviewed VKYC-123", "User B uploaded VKYC-456"]
        }
    }

@router.get("/process_manager_reports", summary="Access Process Manager Reports")
async def get_process_manager_reports(current_user: User = Depends(requires_process_manager)):
    """
    Endpoint accessible only by users with the 'Process Manager' role.
    Returns dummy data for process manager reports.
    """
    logger.info(f"User {current_user.username} (Role: {current_user.role.name.value}) accessed Process Manager Reports.")
    return {
        "message": f"Hello, Process Manager {current_user.username}! Here are your process reports.",
        "data": {
            "overall_compliance": "98%",
            "audit_logs_count": 1200,
            "process_efficiency_score": 8.7
        }
    }

@router.get("/vkyc_recordings_list", summary="List VKYC Recordings (Any VKYC Role)")
async def list_vkyc_recordings(current_user: User = Depends(requires_any_vkyc_role)):
    """
    Endpoint accessible by any user with a VKYC role ('Team Lead' or 'Process Manager').
    Returns a dummy list of VKYC recording metadata.
    """
    logger.info(f"User {current_user.username} (Role: {current_user.role.name.value}) accessed VKYC Recordings List.")
    return {
        "message": f"Here are the VKYC recordings for {current_user.username}.",
        "recordings": [
            {"id": "VKYC-001", "lan_id": "LAN123", "date": "2023-01-15", "status": "Completed"},
            {"id": "VKYC-002", "lan_id": "LAN456", "date": "2023-01-16", "status": "Pending Review"},
            {"id": "VKYC-003", "lan_id": "LAN789", "date": "2023-01-17", "status": "Approved"}
        ]
    }

@router.get("/public_info", summary="Publicly Accessible Information")
async def get_public_info():
    """
    Endpoint accessible by anyone, no authentication required.
    """
    logger.info("Accessed public information endpoint.")
    return {"message": "This is publicly accessible information."}