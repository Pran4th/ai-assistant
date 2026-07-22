from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from typing import Optional, List, Dict
from app.tools.base import BaseTool


class ContactsTool(BaseTool):
    def __init__(self):
        self.service_name = "people"
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

    async def list_contacts(
        self,
        credentials: Dict,
        page_size: int = 20,
    ) -> List[Dict]:
        service = self._get_service(credentials)
        result = service.people().connections().list(
            resourceName="people/me",
            pageSize=page_size,
            personFields="names,emailAddresses,phoneNumbers,photos",
        ).execute()

        connections = result.get("connections", [])
        return [
            {
                "resource_name": p.get("resourceName", ""),
                "name": p.get("names", [{}])[0].get("displayName", "Unknown") if p.get("names") else "Unknown",
                "email": p.get("emailAddresses", [{}])[0].get("value", "") if p.get("emailAddresses") else "",
                "phone": p.get("phoneNumbers", [{}])[0].get("value", "") if p.get("phoneNumbers") else "",
                "photo": p.get("photos", [{}])[0].get("url", "") if p.get("photos") else "",
            }
            for p in connections
        ]

    async def search_contacts(
        self,
        credentials: Dict,
        query: str,
        page_size: int = 10,
    ) -> List[Dict]:
        service = self._get_service(credentials)
        result = service.people().searchContacts(
            query=query,
            pageSize=page_size,
            personFields="names,emailAddresses,phoneNumbers,photos",
        ).execute()

        results = result.get("results", [])
        return [
            {
                "resource_name": p.get("resourceName", ""),
                "name": p.get("names", [{}])[0].get("displayName", "Unknown") if p.get("names") else "Unknown",
                "email": p.get("emailAddresses", [{}])[0].get("value", "") if p.get("emailAddresses") else "",
                "phone": p.get("phoneNumbers", [{}])[0].get("value", "") if p.get("phoneNumbers") else "",
            }
            for r in results
            for p in [r.get("person", {})]
        ]

    async def create_contact(
        self,
        credentials: Dict,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Dict:
        service = self._get_service(credentials)
        body = {
            "names": [{"givenName": name}],
        }
        if email:
            body["emailAddresses"] = [{"value": email}]
        if phone:
            body["phoneNumbers"] = [{"value": phone}]

        result = service.people().createContact(body=body).execute()
        return {
            "resource_name": result.get("resourceName", ""),
            "name": result.get("names", [{}])[0].get("displayName", name),
        }

    def is_ready(self) -> bool:
        return True
