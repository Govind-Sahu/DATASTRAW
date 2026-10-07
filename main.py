"""Datastraw CX Reply Assistant — standard-library demo server."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
ASSIGNMENT_ZIP = STATIC / "datastraw-cx-reply-assistant.zip"
DB_PATH = Path(os.environ.get("CX_DB_PATH", ROOT / "instance" / "cx_assistant.sqlite"))

SEED_BRANDS = [
    {
        "name": "Northstar Botanics",
        "slug": "northstar",
        "initials": "NB",
        "color": "#4d735d",
        "entries": [
            ("returns", "Returns", "Unused, unopened products can be returned within 30 days of delivery. Contact support for a prepaid return label."),
            ("refunds", "Refunds", "Refunds are issued to the original payment method within 5–7 business days after an approved return is received. Requests must be made within 30 days of delivery."),
            ("shipping", "Shipping", "Standard shipping takes 3–5 business days. Delivery estimates begin when the carrier scans the parcel."),
            ("cancellations", "Cancellations", "Orders can be cancelled within 2 hours of placement, provided the order has not entered fulfillment."),
            ("damaged_items", "Damaged items", "Report an item that arrives broken or leaking within 7 days of delivery. Include a clear photo of the item and its packaging. Support will review the claim and confirm whether a replacement or refund is available."),
        ],
    },
    {
        "name": "Tide & Timber",
        "slug": "tide-timber",
        "initials": "TT",
        "color": "#38778b",
        "entries": [
            ("returns", "Returns", "Eligible unused items can be returned within 14 days of delivery. Return shipping is paid by the customer unless the item is faulty."),
            ("refunds", "Refunds", "Approved refunds are returned to the original payment method within 10 business days. Refund requests must be submitted within 14 days of delivery."),
            ("shipping", "Shipping", "Standard delivery takes 5–8 business days. Tracking is sent by email once the parcel leaves our warehouse."),
            ("cancellations", "Cancellations", "Orders may be cancelled before dispatch. Once dispatched, the order cannot be cancelled and the returns process applies."),
            ("damaged_items", "Damaged items", "Report a damaged or broken item within 5 days of delivery and attach clear photos of the item and outer packaging. Support will review the claim and then confirm the available resolution."),
        ],
    },
]

SEED_CONVERSATIONS = [
    ("northstar", "Maya Chen", "maya@example.com", "NS-48291", "Delivered", "$42.00", "Yesterday, 2:14 PM", "Glass face serum bottle", "My order was delivered but the bottle is broken. What can I do?"),
    ("tide-timber", "Alex Morgan", "alex@example.com", "TT-19307", "Delivered", "$68.00", "Today, 9:32 AM", "Ceramic oil bottle", "My order was delivered but the bottle is broken. What can I do?"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize_db() -> None:
    with connect_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS brands (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                initials TEXT NOT NULL,
                color TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS knowledge_entries (
                id INTEGER PRIMARY KEY,
                brand_id INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_knowledge_brand_category
                ON knowledge_entries(brand_id, category);
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY,
                brand_id INTEGER NOT NULL REFERENCES brands(id),
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                order_number TEXT NOT NULL,
                order_status TEXT NOT NULL,
                order_total TEXT NOT NULL,
                delivery_date TEXT NOT NULL,
                product TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_conversations_brand_updated
                ON conversations(brand_id, updated_at DESC);
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                sender TEXT NOT NULL CHECK(sender IN ('customer', 'agent')),
                source TEXT NOT NULL DEFAULT 'manual',
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
                ON messages(conversation_id, created_at);
            CREATE TABLE IF NOT EXISTS reply_runs (
                id INTEGER PRIMARY KEY,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                customer_message_id INTEGER REFERENCES messages(id),
                retrieved_context TEXT NOT NULL,
                generated_response TEXT NOT NULL,
                edited_response TEXT,
                final_response TEXT,
                confidence TEXT NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL,
                sent_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_reply_runs_conversation_created
                ON reply_runs(conversation_id, created_at DESC);
            """
        )
        # Refresh only the original shipped copy; never overwrite a policy an agent edited.
        db.execute(
            """UPDATE knowledge_entries SET content=?
               WHERE brand_id=(SELECT id FROM brands WHERE slug='northstar')
                 AND category='damaged_items'
                 AND content=?""",
            (
                "Report an item that arrives broken or leaking within 7 days of delivery. "
                "Include a clear photo of the item and its packaging. Support will review the "
                "claim and confirm whether a replacement or refund is available.",
                "For an item that arrives broken or leaking, contact us within 7 days of delivery "
                "and include a photo of the item and packaging. We will review it and confirm "
                "whether a replacement or refund is available. Do not promise an outcome before review.",
            ),
        )
        db.execute(
            """UPDATE knowledge_entries SET content=?
               WHERE brand_id=(SELECT id FROM brands WHERE slug='tide-timber')
                 AND category='damaged_items'
                 AND content=?""",
            (
                "Report a damaged or broken item within 5 days of delivery and attach clear photos "
                "of the item and outer packaging. Support will review the claim and then confirm "
                "the available resolution.",
                "Report a damaged or broken item within 5 days of delivery and attach clear photos "
                "of the item and outer packaging. Support will review the claim and explain the "
                "available resolution; do not guarantee a refund or replacement before review.",
            ),
        )
        if db.execute("SELECT COUNT(*) FROM brands").fetchone()[0] == 0:
            brand_ids = {}
            for brand in SEED_BRANDS:
                cursor = db.execute(
                    "INSERT INTO brands(name, slug, initials, color, created_at) VALUES (?, ?, ?, ?, ?)",
                    (brand["name"], brand["slug"], brand["initials"], brand["color"], now_iso()),
                )
                brand_ids[brand["slug"]] = cursor.lastrowid
                for category, title, content in brand["entries"]:
                    db.execute(
                        """INSERT INTO knowledge_entries
                           (brand_id, category, title, content, updated_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (cursor.lastrowid, category, title, content, now_iso()),
                    )
            for slug, name, email, order, status, total, delivered, product, first_message in SEED_CONVERSATIONS:
                cursor = db.execute(
                    """INSERT INTO conversations
                       (brand_id, customer_name, customer_email, order_number, order_status,
                        order_total, delivery_date, product, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (brand_ids[slug], name, email, order, status, total, delivered, product, now_iso()),
                )
                db.execute(
                    """INSERT INTO messages(conversation_id, sender, source, content, created_at)
                       VALUES (?, 'customer', 'inbound', ?, ?)""",
                    (cursor.lastrowid, first_message, now_iso()),
                )


def row_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "can", "could",
    "do", "does", "for", "from", "get", "got", "has", "have", "help", "how",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "our", "please",
    "the", "this", "to", "was", "we", "what", "when", "with", "you", "your",
}


def tokens(text: str) -> set[str]:
    words = set(re.findall(r"[a-z0-9]+", (text or "").lower()))
    return {word for word in words if word not in STOP_WORDS}


def retrieve_context(db: sqlite3.Connection, brand_id: int, question: str) -> list[dict]:
    """Small lexical retrieval. The brand_id filter is always applied in SQL."""
    query_terms = tokens(question)
    entries = db.execute(
        """SELECT id, category, title, content
           FROM knowledge_entries WHERE brand_id = ? ORDER BY id""",
        (brand_id,),
    ).fetchall()
    scored = []
    for entry in entries:
        terms = tokens(entry["title"] + " " + entry["category"] + " " + entry["content"])
        overlap = query_terms & terms
        score = len(overlap)
        category = entry["category"]
        if category == "damaged_items" and query_terms & {
            "broken", "damage", "damaged", "cracked", "crack", "leaking", "leak", "shattered",
        }:
            score += 5
        if category == "shipping" and query_terms & {"delivered", "delivery", "shipping", "shipment", "carrier"}:
            score += 2
        if category == "refunds" and query_terms & {"refund", "money", "reimburse", "refunded"}:
            score += 3
        if category == "returns" and query_terms & {"return", "exchange", "send", "back"}:
            score += 2
        if category == "cancellations" and query_terms & {"cancel", "cancellation"}:
            score += 4
        if score > 0:
            scored.append(
                {
                    "id": entry["id"],
                    "category": category,
                    "title": entry["title"],
                    "content": entry["content"],
                    "score": score,
                    "matched_terms": sorted(overlap),
                }
            )
    return sorted(scored, key=lambda item: (-item["score"], item["category"]))[:3]


def make_grounded_draft(customer_name: str, product: str, context: list[dict]) -> tuple[str, str, str]:
    if not context:
        return (
            f"Hi {customer_name}, I’m sorry to hear there’s a problem with your order. "
            "I don’t have a verified policy for this request, so I’m checking with our support team "
            "before advising on the next steps. We’ll follow up as soon as we’ve confirmed the right resolution.",
            "low",
            "No matching brand policy was found. Review the case and confirm the correct next step before sending.",
        )
    by_category = {item["category"]: item for item in context}
    damaged = by_category.get("damaged_items")
    if damaged:
        body = damaged["content"]
        window = re.search(r"\bwithin\s+(\d+\s+days?)\s+of\s+delivery\b", body, re.IGNORECASE)
        window_hint = (
            f" Our damaged-item policy asks that you contact us within {window.group(1)} of delivery."
            if window
            else ""
        )
        photo_hint = (
            " Please send us a clear photo of the item and its packaging."
            if "photo" in body.lower()
            else ""
        )
        return (
            f"Hi {customer_name}, I’m sorry your {product.lower()} arrived damaged. "
            f"{window_hint}{photo_hint} "
            "We’ll review the claim and confirm the available resolution.",
            "high",
            "Draft is grounded in this brand’s damaged-item policy. An agent should verify the case details before sending.",
        )
    best = context[0]
    return (
        f"Hi {customer_name}, thanks for reaching out. Based on our {best['title'].lower()} policy: "
        f"{best['content']} If you share any missing details, I can help with the next step.",
        "medium",
        "Only the retrieved policy text is available. Review the draft for fit before sending.",
    )


def validate_model_draft(response: str, context: list[dict]) -> str | None:
    """Reject unsupported refund/replacement guarantees from the optional model."""
    lower_response = response.lower()
    policy_text = " ".join(item["content"].lower() for item in context)
    promises = {
        "refund": re.compile(
            r"\b(?:we(?:'ll| will| can| have| are going to)\s+(?:issue|process|send|provide|arrange|give)\s+(?:you\s+)?(?:a\s+)?refund|"
            r"you(?:'ll| will)\s+(?:receive|get)\s+(?:a\s+)?refund|your refund\s+(?:is|has been)\s+(?:approved|processed|issued))\b"
        ),
        "replacement": re.compile(
            r"\b(?:we(?:'ll| will| can| have| are going to)\s+(?:send|provide|arrange|ship|give)\s+(?:you\s+)?(?:a\s+)?replacement|"
            r"you(?:'ll| will)\s+(?:receive|get)\s+(?:a\s+)?replacement|your replacement\s+(?:is|has been)\s+(?:approved|on the way|shipped))\b"
        ),
    }
    for outcome, pattern in promises.items():
        if pattern.search(lower_response):
            # Mentioning a possible outcome is not the same as authorizing a promise.
            explicitly_authorized = any(
                phrase in policy_text
                for phrase in (
                    f"we will {outcome}",
                    f"we'll {outcome}",
                    f"guaranteed {outcome}",
                    f"automatically {outcome}",
                )
            )
            if not explicitly_authorized:
                return f"Blocked an unsupported {outcome} promise."
    return None


def openrouter_draft(customer_name: str, product: str, latest_message: str, context: list[dict]) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    payload = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": 220,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You draft concise, empathetic customer-support replies. Treat the supplied "
                    "brand policy excerpts as the only source of truth. Never promise a refund, "
                    "replacement, or exception unless the excerpts explicitly authorize it. If "
                    "the excerpts do not answer the question, say that a human agent will verify "
                    "the next step. Do not invent dates, order facts, or policy terms. Return only "
                    "the message to the customer."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "customer": customer_name,
                        "product": product,
                        "latest_customer_message": latest_message,
                        "retrieved_brand_policies": [
                            {"title": item["title"], "text": item["content"]} for item in context
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    }
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.environ.get("APP_ORIGIN", "http://localhost:5000"),
            "X-Title": "Datastraw CX Reply Assistant",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"].strip()
        if not content:
            raise RuntimeError("The model returned an empty draft")
        return content
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Model request failed: {exc}") from exc


class AppHandler(BaseHTTPRequestHandler):
    server_version = "CXReplyAssistant/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print("%s - %s" % (self.log_date_time_string(), fmt % args))

    def send_json(self, status: int, payload: dict | list) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 100_000:
            raise ValueError("Request body is too large")
        data = self.rfile.read(length) if length else b"{}"
        value = json.loads(data.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Expected a JSON object")
        return value

    def serve_static(self, path: str) -> None:
        candidate = (STATIC / unquote(path)).resolve()
        if not candidate.is_relative_to(STATIC.resolve()) or not candidate.is_file():
            self.send_error(404)
            return
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
        }.get(candidate.suffix, "application/octet-stream")
        content = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def serve_assignment_zip(self) -> None:
        if not ASSIGNMENT_ZIP.is_file():
            self.send_error(404, "Assignment ZIP not found")
            return
        content = ASSIGNMENT_ZIP.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header(
            "Content-Disposition",
            'attachment; filename="datastraw-cx-reply-assistant.zip"',
        )
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path == "/":
            self.serve_static("index.html")
            return
        if path == "/download/assignment.zip":
            self.serve_assignment_zip()
            return
        if path.startswith("/static/"):
            self.serve_static(path[len("/static/"):])
            return
        try:
            with connect_db() as db:
                if path == "/api/bootstrap":
                    brands = [
                        dict(row)
                        for row in db.execute(
                            """SELECT b.*,
                                      (SELECT COUNT(*) FROM knowledge_entries k WHERE k.brand_id=b.id)
                                          AS knowledge_count
                               FROM brands b ORDER BY b.id"""
                        )
                    ]
                    conversations = [
                        dict(row)
                        for row in db.execute(
                            """SELECT c.*, b.name AS brand_name, b.slug AS brand_slug,
                                      b.initials AS brand_initials, b.color AS brand_color,
                                      (SELECT content FROM messages m
                                       WHERE m.conversation_id=c.id ORDER BY m.id DESC LIMIT 1) AS last_message
                               FROM conversations c JOIN brands b ON b.id=c.brand_id
                               ORDER BY c.updated_at DESC"""
                        )
                    ]
                    self.send_json(
                        200,
                        {
                            "brands": brands,
                            "conversations": conversations,
                            "llm_enabled": bool(os.environ.get("OPENROUTER_API_KEY")),
                        },
                    )
                    return
                match = re.fullmatch(r"/api/conversations/(\d+)", path)
                if match:
                    conversation_id = int(match.group(1))
                    conversation = db.execute(
                        """SELECT c.*, b.name AS brand_name, b.slug AS brand_slug,
                                  b.initials AS brand_initials, b.color AS brand_color
                           FROM conversations c JOIN brands b ON b.id=c.brand_id WHERE c.id=?""",
                        (conversation_id,),
                    ).fetchone()
                    if not conversation:
                        self.send_json(404, {"error": "Conversation not found"})
                        return
                    messages = [
                        dict(row)
                        for row in db.execute(
                            "SELECT * FROM messages WHERE conversation_id=? ORDER BY id",
                            (conversation_id,),
                        )
                    ]
                    self.send_json(200, {"conversation": dict(conversation), "messages": messages})
                    return
                if path == "/api/knowledge":
                    try:
                        brand_id = int(query.get("brand_id", [""])[0])
                    except ValueError:
                        self.send_json(400, {"error": "A valid brand_id is required"})
                        return
                    entries = [
                        dict(row)
                        for row in db.execute(
                            "SELECT * FROM knowledge_entries WHERE brand_id=? ORDER BY category, id",
                            (brand_id,),
                        )
                    ]
                    self.send_json(200, {"entries": entries})
                    return
                if path == "/api/activity":
                    conversation_id = query.get("conversation_id", [""])[0]
                    if conversation_id:
                        rows = db.execute(
                            """SELECT r.*, c.order_number, b.name AS brand_name,
                                      m.content AS customer_message
                               FROM reply_runs r
                               JOIN conversations c ON c.id=r.conversation_id
                               JOIN brands b ON b.id=c.brand_id
                               LEFT JOIN messages m ON m.id=r.customer_message_id
                               WHERE r.conversation_id=? ORDER BY r.created_at DESC LIMIT 30""",
                            (conversation_id,),
                        )
                    else:
                        rows = db.execute(
                            """SELECT r.*, c.order_number, b.name AS brand_name,
                                      m.content AS customer_message
                               FROM reply_runs r
                               JOIN conversations c ON c.id=r.conversation_id
                               JOIN brands b ON b.id=c.brand_id
                               LEFT JOIN messages m ON m.id=r.customer_message_id
                               ORDER BY r.created_at DESC LIMIT 30"""
                        )
                    self.send_json(200, {"runs": [dict(row) for row in rows]})
                    return
            self.send_json(404, {"error": "Not found"})
        except sqlite3.Error as exc:
            self.send_json(500, {"error": f"Database error: {exc}"})

    def do_POST(self) -> None:
        try:
            payload = self.read_json()
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
            return
        path = urlparse(self.path).path
        if path == "/api/messages":
            self.create_message(payload)
        elif path == "/api/generate":
            self.generate_reply(payload)
        elif path == "/api/knowledge":
            self.create_knowledge(payload)
        elif re.fullmatch(r"/api/reply-runs/\d+/send", path):
            self.send_reply(path, payload)
        else:
            self.send_json(404, {"error": "Not found"})

    def do_PUT(self) -> None:
        try:
            payload = self.read_json()
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
            return
        path = urlparse(self.path).path
        match = re.fullmatch(r"/api/knowledge/(\d+)", path)
        if match:
            self.update_knowledge(int(match.group(1)), payload)
            return
        match = re.fullmatch(r"/api/reply-runs/(\d+)", path)
        if match:
            self.update_reply(int(match.group(1)), payload)
            return
        self.send_json(404, {"error": "Not found"})

    def do_DELETE(self) -> None:
        match = re.fullmatch(r"/api/knowledge/(\d+)", urlparse(self.path).path)
        if not match:
            self.send_json(404, {"error": "Not found"})
            return
        with connect_db() as db:
            cursor = db.execute("DELETE FROM knowledge_entries WHERE id=?", (int(match.group(1)),))
            if not cursor.rowcount:
                self.send_json(404, {"error": "Knowledge entry not found"})
                return
        self.send_json(200, {"ok": True})

    def create_message(self, payload: dict) -> None:
        try:
            conversation_id = int(payload.get("conversation_id"))
        except (TypeError, ValueError):
            self.send_json(400, {"error": "A valid conversation_id is required"})
            return
        sender = payload.get("sender")
        content = str(payload.get("content", "")).strip()
        if sender not in {"customer", "agent"} or not content or len(content) > 4000:
            self.send_json(400, {"error": "Choose customer or agent and enter a message under 4,000 characters."})
            return
        with connect_db() as db:
            if not db.execute("SELECT id FROM conversations WHERE id=?", (conversation_id,)).fetchone():
                self.send_json(404, {"error": "Conversation not found"})
                return
            cursor = db.execute(
                "INSERT INTO messages(conversation_id, sender, source, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (conversation_id, sender, "manual", content, now_iso()),
            )
            db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now_iso(), conversation_id))
            message = row_dict(db.execute("SELECT * FROM messages WHERE id=?", (cursor.lastrowid,)).fetchone())
        self.send_json(201, {"message": message})

    def generate_reply(self, payload: dict) -> None:
        try:
            conversation_id = int(payload.get("conversation_id"))
        except (TypeError, ValueError):
            self.send_json(400, {"error": "A valid conversation_id is required"})
            return
        with connect_db() as db:
            conversation = db.execute(
                """SELECT c.*, b.name AS brand_name FROM conversations c
                   JOIN brands b ON b.id=c.brand_id WHERE c.id=?""",
                (conversation_id,),
            ).fetchone()
            if not conversation:
                self.send_json(404, {"error": "Conversation not found"})
                return
            latest_customer = db.execute(
                """SELECT * FROM messages WHERE conversation_id=? AND sender='customer'
                   ORDER BY id DESC LIMIT 1""",
                (conversation_id,),
            ).fetchone()
            if not latest_customer:
                self.send_json(409, {"error": "Add a customer message before generating a reply."})
                return
            context = retrieve_context(db, conversation["brand_id"], latest_customer["content"])
            generated, confidence, notice = make_grounded_draft(
                conversation["customer_name"], conversation["product"], context
            )
            provider = "Grounded demo mode"
            if os.environ.get("OPENROUTER_API_KEY") and context:
                try:
                    model_draft = openrouter_draft(
                        conversation["customer_name"],
                        conversation["product"],
                        latest_customer["content"],
                        context,
                    )
                    validation_issue = validate_model_draft(model_draft, context)
                    if validation_issue:
                        notice += f" {validation_issue} A grounded fallback was used."
                        provider = "OpenRouter rejected · grounded fallback"
                    else:
                        generated = model_draft
                        provider = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini") + " via OpenRouter"
                except RuntimeError as exc:
                    cursor = db.execute(
                        """INSERT INTO reply_runs
                           (conversation_id, customer_message_id, retrieved_context, generated_response,
                            confidence, provider, status, error, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, 'failed', ?, ?)""",
                        (
                            conversation_id,
                            latest_customer["id"],
                            json.dumps(context, ensure_ascii=False),
                            generated,
                            confidence,
                            "OpenRouter failed · grounded fallback suggestion",
                            str(exc),
                            now_iso(),
                        ),
                    )
                    self.send_json(
                        502,
                        {"error": str(exc), "run_id": cursor.lastrowid, "suggestion": generated, "context": context},
                    )
                    return
            elif os.environ.get("OPENROUTER_API_KEY"):
                provider = "Grounded fallback · no matching policy"
            cursor = db.execute(
                """INSERT INTO reply_runs
                   (conversation_id, customer_message_id, retrieved_context, generated_response,
                    confidence, provider, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'generated', ?)""",
                (
                    conversation_id,
                    latest_customer["id"],
                    json.dumps(context, ensure_ascii=False),
                    generated,
                    confidence,
                    provider,
                    now_iso(),
                ),
            )
            run_id = cursor.lastrowid
        self.send_json(
            201,
            {
                "run_id": run_id,
                "draft": generated,
                "context": context,
                "confidence": confidence,
                "notice": notice,
                "provider": provider,
            },
        )

    def create_knowledge(self, payload: dict) -> None:
        try:
            brand_id = int(payload.get("brand_id"))
        except (TypeError, ValueError):
            self.send_json(400, {"error": "Choose a brand"})
            return
        category = str(payload.get("category", "")).strip()
        title = str(payload.get("title", "")).strip()
        content = str(payload.get("content", "")).strip()
        if not category or not title or not content:
            self.send_json(400, {"error": "Category, title and policy text are required"})
            return
        if len(content) > 5000 or len(title) > 120:
            self.send_json(400, {"error": "Title must be under 120 characters and policy text under 5,000"})
            return
        with connect_db() as db:
            if not db.execute("SELECT id FROM brands WHERE id=?", (brand_id,)).fetchone():
                self.send_json(404, {"error": "Brand not found"})
                return
            cursor = db.execute(
                """INSERT INTO knowledge_entries(brand_id, category, title, content, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (brand_id, category, title, content, now_iso()),
            )
            entry = row_dict(db.execute("SELECT * FROM knowledge_entries WHERE id=?", (cursor.lastrowid,)).fetchone())
        self.send_json(201, {"entry": entry})

    def update_knowledge(self, entry_id: int, payload: dict) -> None:
        category = str(payload.get("category", "")).strip()
        title = str(payload.get("title", "")).strip()
        content = str(payload.get("content", "")).strip()
        if not category or not title or not content:
            self.send_json(400, {"error": "Category, title and policy text are required"})
            return
        with connect_db() as db:
            cursor = db.execute(
                """UPDATE knowledge_entries SET category=?, title=?, content=?, updated_at=?
                   WHERE id=?""",
                (category, title, content, now_iso(), entry_id),
            )
            if not cursor.rowcount:
                self.send_json(404, {"error": "Knowledge entry not found"})
                return
            entry = row_dict(db.execute("SELECT * FROM knowledge_entries WHERE id=?", (entry_id,)).fetchone())
        self.send_json(200, {"entry": entry})

    def update_reply(self, run_id: int, payload: dict) -> None:
        edited = str(payload.get("edited_response", "")).strip()
        if not edited or len(edited) > 4000:
            self.send_json(400, {"error": "Enter an edited reply under 4,000 characters"})
            return
        with connect_db() as db:
            cursor = db.execute(
                """UPDATE reply_runs SET edited_response=?
                   WHERE id=? AND status IN ('generated', 'edited')""",
                (edited, run_id),
            )
            if not cursor.rowcount:
                self.send_json(404, {"error": "An editable reply run was not found"})
                return
            db.execute("UPDATE reply_runs SET status='edited' WHERE id=?", (run_id,))
        self.send_json(200, {"ok": True})

    def send_reply(self, path: str, payload: dict) -> None:
        run_id = int(re.fullmatch(r"/api/reply-runs/(\d+)/send", path).group(1))
        with connect_db() as db:
            run = db.execute("SELECT * FROM reply_runs WHERE id=?", (run_id,)).fetchone()
            if not run or run["status"] not in {"generated", "edited"}:
                self.send_json(409, {"error": "This draft is not available to send"})
                return
            final = str(payload.get("final_response") or run["edited_response"] or run["generated_response"]).strip()
            if not final or len(final) > 4000:
                self.send_json(400, {"error": "Enter a final reply under 4,000 characters"})
                return
            cursor = db.execute(
                """INSERT INTO messages(conversation_id, sender, source, content, created_at)
                   VALUES (?, 'agent', 'approved_ai', ?, ?)""",
                (run["conversation_id"], final, now_iso()),
            )
            db.execute(
                """UPDATE reply_runs SET edited_response=?, final_response=?, status='sent', sent_at=?
                   WHERE id=?""",
                (final, final, now_iso(), run_id),
            )
            db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now_iso(), run["conversation_id"]))
            message = row_dict(db.execute("SELECT * FROM messages WHERE id=?", (cursor.lastrowid,)).fetchone())
        self.send_json(201, {"message": message})

def main() -> None:
    initialize_db()
    port = int(os.environ.get("PORT", "5000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), AppHandler)
    print(f"CX Reply Assistant listening on 0.0.0.0:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
