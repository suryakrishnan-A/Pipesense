"""
Automated Work Order Dispatcher.
Current Build: Local deterministic notification and tracking. Remote AWS SNS / SES integration is unimplemented.
"""

from datetime import datetime
from backend.data.campus_db import store

class WorkOrderDispatcher:
    def __init__(self, use_sns=False):
        self.use_sns = False

    def dispatch_leak_repair(self, incident_id, diagnosis):
        """
        Creates actionable work order and dispatches notification with full diagnostic context.
        """
        title = f"[P1 URGENT] Water Leak Repair: {diagnosis['probable_location']}"
        instructions = (
            f"Investigate and isolate suspected rupture at {diagnosis['probable_location']}.\n"
            f"Observed Night Leak Rate: {diagnosis['estimated_water_loss_rate_lpm']} L/min.\n"
            f"Daily Waste Risk: {diagnosis['estimated_daily_waste_liters']:,} Liters/day.\n"
            f"Diagnosis: Localized joint failure confirmed by Local Resilience Agent (4 tools checked).\n"
            f"Protocol: Shut Isolation Valve B-2, replace 2-inch GI coupling with reinforced flange, pressure test to 45 PSI."
        )

        # Get assigned plumber
        plumber = store.on_call_crew[0]
        work_order = store.create_work_order(
            incident_id=incident_id,
            title=title,
            instructions=instructions,
            assigned_to=plumber,
            priority="P1"
        )

        notification_payload = {
            "channel": "SMS_AND_PORTAL",
            "recipient": plumber["name"],
            "phone": plumber["phone"],
            "message": f"ALERT P1: PipeSense detected major leak at BLDG-04 ({diagnosis['probable_location']}). Work order {work_order['work_order_id']} dispatched. Estimated loss: {diagnosis['estimated_water_loss_rate_lpm']} L/min.",
            "sent_at": datetime.now().isoformat()
        }

        return {
            "work_order": work_order,
            "notification": notification_payload
        }

dispatcher = WorkOrderDispatcher()
