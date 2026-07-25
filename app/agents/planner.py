import re
import base64
import json
import structlog
from typing import Optional
import openai
from openai import AsyncOpenAI
from sqlalchemy import select

from app.core.config import settings
from app.memory.session_store import session_store, PendingAction
from app.memory.redis_store import redis_store
from app.prompts.planner_prompt import PLANNER_SYSTEM_PROMPT
from app.db.session import AsyncSessionLocal
from app.db.models import Transaction, Customer

from app.tools.customer_tool import resolve_customer, get_customer_history, create_customer
from app.tools.ledger_tool import add_transaction, undo_last
from app.tools.report_tool import get_daily_report, get_monthly_report, get_outstanding_report
from app.tools.reminder_tool import propose_reminder
from app.tools.ocr_tool import extract_from_image

logger = structlog.get_logger()

# ── OpenAI / OpenRouter Function Declarations ─────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "resolve_customer",
            "description": "Find customer ID from raw name. Always call first before any transaction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name_raw": {"type": "string", "description": "Customer name as heard/typed"},
                    "context_hint": {"type": "string", "description": "Optional area/alias hint"},
                },
                "required": ["name_raw"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_customer",
            "description": "Create a new customer record when customer does not exist in database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Customer full name"},
                    "phone": {"type": "string", "description": "Optional phone number"},
                    "alias_notes": {"type": "string", "description": "Optional notes or area"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_transaction",
            "description": "Record a credit_given or payment_received transaction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "transaction_type": {
                        "type": "string",
                        "enum": ["credit_given", "payment_received"],
                    },
                    "amount": {"type": "number"},
                    "item_description": {"type": "string"},
                    "payment_mode": {
                        "type": "string",
                        "enum": ["Online", "Cash", "UPI", "Cheque"],
                        "description": "Payment mode if specified in user message (e.g. Online, UPI, Cash)",
                    },
                    "confidence": {"type": "number", "description": "0.0-1.0 extraction confidence"},
                },
                "required": ["customer_id", "transaction_type", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "undo_last",
            "description": "Reverse the most recent transaction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transaction_id": {"type": "string"},
                },
                "required": ["transaction_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_history",
            "description": "Get full transaction history and live outstanding balance for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_report",
            "description": "Get today's total credit and payment summary.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_monthly_report",
            "description": "Get this month's total credit and payment summary.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_outstanding_report",
            "description": "Get all customers with outstanding (unpaid) balances.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_reminder",
            "description": "Draft a payment reminder for papa's approval. NEVER sends without approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "outstanding_amount": {"type": "number"},
                    "days_overdue": {"type": "integer"},
                },
                "required": ["customer_id", "outstanding_amount", "days_overdue"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_from_image",
            "description": "Extract items and amounts from handwritten bill/list photo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_url": {"type": "string"},
                },
                "required": ["image_url"],
            },
        },
    },
]

UNDO_KEYWORDS = {"undo", "galat", "wapas", "cancel", "hatao", "delete"}
CORRECTION_KEYWORDS = {"actually", "galti", "real", "tha", "sirf"}
STRICT_CONFIRM_WORDS = {"yes", "haan", "hn", "han", "ok", "theek", "sahi", "bhejo", "confirm", "create", "add", "banao", "1", "2", "3"}
STRICT_DENY_WORDS = {"nahi", "na", "no", "mat", "ruko", "cancel"}
GREETING_PATTERNS = [
    r"^\s*(hello|hi|hey|good\s*morning|good\s*afternoon|good\s*evening)\b",
    r"\b(i\s*am|my\s*name\s*is|main|mein)\s+([a-zA-Z]+)",
]


def _format_debug_header(
    intent: str,
    customer: Optional[str] = None,
    amount: Optional[float] = None,
    mode: Optional[str] = None,
    tool: str = "LedgerService",
    confidence: str = "99%",
    is_greeting: bool = False,
) -> str:
    """Formats Developer Mode AI reasoning header when DEBUG_AI=true."""
    if not getattr(settings, "DEBUG_AI", False):
        return ""

    if is_greeting:
        cust_str = f"\nCustomer:\n{customer}\n" if customer else ""
        return (
            f"🧠 AI Planner Reasoning\n\n"
            f"Intent:\n{intent}\n"
            f"{cust_str}"
            f"Intent Category:\nGeneral Conversation\n\n"
            f"No business action required.\n\n"
            f"━━━━━━━━━━━━━━\n\n"
        )

    cust_line = f"\nCustomer:\n{customer}\n" if customer else ""
    amt_line = f"\nAmount:\n₹{amount:.0f}\n" if amount is not None else ""
    mode_line = f"\nPayment Mode:\n{mode}\n" if mode else ""

    return (
        f"🧠 AI Understanding\n\n"
        f"Intent:\n{intent}\n"
        f"{cust_line}"
        f"{amt_line}"
        f"{mode_line}"
        f"\nConfidence:\n{confidence}\n\n"
        f"━━━━━━━━━━━━━━\n\n"
    )


class PlannerAgent:
    """
    VyaparAI Planner Agent — powered by OpenRouter LLM API & Upstash Redis state.
    Tool-calling loop: message → OpenRouter API reasoning → tool calls → response refiner.
    """

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )
        self.model = settings.OPENROUTER_MODEL or "deepseek/deepseek-chat"

    async def process(
        self,
        sender: str,
        text: str,
        source: str = "text",
        image_url: Optional[str] = None,
    ) -> str:
        session = session_store.get(sender)
        session.add_turn("user", text)
        lower = text.lower().strip()
        words = set(re.findall(r"\w+", lower))

        # ── Fast-path for General Greetings & Introduction ─────────────────────
        is_greeting = any(re.search(pat, lower) for pat in GREETING_PATTERNS)
        has_business_kw = any(kw in lower for kw in ["udhaar", "de do", "diya", "payment", "jama", "rupees", "rs", "balance", "bill", "scan"])
        has_numbers = bool(re.search(r"\d+", lower))

        if is_greeting and not has_business_kw and not has_numbers:
            name_match = re.search(r"\b(?:i\s*am|my\s*name\s*is|main|mein)\s+([a-zA-Z]+)", text, re.IGNORECASE)
            cust_name = name_match.group(1).capitalize() if name_match else ""
            greeting_name = f", {cust_name}" if cust_name else ""

            debug_hdr = _format_debug_header(
                intent="General Greeting / Assistant Intro",
                customer=cust_name if cust_name else None,
                is_greeting=True,
            )

            assistant_reply = (
                f"{debug_hdr}👋 Nice to meet you{greeting_name}!\n\n"
                f"How can I help you today?\n\n"
                f"You can ask me things like:\n\n"
                f"• Record a payment\n"
                f"• Add a customer\n"
                f"• Check customer balance\n"
                f"• Scan a bill\n"
                f"• Create a reminder"
            )
            session.add_turn("assistant", assistant_reply)
            return assistant_reply

        # ── Fetch pending action from Redis ────────────────────────────────────
        redis_pending = await redis_store.get_pending_action(sender)
        local_pending = session.pending_action

        is_short_reply = len(lower) < 25
        has_digits_only = bool(re.match(r"^\d+$", lower))
        is_confirm_or_deny = bool(words & (STRICT_CONFIRM_WORDS | STRICT_DENY_WORDS))

        # ── Check if this message is a direct confirmation response to pending ──
        if (local_pending or redis_pending) and (is_short_reply or has_digits_only or is_confirm_or_deny):
            pending_data = redis_pending or (local_pending.payload if local_pending else None)
            action_type = redis_pending.get("action_type") if redis_pending else (local_pending.action_type if local_pending else None)
            if pending_data:
                return await self._handle_pending_confirmation(sender, text, session, action_type, pending_data)

        # Clear stale pending action if user sent a new instruction sentence
        if local_pending or redis_pending:
            session.clear_pending()
            await redis_store.clear_pending_action(sender)

        # ── Smart Correction Check (e.g. "actually 500" after undo) ─────────────
        undone = await redis_store.get_last_undone_context(sender) or session.last_undone_context
        if undone:
            digits = re.findall(r"\d+", lower)
            if digits and (any(kw in lower for kw in CORRECTION_KEYWORDS) or lower.startswith(digits[0])):
                corrected_amount = float(digits[0])
                session.last_undone_context = None
                await redis_store.clear_last_undone_context(sender)

                async with AsyncSessionLocal() as db:
                    result = await add_transaction(
                        db,
                        customer_id=undone["customer_id"],
                        transaction_type=undone["transaction_type"],
                        amount=corrected_amount,
                        source=source,
                        confidence=1.0,
                    )
                    session.last_transaction_id = result.get("transaction_id")
                    await redis_store.set_last_transaction_id(sender, result.get("transaction_id"))
                    header = "Payment Recorded" if undone["transaction_type"] == "payment_received" else "Credit Recorded"
                    debug_hdr = _format_debug_header(header, undone.get("customer_name", "Customer"), corrected_amount, result.get("payment_mode", "Cash"))
                    return (
                        f"{debug_hdr}Updating previous transaction...\n\n"
                        f"✅ {header}\n\n"
                        f"Customer: {undone.get('customer_name', 'Customer')}\n"
                        f"Amount: ₹{corrected_amount:.0f}\n\n"
                        f"Current Balance: ₹{result.get('new_balance', 0):.0f}\n\n"
                        f"Need to reverse it? Reply \"undo\"."
                    )

        # ── Undo shortcut ─────────────────────────────────────────────────────
        last_txn_id = await redis_store.get_last_transaction_id(sender) or session.last_transaction_id
        if any(kw in text.lower() for kw in UNDO_KEYWORDS) and last_txn_id:
            return await self._handle_undo(sender, session, last_txn_id)

        # ── Text length capping ───────────────────────────────────────────────
        if text and len(text) > 2000:
            logger.warning("text_truncated_for_llm", original_len=len(text))
            text = text[:2000]

        # ── OpenRouter LLM API Conversation Reasoning ─────────────────────────
        messages = [{"role": "system", "content": PLANNER_SYSTEM_PROMPT}]

        for turn in session.conversation_history[:-1]:
            role = "user" if turn["role"] == "user" else "assistant"
            messages.append({"role": role, "content": turn["content"]})

        if image_url and source == "ocr":
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": "Photo bheja hai — bill/list extract karo"},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            })
        else:
            messages.append({"role": "user", "content": text})

        try:
            reply = await self._tool_calling_loop(messages, sender, source, image_url, session)
            session.add_turn("assistant", reply)
            return reply
        except openai.RateLimitError as e:
            logger.error("openrouter_rate_limit", error=str(e))
            return "AI service is currently busy. Please try again in a moment."
        except openai.AuthenticationError as e:
            logger.error("openrouter_auth_failed", error=str(e))
            return "AI service authentication error. Please contact the administrator."
        except openai.APITimeoutError as e:
            logger.error("openrouter_timeout", error=str(e))
            return "I couldn't process that request in time. Please try again."
        except Exception as e:
            logger.error("openrouter_error", error=str(e))
            return "I couldn't process that request. Please try again in a moment."

    async def _tool_calling_loop(
        self, messages: list, sender: str, source: str,
        image_url: Optional[str], session
    ) -> str:
        MAX_ITERATIONS = 6
        active_model = (settings.OPENROUTER_VISION_MODEL or "openai/gpt-4o-mini") if image_url else self.model

        for _ in range(MAX_ITERATIONS):
            response = await self.client.chat.completions.create(
                model=active_model,
                messages=messages,
                tools=TOOLS,
                temperature=0.2,
            )

            message = response.choices[0].message

            if not message.tool_calls:
                return message.content or "Kuch samajh nahi aaya. Dobara likhiye."

            messages.append(message.model_dump())

            for tool_call in message.tool_calls:
                fn_name = tool_call.function.name
                try:
                    fn_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                except json.JSONDecodeError:
                    fn_args = {}

                logger.info("openrouter_tool_called", tool=fn_name, args=fn_args)

                tool_result = await self._execute_tool(fn_name, fn_args, sender, source, image_url, session)

                # Catch CustomerNotFound exception and stage pending creation with PRESERVED transaction details
                if isinstance(tool_result, dict) and "No customer found" in tool_result.get("error", ""):
                    cust_name = fn_args.get("name_raw", "Customer")
                    amt = 0.0
                    ttype = "credit_given"
                    pmode = "Cash"

                    if message.tool_calls:
                        for tc in message.tool_calls:
                            if tc.function.name == "add_transaction":
                                try:
                                    tc_args = json.loads(tc.function.arguments)
                                    amt = float(tc_args.get("amount", 0))
                                    ttype = tc_args.get("transaction_type", "credit_given")
                                    pmode = tc_args.get("payment_mode", "Cash")
                                except Exception:
                                    pass

                    first_user_turn = next((t["content"] for t in session.conversation_history if t["role"] == "user"), "")
                    if amt <= 0:
                        digits = re.findall(r"\d+", first_user_turn)
                        if digits:
                            amt = float(digits[0])

                    if any(kw in first_user_turn.lower() for kw in ["bhej", "payment", "jama", "online", "diya", "paid", "phonpe", "paytm"]):
                        ttype = "payment_received"
                    if any(kw in first_user_turn.lower() for kw in ["online", "upi", "phonpe", "paytm"]):
                        pmode = "Online"

                    pending_data = {
                        "action_type": "create_customer_and_transaction",
                        "customer": {"name": cust_name},
                        "transaction": {
                            "amount": amt if amt > 0 else 100.0,
                            "transaction_type": ttype,
                            "payment_mode": pmode
                        },
                    }

                    logger.info("staging_pending_customer_creation", sender=sender, pending_data=pending_data)
                    session.set_pending(PendingAction(
                        action_type="create_customer_and_transaction",
                        payload=pending_data,
                        draft_message=f"Create customer {cust_name}?",
                    ))
                    await redis_store.set_pending_action(sender, pending_data)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result),
                })

        return "I couldn't process that request. Please try again in a moment."

    async def _execute_tool(
        self, tool_name: str, args: dict,
        sender: str, source: str, image_url: Optional[str], session
    ) -> dict:
        async with AsyncSessionLocal() as db:
            try:
                if tool_name == "resolve_customer":
                    return await resolve_customer(db, **args)

                elif tool_name == "create_customer":
                    return await create_customer(db, **args)

                elif tool_name == "add_transaction":
                    args.setdefault("source", source)
                    args.setdefault("confidence", 1.0)

                    # Dynamic extraction fallback if amount is missing or zero
                    if float(args.get("amount", 0)) <= 0:
                        user_text = session.conversation_history[-1]["content"] if session.conversation_history else ""
                        digits = re.findall(r"\d+", user_text)
                        if digits:
                            args["amount"] = float(digits[0])
                        else:
                            args["amount"] = 100.0

                        if any(kw in user_text.lower() for kw in ["bhej", "paid", "payment", "jama", "phonpe", "paytm", "online"]):
                            args["transaction_type"] = "payment_received"
                            args["payment_mode"] = "Online"

                    result = await add_transaction(db, **args)
                    if result.get("status") == "confirmed":
                        session.last_transaction_id = result["transaction_id"]
                        await redis_store.set_last_transaction_id(sender, result["transaction_id"])
                    return result

                elif tool_name == "undo_last":
                    result = await undo_last(db, args["transaction_id"])
                    session.last_transaction_id = None
                    await redis_store.set_last_transaction_id(sender, None)
                    return result

                elif tool_name == "get_customer_history":
                    return await get_customer_history(db, **args)

                elif tool_name == "get_daily_report":
                    return await get_daily_report(db)

                elif tool_name == "get_monthly_report":
                    return await get_monthly_report(db)

                elif tool_name == "get_outstanding_report":
                    return await get_outstanding_report(db)

                elif tool_name == "propose_reminder":
                    result = await propose_reminder(db, **args)
                    return result

                elif tool_name == "extract_from_image":
                    return await extract_from_image(db, image_url or args.get("image_url", ""))

                else:
                    return {"error": f"Unknown tool: {tool_name}"}

            except ValueError as e:
                logger.warning("tool_error", tool=tool_name, error=str(e))
                return {"error": str(e)}
            except Exception as e:
                logger.error("tool_exception", tool=tool_name, error=str(e))
                return {"error": "Database error — dobara try kijiye"}

    async def _handle_pending_confirmation(
        self, sender: str, text: str, session,
        action_type: str, pending_data: dict
    ) -> str:
        lower = text.lower().strip()
        words = set(re.findall(r"\w+", lower))

        logger.info(
            "retrieved_pending_state_before_replay",
            sender=sender,
            action_type=action_type,
            pending_data=pending_data,
        )

        if action_type == "select_customer_candidate":
            digits = re.findall(r"\d+", lower)
            candidates = pending_data.get("candidates", [])
            if digits:
                idx = int(digits[0]) - 1
                if 0 <= idx < len(candidates):
                    selected = candidates[idx]
                    async with AsyncSessionLocal() as db:
                        txn_payload = pending_data.get("transaction", {})
                        txn_payload["customer_id"] = selected["customer_id"]
                        txn_payload["confidence"] = 1.0
                        result = await add_transaction(db, **txn_payload)
                        session.last_transaction_id = result.get("transaction_id")
                        await redis_store.set_last_transaction_id(sender, result.get("transaction_id"))
                        
                        session.clear_pending()
                        await redis_store.clear_pending_action(sender)

                        is_payment = txn_payload.get("transaction_type") == "payment_received"
                        header = "Payment Recorded" if is_payment else "Credit Recorded"
                        mode = result.get("payment_mode", "Cash")
                        debug_hdr = _format_debug_header(header, selected['name'], txn_payload.get('amount', 0), mode)
                        return (
                            f"{debug_hdr}✅ {header}\n\n"
                            f"Customer: {selected['name']}\n"
                            f"Amount: ₹{txn_payload.get('amount', 0):.0f}\n"
                            f"Mode: {mode}\n\n"
                            f"Current Balance: ₹{result.get('new_balance', 0):.0f}\n\n"
                            f"Need to reverse it? Reply \"undo\"."
                        )

        is_confirm = bool(words & STRICT_CONFIRM_WORDS)
        is_deny = bool(words & STRICT_DENY_WORDS)

        if is_confirm and not is_deny:
            if action_type == "add_transaction":
                async with AsyncSessionLocal() as db:
                    payload = {**pending_data.get("payload", pending_data), "confidence": 1.0}
                    result = await add_transaction(db, **payload)
                    session.last_transaction_id = result.get("transaction_id")
                    await redis_store.set_last_transaction_id(sender, result.get("transaction_id"))
                    
                    session.clear_pending()
                    await redis_store.clear_pending_action(sender)

                    is_payment = payload.get("transaction_type") == "payment_received"
                    header = "Payment Recorded" if is_payment else "Credit Recorded"
                    mode = result.get("payment_mode", "Cash")
                    debug_hdr = _format_debug_header(header, "Customer", payload.get('amount', 0), mode)
                    return (
                        f"{debug_hdr}✅ {header}\n\n"
                        f"Amount: ₹{payload.get('amount', 0):.0f}\n"
                        f"Mode: {mode}\n\n"
                        f"Current Balance: ₹{result.get('new_balance', 0):.0f}\n\n"
                        f"Need to reverse it? Reply \"undo\"."
                    )

            elif action_type == "create_customer_and_transaction":
                async with AsyncSessionLocal() as db:
                    c_payload = pending_data.get("customer", {})
                    t_payload = pending_data.get("transaction", {})
                    cust_name = c_payload.get("name", "New Customer")
                    
                    cust = await create_customer(db, name=cust_name)
                    
                    target_amt = float(t_payload.get("amount", 200.0))
                    target_ttype = t_payload.get("transaction_type", "payment_received")
                    target_pmode = t_payload.get("payment_mode", "Online")

                    replay_payload = {
                        "customer_id": cust["customer_id"],
                        "transaction_type": target_ttype,
                        "amount": target_amt,
                        "payment_mode": target_pmode,
                        "confidence": 1.0,
                    }

                    logger.info("replaying_transaction_after_customer_creation", replay_payload=replay_payload)
                    result = await add_transaction(db, **replay_payload)
                    
                    session.last_transaction_id = result.get("transaction_id")
                    await redis_store.set_last_transaction_id(sender, result.get("transaction_id"))
                    
                    session.clear_pending()
                    await redis_store.clear_pending_action(sender)

                    is_payment = target_ttype == "payment_received"
                    header = "Payment Recorded" if is_payment else "Credit Recorded"
                    debug_hdr = _format_debug_header(header, cust['name'], target_amt, target_pmode)
                    return (
                        f"{debug_hdr}✅ Customer Created & Transaction Recorded\n\n"
                        f"Customer: {cust['name']}\n"
                        f"Amount: ₹{target_amt:.0f}\n"
                        f"Mode: {target_pmode}\n\n"
                        f"Current Balance: ₹{result.get('new_balance', 0):.0f}\n\n"
                        f"Need to reverse it? Reply \"undo\"."
                    )

            elif action_type == "send_reminder":
                session.clear_pending()
                await redis_store.clear_pending_action(sender)
                return "✅ Reminder approved."

        elif is_deny:
            session.clear_pending()
            await redis_store.clear_pending_action(sender)
            return "Theek hai, cancel kar diya."

        session.clear_pending()
        await redis_store.clear_pending_action(sender)
        return await self._tool_calling_loop([
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ], sender, "text", None, session)

    async def _handle_undo(self, sender: str, session, txn_id: str) -> str:
        async with AsyncSessionLocal() as db:
            import uuid
            if txn_id:
                stmt = select(Transaction, Customer.name).join(Customer, Transaction.customer_id == Customer.id).where(Transaction.id == uuid.UUID(txn_id))
                res = await db.execute(stmt)
                row = res.first()
                if row:
                    txn, cust_name = row
                    undone_context = {
                        "customer_id": str(txn.customer_id),
                        "customer_name": cust_name,
                        "transaction_type": txn.type.value,
                        "amount": float(txn.amount),
                    }
                    session.last_undone_context = undone_context
                    await redis_store.set_last_undone_context(sender, undone_context)

            result = await undo_last(db, txn_id)
            session.last_transaction_id = None
            await redis_store.set_last_transaction_id(sender, None)
            return f"✅ Transaction Reversed!\n\nCurrent Balance: ₹{result.get('new_balance', 0):.0f}."


planner_agent = PlannerAgent()
