-- Reference schema for the SQLite assessment demo. main.py initializes it on startup.
CREATE TABLE brands (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    initials TEXT NOT NULL,
    color TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE knowledge_entries (
    id INTEGER PRIMARY KEY,
    brand_id INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_knowledge_brand_category ON knowledge_entries(brand_id, category);

CREATE TABLE conversations (
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
CREATE INDEX idx_conversations_brand_updated ON conversations(brand_id, updated_at DESC);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender TEXT NOT NULL CHECK(sender IN ('customer', 'agent')),
    source TEXT NOT NULL DEFAULT 'manual',
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at);

CREATE TABLE reply_runs (
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
CREATE INDEX idx_reply_runs_conversation_created ON reply_runs(conversation_id, created_at DESC);
