from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
from typing import Optional, List, Dict


class CalendarTool:
    def __init__(self):
        self.service_name = "calendar"
        self.version = "v3"

    def _get_service(self, credentials: Dict):
        creds = Credentials(
            token=credentials["token"],
            refresh_token=credentials.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"],
            scopes=credentials["scopes"],
        )
        return build(self.service_name, self.version, credentials=creds)

    def _ensure_rfc3339(self, dt: str) -> str:
        if "T" not in dt:
            return f"{dt}T10:00:00Z"
        return dt if dt.endswith("Z") else dt + "Z"

    async def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        credentials: Dict,
        attendees: Optional[List[str]] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict:
        service = self._get_service(credentials)
        event_body = {
            "summary": summary,
            "start": {"dateTime": self._ensure_rfc3339(start_time), "timeZone": "UTC"},
            "end": {"dateTime": self._ensure_rfc3339(end_time), "timeZone": "UTC"},
        }
        if attendees:
            event_body["attendees"] = [{"email": e} for e in attendees]
        if description:
            event_body["description"] = description
        if location:
            event_body["location"] = location

        event = service.events().insert(calendarId="primary", body=event_body).execute()
        return {
            "event_id": event["id"],
            "html_link": event["htmlLink"],
            "summary": event["summary"],
        }

    async def list_events(
        self,
        credentials: Dict,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[Dict]:
        service = self._get_service(credentials)

        def _to_rfc3339(d: str, end: bool = False) -> str:
            if "T" in d:
                return d if d.endswith("Z") else d + "Z"
            return f"{d}T{'23:59:59Z' if end else '00:00:00Z'}"

        if not start_date:
            start_date = datetime.now().isoformat() + "Z"
        else:
            start_date = _to_rfc3339(start_date)
        if not end_date:
            end_date = (datetime.now() + timedelta(days=7)).isoformat() + "Z"
        else:
            end_date = _to_rfc3339(end_date, end=True)

        events_result = service.events().list(
            calendarId="primary",
            timeMin=start_date,
            timeMax=end_date,
            q=query,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = events_result.get("items", [])
        return [
            {
                "id": e["id"],
                "summary": e.get("summary", "No title"),
                "start": e["start"],
                "end": e["end"],
                "location": e.get("location"),
                "attendees": [a["email"] for a in e.get("attendees", [])],
            }
            for e in events
        ]

    async def update_event(
        self,
        event_id: str,
        credentials: Dict,
        **kwargs,
    ) -> Dict:
        service = self._get_service(credentials)
        event = service.events().get(calendarId="primary", eventId=event_id).execute()

        if "summary" in kwargs:
            event["summary"] = kwargs["summary"]
        if "start_time" in kwargs:
            event["start"]["dateTime"] = kwargs["start_time"]
        if "end_time" in kwargs:
            event["end"]["dateTime"] = kwargs["end_time"]
        if "attendees" in kwargs:
            event["attendees"] = [{"email": e} for e in kwargs["attendees"]]

        updated = service.events().update(
            calendarId="primary", eventId=event_id, body=event
        ).execute()

        return {"event_id": updated["id"], "status": "updated"}

    async def delete_event(
        self,
        event_id: str,
        credentials: Dict,
    ) -> Dict:
        service = self._get_service(credentials)
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return {"status": "deleted", "event_id": event_id}

    def is_ready(self) -> bool:
        return True
