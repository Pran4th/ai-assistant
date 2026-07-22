from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class IntentResult:
    intent: str
    confidence: float
    entities: Dict[str, Any]
    requires_clarification: bool
    clarification_question: Optional[str] = None


class IntentRouter:
    INTENTS = [
        "calendar_create_event", "calendar_update_event", "calendar_delete_event", "calendar_list_events",
        "tasks_create", "tasks_update", "tasks_delete", "tasks_list",
        "gmail_list_inbox", "gmail_send_email", "gmail_search_emails",
        "contacts_list", "contacts_search", "contacts_create",
        "general_query", "greeting", "help",
    ]

    def classify(self, message: str, context: list) -> IntentResult:
        message_lower = message.lower()
        entities = {}

        # ── Calendar Create ──
        if any(w in message_lower for w in ["create", "add", "new", "schedule", "set up"]):
            if any(w in message_lower for w in ["meeting", "event", "appointment", "calendar"]):
                entities = self._extract_calendar_entities(message_lower)
                return IntentResult("calendar_create_event", 0.9, entities,
                    self._needs_calendar_clarification(entities),
                    self._get_calendar_clarification(entities))

        # ── Tasks Create ──
        if any(w in message_lower for w in ["task", "todo", "to-do", "to do"]):
            if any(w in message_lower for w in ["add", "create", "new", "make"]):
                entities = self._extract_task_entities(message_lower)
                return IntentResult("tasks_create", 0.9, entities,
                    self._needs_task_clarification(entities),
                    self._get_task_clarification(entities))

        # ── List / View ──
        if any(w in message_lower for w in ["list", "show", "what", "upcoming", "agenda", "view"]):
            if any(w in message_lower for w in ["event", "meeting", "calendar", "schedule"]):
                return IntentResult("calendar_list_events", 0.85, self._extract_date_range(message_lower), False)
            if any(w in message_lower for w in ["task", "todo"]):
                return IntentResult("tasks_list", 0.85, {}, False)
            if any(w in message_lower for w in ["email", "mail", "inbox", "message"]):
                entities = self._extract_email_query(message_lower)
                return IntentResult("gmail_list_inbox", 0.85, entities, False)
            if any(w in message_lower for w in ["contact", "person", "people", "address book"]):
                return IntentResult("contacts_list", 0.85, {}, False)

        # ── Send Email ──
        if any(w in message_lower for w in ["send", "email", "mail", "compose"]):
            if any(w in message_lower for w in ["email", "mail", "message"]):
                entities = self._extract_email_entities(message_lower)
                return IntentResult("gmail_send_email", 0.85, entities,
                    "to" not in entities,
                    "Who would you like to send the email to?")

        # ── Search Email ──
        if any(w in message_lower for w in ["find", "search", "look for"]):
            if any(w in message_lower for w in ["email", "mail", "message", "inbox"]):
                entities = self._extract_email_query(message_lower)
                return IntentResult("gmail_search_emails", 0.85, entities, False)

        # ── Search Contacts ──
        if any(w in message_lower for w in ["find", "search", "look for"]):
            if any(w in message_lower for w in ["contact", "person", "people"]):
                return IntentResult("contacts_search", 0.85, {"query": message_lower.replace("find", "").replace("search", "").replace("contact", "").replace("person", "").strip()}, False)

        # ── Create Contact ──
        if any(w in message_lower for w in ["add", "create", "new", "save"]):
            if any(w in message_lower for w in ["contact", "person"]):
                entities = self._extract_contact_entities(message_lower)
                return IntentResult("contacts_create", 0.85, entities,
                    "name" not in entities,
                    "What is the contact's name?")

        # ── Delete ──
        if any(w in message_lower for w in ["delete", "remove", "cancel"]):
            if any(w in message_lower for w in ["event", "meeting", "appointment", "calendar"]):
                return IntentResult("calendar_delete_event", 0.8, {"query": message_lower}, True,
                    "Which event would you like to delete? Please provide the event name or details.")
            if any(w in message_lower for w in ["task", "todo"]):
                return IntentResult("tasks_delete", 0.8, {"query": message_lower}, True,
                    "Which task would you like to delete? Please provide the task name.")
            if any(w in message_lower for w in ["email", "mail", "message"]):
                return IntentResult("general_query", 0.5, {}, False)

        # ── Update ──
        if any(w in message_lower for w in ["update", "change", "modify", "reschedule", "edit"]):
            if any(w in message_lower for w in ["event", "meeting", "calendar"]):
                return IntentResult("calendar_update_event", 0.8, {"query": message_lower}, True,
                    "Which event would you like to update? Please provide details.")
            if any(w in message_lower for w in ["task", "todo"]):
                return IntentResult("tasks_update", 0.8, {"query": message_lower}, True,
                    "Which task would you like to update? Please provide the task name.")

        # ── Greeting ──
        if any(w in message_lower for w in ["hi", "hello", "hey", "good morning", "good evening"]):
            return IntentResult("greeting", 1.0, {}, False)

        # ── Help ──
        if any(w in message_lower for w in ["help", "what can you", "capabilities", "features"]):
            return IntentResult("help", 1.0, {}, False)

        # ── Context ──
        context_aware = self._check_context_for_intent(context)
        if context_aware:
            return context_aware

        return IntentResult("general_query", 0.5, {}, False)

    def _extract_calendar_entities(self, text: str) -> dict:
        entities = {}
        if "tomorrow" in text:
            from datetime import datetime, timedelta
            t = datetime.now() + timedelta(days=1)
            entities["start_time"] = t.replace(hour=10, minute=0).isoformat()
            entities["end_time"] = t.replace(hour=11, minute=0).isoformat()
        if "next week" in text:
            from datetime import datetime, timedelta
            t = datetime.now() + timedelta(weeks=1)
            entities["start_time"] = t.replace(hour=10, minute=0).isoformat()
            entities["end_time"] = t.replace(hour=11, minute=0).isoformat()
        return entities

    def _extract_task_entities(self, text: str) -> dict:
        entities = {}
        for prefix in ["task", "todo", "to-do"]:
            if prefix in text:
                idx = text.find(prefix) + len(prefix)
                rest = text[idx:].strip(" :callednamed")
                if rest:
                    entities["title"] = rest
                break
        if not entities.get("title"):
            for phrase in ["called", "named", "to", ":"]:
                if phrase in text:
                    idx = text.find(phrase) + len(phrase)
                    rest = text[idx:].strip()
                    if rest:
                        entities["title"] = rest
                    break
        return entities

    def _extract_date_range(self, text: str) -> dict:
        from datetime import datetime, timedelta
        if "today" in text:
            return {"start_date": datetime.now().strftime("%Y-%m-%d"), "end_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")}
        if "tomorrow" in text:
            t = datetime.now() + timedelta(days=1)
            return {"start_date": t.strftime("%Y-%m-%d"), "end_date": (t + timedelta(days=1)).strftime("%Y-%m-%d")}
        if "this week" in text:
            return {"start_date": datetime.now().strftime("%Y-%m-%d"), "end_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")}
        if "next week" in text:
            t = datetime.now() + timedelta(weeks=1)
            return {"start_date": t.strftime("%Y-%m-%d"), "end_date": (t + timedelta(days=7)).strftime("%Y-%m-%d")}
        return {}

    def _extract_email_query(self, text: str) -> dict:
        query = text.replace("show", "").replace("list", "").replace("view", "").replace("my", "").replace("emails", "").replace("mail", "").replace("inbox", "").replace("messages", "").strip()
        return {"query": query} if query else {}

    def _extract_email_entities(self, text: str) -> dict:
        entities = {}
        for phrase in ["to ", "subject "]:
            if phrase in text:
                idx = text.find(phrase) + len(phrase)
                rest = text[idx:].strip()
                if rest:
                    if phrase == "to ":
                        entities["to"] = rest.split(" subject")[0].strip()
                    elif phrase == "subject ":
                        entities["subject"] = rest
        if "say " in text or "body " in text:
            entities["body"] = text
        return entities

    def _extract_contact_entities(self, text: str) -> dict:
        entities = {}
        for phrase in ["named ", "called ", "name "]:
            if phrase in text:
                idx = text.find(phrase) + len(phrase)
                rest = text[idx:].strip()
                if rest:
                    entities["name"] = rest.split(" email")[0].split(" phone")[0].strip()
                    break
        parts = text.split()
        for i, w in enumerate(parts):
            if w == "email" and i + 1 < len(parts):
                entities["email"] = parts[i + 1].strip("@,. ")
            if w == "phone" and i + 1 < len(parts):
                entities["phone"] = parts[i + 1].strip("@,. ")
        return entities

    def _needs_calendar_clarification(self, entities: dict) -> bool:
        return "start_time" not in entities

    def _get_calendar_clarification(self, entities: dict) -> str:
        return "When would you like the event to take place?" if "start_time" not in entities else ""

    def _needs_task_clarification(self, entities: dict) -> bool:
        return "title" not in entities

    def _get_task_clarification(self, entities: dict) -> str:
        return "What task would you like to add?" if "title" not in entities else ""

    def _check_context_for_intent(self, context: list) -> Optional[IntentResult]:
        if not context:
            return None
        for msg in reversed(context):
            if msg.get("role") == "assistant":
                content = msg["content"].lower()
                if "which event" in content:
                    return IntentResult("context_response", 0.9, {"context_type": "event_selection"}, False)
                if "which task" in content:
                    return IntentResult("context_response", 0.9, {"context_type": "task_selection"}, False)
                if "who would you like" in content or "send the email" in content:
                    return IntentResult("context_response", 0.9, {"context_type": "email_recipient"}, False)
                if "contact's name" in content:
                    return IntentResult("context_response", 0.9, {"context_type": "contact_name"}, False)
                break
        return None
