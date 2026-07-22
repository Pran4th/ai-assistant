from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from typing import Optional, List, Dict
from app.tools.base import BaseTool
import base64
from email.mime.text import MIMEText


class GmailTool(BaseTool):
    def __init__(self):
        self.service_name = "gmail"
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

    async def list_inbox(
        self,
        credentials: Dict,
        max_results: int = 10,
        query: Optional[str] = None,
    ) -> List[Dict]:
        service = self._get_service(credentials)
        params = {"userId": "me", "maxResults": min(max_results, 50)}
        if query:
            params["q"] = query

        result = service.users().messages().list(**params).execute()
        messages = result.get("messages", [])

        detailed = []
        for msg in messages[:max_results]:
            details = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["Subject", "From", "Date", "To"]
            ).execute()

            headers = {h["name"]: h["value"] for h in details.get("payload", {}).get("headers", [])}
            detailed.append({
                "id": msg["id"],
                "subject": headers.get("Subject", "(No subject)"),
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "date": headers.get("Date", ""),
                "snippet": details.get("snippet", ""),
            })

        return detailed

    async def send_email(
        self,
        credentials: Dict,
        to: str,
        subject: str,
        body: str,
    ) -> Dict:
        service = self._get_service(credentials)
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()

        sent = service.users().messages().send(
            userId="me", body={"raw": encoded}
        ).execute()

        return {"message_id": sent["id"], "status": "sent", "to": to, "subject": subject}

    async def search_emails(
        self,
        credentials: Dict,
        query: str,
        max_results: int = 10,
    ) -> List[Dict]:
        return await self.list_inbox(credentials, max_results=max_results, query=query)

    async def delete_email(
        self,
        credentials: Dict,
        message_id: str,
    ) -> Dict:
        service = self._get_service(credentials)
        service.users().messages().delete(userId="me", id=message_id).execute()
        return {"status": "deleted", "message_id": message_id}

    async def get_email(
        self,
        credentials: Dict,
        message_id: str,
    ) -> Dict:
        service = self._get_service(credentials)
        details = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in details.get("payload", {}).get("headers", [])}

        payload = details.get("payload", {})
        body_data = ""
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                    body_data = base64.urlsafe_b64decode(
                        part["body"]["data"].encode("ASCII")
                    ).decode("utf-8", errors="ignore")
                    break
        elif payload.get("body", {}).get("data"):
            body_data = base64.urlsafe_b64decode(
                payload["body"]["data"].encode("ASCII")
            ).decode("utf-8", errors="ignore")

        return {
            "id": details["id"],
            "subject": headers.get("Subject", "(No subject)"),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "body": body_data[:2000],
        }

    def is_ready(self) -> bool:
        return True
