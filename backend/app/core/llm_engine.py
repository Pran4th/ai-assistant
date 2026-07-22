import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from app.config import settings
from app.models.schemas import UserProfile
from app.core.intent_router import IntentRouter


@dataclass
class LLMResult:
    response: str
    action: Optional[str]
    data: Optional[Dict]
    follow_up_needed: bool
    clarification_question: Optional[str]
    suggestions: List[str]


class LLMEngine:
    def __init__(self):
        self.has_openai = bool(settings.OPENAI_API_KEY)
        self.has_groq = bool(settings.GROQ_API_KEY)
        self.provider = "offline"
        self.intent_router = IntentRouter()
        self.tools_schema = self._build_tools_schema()

        if self.has_openai:
            import openai
            self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = "gpt-4-turbo-preview"
            self.provider = "openai"
        elif self.has_groq:
            import openai
            self.client = openai.AsyncOpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
            )
            self.model = "llama-3.3-70b-versatile"
            self.provider = "groq"

    def _build_tools_schema(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "calendar_create_event",
                    "description": "Create a new calendar event",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string", "description": "Event title"},
                            "start_time": {"type": "string", "format": "date-time"},
                            "end_time": {"type": "string", "format": "date-time"},
                            "attendees": {"type": "array", "items": {"type": "string"}},
                            "description": {"type": "string"},
                            "location": {"type": "string"},
                        },
                        "required": ["summary", "start_time", "end_time"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calendar_update_event",
                    "description": "Update an existing calendar event",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_id": {"type": "string"},
                            "summary": {"type": "string"},
                            "start_time": {"type": "string"},
                            "end_time": {"type": "string"},
                            "attendees": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["event_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calendar_delete_event",
                    "description": "Delete a calendar event",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_id": {"type": "string"},
                            "query": {"type": "string", "description": "Search query if event_id unknown"},
                        },
                        "required": ["event_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calendar_list_events",
                    "description": "List calendar events in a date range",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string", "format": "date"},
                            "end_date": {"type": "string", "format": "date"},
                            "query": {"type": "string"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "tasks_create",
                    "description": "Create a new task",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "due_date": {"type": "string", "format": "date"},
                            "notes": {"type": "string"},
                            "list_id": {"type": "string"},
                        },
                        "required": ["title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "tasks_update",
                    "description": "Update a task",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string"},
                            "title": {"type": "string"},
                            "due_date": {"type": "string"},
                            "status": {"type": "string", "enum": ["needsAction", "completed"]},
                            "notes": {"type": "string"},
                        },
                        "required": ["task_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "tasks_delete",
                    "description": "Delete a task",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string"},
                            "query": {"type": "string"},
                        },
                        "required": ["task_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "tasks_list",
                    "description": "List tasks",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "list_id": {"type": "string"},
                            "due_min": {"type": "string", "format": "date"},
                            "due_max": {"type": "string", "format": "date"},
                            "show_completed": {"type": "boolean"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "gmail_list_inbox",
                    "description": "List recent emails in inbox",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_results": {"type": "integer", "description": "Number of emails to fetch (max 50)"},
                            "query": {"type": "string", "description": "Search filter (e.g. 'from:john', 'subject:report')"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "gmail_send_email",
                    "description": "Send an email",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Recipient email address"},
                            "subject": {"type": "string", "description": "Email subject"},
                            "body": {"type": "string", "description": "Email body text"},
                        },
                        "required": ["to", "subject", "body"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "gmail_search_emails",
                    "description": "Search emails with a query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Gmail search query"},
                            "max_results": {"type": "integer"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "contacts_list",
                    "description": "List all contacts",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "page_size": {"type": "integer"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "contacts_search",
                    "description": "Search contacts by name or email",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "contacts_create",
                    "description": "Create a new contact",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                            "phone": {"type": "string"},
                        },
                        "required": ["name"],
                    },
                },
            },
        ]

    async def process_command(
        self,
        message: str,
        context: List[Dict],
        user: UserProfile,
        tools: List,
    ) -> LLMResult:
        if self.provider in ("openai", "groq"):
            return await self._process_with_llm(message, context, user, tools)
        return await self._process_offline(message, context, user, tools)

    async def _process_with_llm(
        self,
        message: str,
        context: List[Dict],
        user: UserProfile,
        tools: List,
    ) -> LLMResult:
        system_prompt = self._build_system_prompt(user)
        messages = [
            {"role": "system", "content": system_prompt},
            *context,
            {"role": "user", "content": message},
        ]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tools_schema,
            tool_choice="auto",
            temperature=0.2,
        )

        message_obj = response.choices[0].message

        if message_obj.tool_calls:
            return await self._handle_tool_calls(message_obj.tool_calls, messages, tools, user)

        return await self._process_offline(message, context, user, tools)

    async def _process_offline(
        self,
        message: str,
        context: List[Dict],
        user: UserProfile,
        tools: List,
    ) -> LLMResult:
        intent = self.intent_router.classify(message, context)

        if intent.intent == "greeting":
            return LLMResult(
                response=f"Hello {user.name}! I can help you with Calendar, Tasks, Gmail, and Contacts. What would you like to do?",
                action=None, data=None, follow_up_needed=False, clarification_question=None,
                suggestions=["Show my events today", "Show my inbox", "Add a task", "Search contacts"],
            )

        if intent.intent == "help":
            return LLMResult(
                response="""I can help you with Google Workspace:

**Calendar**: Create, list, update, delete events
**Tasks**: Create, list, update, delete tasks
**Gmail**: View inbox, search emails, send emails
**Contacts**: List, search, create contacts

Try: "Show my events today", "What's in my inbox?", "Send an email to John", "Find a contact named Sarah"
""",
                action=None, data=None, follow_up_needed=False, clarification_question=None,
                suggestions=["Show my events today", "What's in my inbox?", "List my contacts", "Add a task"],
            )

        if intent.requires_clarification:
            return LLMResult(
                response=intent.clarification_question,
                action=None, data=None, follow_up_needed=True,
                clarification_question=intent.clarification_question, suggestions=[],
            )

        tool_map = {
            "calendar_create_event": (tools[0].create_event, self._format_event_created),
            "calendar_update_event": (tools[0].update_event, self._format_event_updated),
            "calendar_delete_event": (tools[0].delete_event, self._format_event_deleted),
            "calendar_list_events": (tools[0].list_events, self._format_events_list),
            "tasks_create": (tools[1].create_task, self._format_task_created),
            "tasks_update": (tools[1].update_task, self._format_task_updated),
            "tasks_delete": (tools[1].delete_task, self._format_task_deleted),
            "tasks_list": (tools[1].list_tasks, self._format_tasks_list),
            "gmail_list_inbox": (tools[2].list_inbox, self._format_emails_list),
            "gmail_send_email": (tools[2].send_email, self._format_email_sent),
            "gmail_search_emails": (tools[2].search_emails, self._format_emails_list),
            "contacts_list": (tools[3].list_contacts, self._format_contacts_list),
            "contacts_search": (tools[3].search_contacts, self._format_contacts_list),
            "contacts_create": (tools[3].create_contact, self._format_contact_created),
        }

        if intent.intent in tool_map:
            func, formatter = tool_map[intent.intent]
            try:
                args = {**intent.entities, "credentials": user.credentials}
                result = await func(**args)
                response = formatter(result)
                return LLMResult(
                    response=response, action=intent.intent, data=result,
                    follow_up_needed=False, clarification_question=None,
                    suggestions=self._extract_suggestions(response),
                )
            except Exception as e:
                error_msg = str(e)
                if "invalid_grant" in error_msg or "token" in error_msg.lower():
                    hints = " Please try signing out and signing in again."
                elif "notFound" in error_msg:
                    hints = " The requested item was not found."
                elif "rate" in error_msg.lower():
                    hints = " Please wait a moment and try again."
                else:
                    hints = ""
                return LLMResult(
                    response=f"Sorry, I couldn't complete that: {error_msg.split('.')[-1]}{hints}",
                    action=intent.intent, data=None,
                    follow_up_needed=False, clarification_question=None, suggestions=[],
                )

        return LLMResult(
            response="I'm not sure how to help with that. I can manage your Calendar, Tasks, Gmail, and Contacts.",
            action=None, data=None, follow_up_needed=False, clarification_question=None,
            suggestions=["Show my events today", "What's in my inbox?", "List my contacts", "Add a task"],
        )

    async def _handle_tool_calls(
        self,
        tool_calls,
        messages: List[Dict],
        tools: List,
        user: UserProfile,
    ) -> LLMResult:
        tool_map = {
            "calendar_create_event": tools[0].create_event,
            "calendar_update_event": tools[0].update_event,
            "calendar_delete_event": tools[0].delete_event,
            "calendar_list_events": tools[0].list_events,
            "tasks_create": tools[1].create_task,
            "tasks_update": tools[1].update_task,
            "tasks_delete": tools[1].delete_task,
            "tasks_list": tools[1].list_tasks,
            "gmail_list_inbox": tools[2].list_inbox,
            "gmail_send_email": tools[2].send_email,
            "gmail_search_emails": tools[2].search_emails,
            "contacts_list": tools[3].list_contacts,
            "contacts_search": tools[3].search_contacts,
            "contacts_create": tools[3].create_contact,
        }

        results = []
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            if function_name in tool_map:
                try:
                    function_args["credentials"] = user.credentials
                    if "max_results" in function_args:
                        function_args["max_results"] = int(function_args["max_results"])
                    result = await tool_map[function_name](**function_args)
                    results.append({"tool": function_name, "status": "success", "data": result})
                except Exception as e:
                    results.append({"tool": function_name, "status": "error", "error": str(e)})
            else:
                results.append({"tool": function_name, "status": "error", "error": "Unknown tool"})

        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [tc.model_dump() for tc in tool_calls],
        })

        for result in results:
            messages.append({
                "role": "tool",
                "tool_call_id": tool_calls[0].id,
                "content": json.dumps(result),
            })

        final_response = await self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=0.7
        )

        content = final_response.choices[0].message.content

        return LLMResult(
            response=content,
            action=results[0]["tool"] if results else None,
            data=results[0].get("data") if results else None,
            follow_up_needed=False,
            clarification_question=None,
            suggestions=self._extract_suggestions(content),
        )

    def _build_system_prompt(self, user: UserProfile) -> str:
        current_time = datetime.now().isoformat()
        return f"""You are an AI Personal Assistant helping with Google Workspace.
Current time: {current_time}
User: {user.name} ({user.email})

Your capabilities:
- Manage Google Calendar (create, update, delete, list events)
- Manage Google Tasks (create, update, delete, list tasks)
- Manage Gmail (list inbox, search emails, send emails)
- Manage Google Contacts (list, search, create contacts)

Guidelines:
1. Always confirm before destructive operations (delete, update)
2. Ask for clarification if request is ambiguous
3. If user asks about "my inbox", use gmail_list_inbox
4. If user wants to email someone, use gmail_send_email
5. Handle relative dates (tomorrow, next Monday, etc.)
6. Be concise but friendly
7. Handle errors gracefully and suggest alternatives
8. If multiple items match, ask user to specify"""

    def _extract_suggestions(self, content: str) -> List[str]:
        suggestions = []
        c = content.lower()
        if "meeting" in c or "event" in c:
            suggestions.append("Would you like to add attendees?")
        if "task" in c:
            suggestions.append("Would you like to set a due date?")
        if "email" in c or "inbox" in c:
            suggestions.append("Would you like to reply?")
        if "contact" in c:
            suggestions.append("Would you like to add an email or phone number?")
        return suggestions

    def _format_event_created(self, data: dict) -> str:
        return f"Created event \"{data.get('summary', 'Untitled')}\" successfully!"

    def _format_event_updated(self, data: dict) -> str:
        return "Event updated successfully."

    def _format_event_deleted(self, data: dict) -> str:
        return "Event deleted successfully."

    def _format_events_list(self, data: list) -> str:
        if not data:
            return "No events found in that time range."
        lines = ["Here are your events:"]
        for e in data:
            start = e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "Unknown"))
            lines.append(f"- {e.get('summary', 'Untitled')} at {start}")
        return "\n".join(lines)

    def _format_task_created(self, data: dict) -> str:
        return f"Task \"{data.get('title', 'Untitled')}\" created successfully!"

    def _format_task_updated(self, data: dict) -> str:
        return "Task updated successfully."

    def _format_task_deleted(self, data: dict) -> str:
        return "Task deleted successfully."

    def _format_tasks_list(self, data: list) -> str:
        if not data:
            return "No tasks found."
        lines = ["Here are your tasks:"]
        for t in data:
            status = "✓" if t.get("status") == "completed" else "○"
            due = f" due: {t.get('due', 'No due date')}" if t.get("due") else ""
            lines.append(f"{status} {t.get('title', 'Untitled')}{due}")
        return "\n".join(lines)

    def _format_emails_list(self, data: list) -> str:
        if not data:
            return "No emails found."
        lines = ["Here are your emails:"]
        for e in data:
            lines.append(f"- From: {e.get('from', 'Unknown')} | Subject: {e.get('subject', '(No subject)')} | {e.get('date', '')}")
        return "\n".join(lines)

    def _format_email_sent(self, data: dict) -> str:
        return f"Email sent to {data.get('to', 'recipient')} with subject \"{data.get('subject', '')}\""

    def _format_contacts_list(self, data: list) -> str:
        if not data:
            return "No contacts found."
        lines = ["Here are your contacts:"]
        for c in data:
            email = f" ({c.get('email', '')})" if c.get("email") else ""
            phone = f" - {c.get('phone', '')}" if c.get("phone") else ""
            lines.append(f"- {c.get('name', 'Unknown')}{email}{phone}")
        return "\n".join(lines)

    def _format_contact_created(self, data: dict) -> str:
        return f"Contact \"{data.get('name', 'Unknown')}\" created successfully!"

    async def transcribe_audio(self, audio_base64: str) -> str:
        if not self.has_openai:
            return "Audio transcription requires an OpenAI API key."
        import openai, base64, tempfile, os
        audio_bytes = base64.b64decode(audio_base64)
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        with open(tmp_path, "rb") as audio_file:
            transcript = await self.client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        os.unlink(tmp_path)
        return transcript.text

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    def is_ready(self) -> bool:
        return True
