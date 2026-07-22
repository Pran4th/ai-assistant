from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from typing import Optional, List, Dict


class TasksTool:
    def __init__(self):
        self.service_name = "tasks"
        self.version = "v1"

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

    async def create_task(
        self,
        title: str,
        credentials: Dict,
        due_date: Optional[str] = None,
        notes: Optional[str] = None,
        list_id: str = "@default",
    ) -> Dict:
        service = self._get_service(credentials)
        task_body = {"title": title}
        if due_date:
            task_body["due"] = due_date + "T00:00:00.000Z"
        if notes:
            task_body["notes"] = notes

        result = service.tasks().insert(tasklist=list_id, body=task_body).execute()
        return {
            "task_id": result["id"],
            "title": result["title"],
            "status": result.get("status", "needsAction"),
        }

    async def list_tasks(
        self,
        credentials: Dict,
        list_id: str = "@default",
        due_min: Optional[str] = None,
        due_max: Optional[str] = None,
        show_completed: bool = False,
    ) -> List[Dict]:
        service = self._get_service(credentials)
        params = {
            "tasklist": list_id,
            "showCompleted": show_completed,
            "showHidden": False,
        }
        if due_min:
            params["dueMin"] = due_min
        if due_max:
            params["dueMax"] = due_max

        result = service.tasks().list(**params).execute()
        tasks = result.get("items", [])

        return [
            {
                "id": t["id"],
                "title": t["title"],
                "due": t.get("due"),
                "status": t.get("status", "needsAction"),
                "notes": t.get("notes"),
            }
            for t in tasks
        ]

    async def update_task(
        self,
        task_id: str,
        credentials: Dict,
        **kwargs,
    ) -> Dict:
        service = self._get_service(credentials)
        task = service.tasks().get(tasklist="@default", task=task_id).execute()

        if "title" in kwargs:
            task["title"] = kwargs["title"]
        if "status" in kwargs:
            task["status"] = kwargs["status"]
        if "due_date" in kwargs:
            task["due"] = kwargs["due_date"] + "T00:00:00.000Z"
        if "notes" in kwargs:
            task["notes"] = kwargs["notes"]

        result = service.tasks().update(
            tasklist="@default", task=task_id, body=task
        ).execute()

        return {"task_id": result["id"], "status": "updated"}

    async def delete_task(
        self,
        task_id: str,
        credentials: Dict,
    ) -> Dict:
        service = self._get_service(credentials)
        service.tasks().delete(tasklist="@default", task=task_id).execute()
        return {"status": "deleted"}

    def is_ready(self) -> bool:
        return True
