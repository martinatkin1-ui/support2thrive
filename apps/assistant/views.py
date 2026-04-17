"""
apps/assistant/views.py
AI Assistant views.

assistant_page  — GET  — renders chat.html with session history
chat_view       — POST — validates, rate-limits, saves to session + DB, triggers SSE
assistant_stream — GET — SSE endpoint streaming LightRAG response

Session keys used:
  chat_history            — list of {"role": "user"/"assistant", "content": "..."}
  pending_assistant_message — the latest user message (read by assistant_stream)
  assistant_msg_count     — session budget counter (rate_limit.py)
  assistant_msg_times     — per-minute timestamp list (rate_limit.py)

Security:
  - Input validated: max 500 chars, stripped
  - Rate limit checked before any processing
  - No PII logged (session key only in AssistantQuery)
  - GEMINI_API_KEY never exposed in response
"""
import asyncio
import html
import logging
import time

from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from apps.assistant.crisis import build_crisis_prefix
from apps.assistant.models import AssistantQuery, Conversation, ConversationMessage
from apps.assistant.rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

MAX_QUERY_LENGTH = 500
HISTORY_CAP = 20  # 10 exchanges (user + assistant = 2 items per turn)


def _get_or_create_conversation(request) -> "Conversation":
    """Get or create a Conversation record for the current session."""
    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key
    conversation, _ = Conversation.objects.get_or_create(session_key=session_key)
    return conversation


def _cap_history(history: list) -> list:
    """Cap chat history at HISTORY_CAP items, removing oldest pairs first."""
    while len(history) > HISTORY_CAP:
        history.pop(0)
    return history


def assistant_page(request):
    """GET /assistant/ — render the chat interface."""
    history = request.session.get("chat_history", [])
    return render(request, "assistant/chat.html", {
        "chat_history": history,
        "page_title": _("Community Assistant"),
    })


@require_http_methods(["POST"])
def chat_view(request):
    """
    POST /assistant/chat/ — process user message.
    Returns HTMX-friendly HTML fragment:
      - On rate limit: error banner (HTTP 200 — HTMX requires 200 for swap)
      - On success: user message bubble HTML + triggers SSE connection setup
    """
    user_message = request.POST.get("message", "").strip()[:MAX_QUERY_LENGTH]

    if not user_message:
        return HttpResponse(
            '<div class="text-sm text-slate-500 italic px-4 py-2">Please enter a message.</div>',
            status=200,
            content_type="text/html",
        )

    # Rate limit check — before any processing
    allowed, error_msg = check_rate_limit(request)
    if not allowed:
        return HttpResponse(
            f'<div class="rounded-xl p-3 bg-amber-50 border border-amber-200 text-amber-800 text-sm font-body">'
            f'{html.escape(error_msg)}</div>',
            status=200,
            content_type="text/html",
        )

    # Store message in session for SSE endpoint to pick up
    request.session["pending_assistant_message"] = user_message

    # Append to session history
    history = request.session.get("chat_history", [])
    history.append({"role": "user", "content": user_message})
    history = _cap_history(history)
    request.session["chat_history"] = history
    request.session.modified = True

    # Save to DB for admin visibility + rate-limit audit
    try:
        conversation = _get_or_create_conversation(request)
        ConversationMessage.objects.create(
            conversation=conversation,
            role=ConversationMessage.ROLE_USER,
            content=user_message,
            crisis_detected=bool(build_crisis_prefix(user_message)),
        )
    except Exception:
        logger.exception("Failed to save ConversationMessage to DB (non-fatal)")

    # Return user message bubble + typing indicator
    # JS in chat.html detects data-start-stream and opens a native EventSource
    safe_message = html.escape(user_message)
    stream_path = html.escape(reverse("assistant:stream"))
    return HttpResponse(
        f'<div class="flex justify-end mb-3">'
        f'  <div class="max-w-[80%] bg-blue-800 text-white rounded-2xl rounded-br-sm px-4 py-2.5 font-body text-sm leading-relaxed">'
        f'    {safe_message}'
        f'  </div>'
        f'</div>'
        f'<div id="assistant-typing" data-start-stream="1" data-stream-url="{stream_path}"'
        f'     class="flex justify-start mb-3">'
        f'  <div class="bg-slate-50 border border-slate-200 rounded-2xl rounded-bl-sm px-4 py-3">'
        f'    <span class="flex gap-1 items-center" aria-label="Assistant is typing">'
        f'      <span class="inline-block w-2 h-2 bg-slate-400 rounded-full typing-dot"></span>'
        f'      <span class="inline-block w-2 h-2 bg-slate-400 rounded-full typing-dot" style="animation-delay:.2s"></span>'
        f'      <span class="inline-block w-2 h-2 bg-slate-400 rounded-full typing-dot" style="animation-delay:.4s"></span>'
        f'    </span>'
        f'  </div>'
        f'</div>',
        status=200,
        content_type="text/html",
    )


def assistant_stream(request):
    """
    GET /assistant/stream/ — SSE endpoint.
    Streams LightRAG response chunk-by-chunk to the browser.
    Crisis prefix streamed first if keywords detected.
    Closes with 'event: done' sentinel.

    PRODUCTION NOTE (RESEARCH.md A3): gunicorn WSGI buffers SSE.
    For production: use uvicorn ASGI worker or set --worker-class=gthread.
    X-Accel-Buffering: no header instructs nginx not to buffer.
    """
    from apps.assistant.rag_service import get_rag_instance

    message = request.session.get("pending_assistant_message", "")
    history = request.session.get("chat_history", [])

    if not message:
        def empty_stream():
            yield "data: No message found.\n\n"
            yield "event: done\ndata: \n\n"
        response = StreamingHttpResponse(streaming_content=empty_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    crisis_prefix = build_crisis_prefix(message)
    # Exclude the current user message from history passed to LightRAG (not yet answered)
    convo_history = list(history[:-1])[-20:]

    def event_stream():
        start_time = time.time()
        full_response = []

        # Stream crisis prefix first if applicable
        if crisis_prefix:
            # Send crisis prefix as a single SSE message (escape newlines in SSE data field)
            escaped = crisis_prefix.replace("\n", "\\n")
            yield f"data: {escaped}\n\n"
            full_response.append(crisis_prefix)

        # Bridge async LightRAG query into sync generator
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        rag_succeeded = False
        try:
            from lightrag import QueryParam

            async def _get_stream():
                # 5-second timeout: if pgvector/postgres isn't running this returns
                # quickly instead of hanging for minutes on a TCP timeout
                rag = await asyncio.wait_for(get_rag_instance(), timeout=5.0)
                param = QueryParam(
                    mode="mix",
                    stream=True,
                    conversation_history=convo_history,
                    response_type="Single Paragraph",
                )
                return await rag.lightrag.aquery(message, param=param)

            response_iter = loop.run_until_complete(_get_stream())

            # Iterate async generator from sync context; timeout each chunk so a
            # stalled query doesn't hang the browser indefinitely.
            async def _next_chunk(agen):
                try:
                    return await asyncio.wait_for(agen.__anext__(), timeout=15.0), False
                except StopAsyncIteration:
                    return None, True
                except asyncio.TimeoutError:
                    return None, True  # treat as end of stream

            while True:
                chunk, done = loop.run_until_complete(_next_chunk(response_iter))
                if done:
                    break
                if chunk:
                    full_response.append(chunk)
                    safe_chunk = str(chunk).replace("\n", "\\n").replace("\r", "")
                    yield f"data: {safe_chunk}\n\n"

            # Only mark success if LightRAG actually returned content.
            # An empty result (nothing indexed yet) falls through to Gemini.
            if "".join(full_response):
                rag_succeeded = True
            else:
                logger.warning("assistant_stream: LightRAG returned empty response, falling back to Gemini")

        except Exception:
            logger.warning("assistant_stream: LightRAG unavailable, falling back to Gemini direct")

        # Gemini direct fallback — active when LightRAG is unavailable or returned nothing.
        if not rag_succeeded:
            try:
                import google.generativeai as genai
                from django.conf import settings as django_settings

                api_key = django_settings.GEMINI_API_KEY
                if not api_key:
                    raise ValueError("GEMINI_API_KEY not configured")

                genai.configure(api_key=api_key)
                gemini_model = genai.GenerativeModel(
                    model_name="gemini-2.5-flash",
                    system_instruction=(
                        "You are a helpful, warm community assistant for Support2Thrive. "
                        "Help users find local services: housing, benefits, food banks, mental health "
                        "support, substance recovery, and community resources across the West Midlands. "
                        "FORMATTING RULES — follow these exactly: "
                        "Write in plain English only. No markdown. No asterisks, hashes, underscores, or backticks. "
                        "Do not bold, italicise, or use any special formatting characters. "
                        "For lists, write each item on its own line starting with a number and full stop (1. 2. 3.) or a bullet point (•). "
                        "Keep responses concise: 2 to 4 sentences or a short numbered list. "
                        "Always name the organisation and include a phone number or website. "
                        "Tell users to verify details directly with organisations before acting. "
                        "If someone is in crisis or danger, always mention Samaritans (116 123) and 999."
                    ),
                )
                gemini_history = [
                    {
                        "role": "user" if m.get("role") == "user" else "model",
                        "parts": [m.get("content", "")],
                    }
                    for m in convo_history
                ]

                async def _gemini_query():
                    chat = gemini_model.start_chat(history=gemini_history)
                    return await chat.send_message_async(message)

                gemini_resp = loop.run_until_complete(_gemini_query())
                answer = gemini_resp.text
                full_response.append(answer)
                safe_answer = answer.replace("\n", "\\n").replace("\r", "")
                yield f"data: {safe_answer}\n\n"

            except ValueError as exc:
                logger.warning("Gemini direct: %s", exc)
                yield (
                    "data: The AI assistant needs a GEMINI_API_KEY — "
                    "add it to your .env file and restart the server.\\n\n\n"
                )
            except Exception:
                logger.exception("assistant_stream: Gemini direct fallback failed")
                yield "data: I wasn't able to get a response right now. Please try again in a moment.\\n\n\n"

        loop.close()

        # Send done sentinel
        yield "event: done\ndata: \n\n"

        # Save assistant response to session + DB
        response_time_ms = int((time.time() - start_time) * 1000)
        full_text = "".join(full_response)

        history_list = request.session.get("chat_history", [])
        history_list.append({"role": "assistant", "content": full_text})
        history_list = _cap_history(history_list)
        request.session["chat_history"] = history_list
        request.session.modified = True

        # Save to AssistantQuery for monitoring (no PII — session key only)
        try:
            if request.session.session_key:
                AssistantQuery.objects.create(
                    session_key=request.session.session_key,
                    query_text=message[:500],
                    response_text=full_text[:2000],
                    response_time_ms=response_time_ms,
                )
        except Exception:
            logger.exception("Failed to save AssistantQuery (non-fatal)")

        # Save assistant ConversationMessage to DB
        try:
            conversation = _get_or_create_conversation(request)
            ConversationMessage.objects.create(
                conversation=conversation,
                role=ConversationMessage.ROLE_ASSISTANT,
                content=full_text,
            )
        except Exception:
            logger.exception("Failed to save assistant ConversationMessage (non-fatal)")

    response = StreamingHttpResponse(
        streaming_content=event_stream(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
