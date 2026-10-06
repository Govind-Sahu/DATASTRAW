const state = {
  brands: [],
  conversations: [],
  activeBrandId: null,
  activeConversationId: null,
  conversation: null,
  mode: "agent",
  activeRunId: null,
  activePage: "inbox",
  toastTimer: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("visible"), 2400);
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.error || `Request failed (${response.status})`);
    error.payload = body;
    throw error;
  }
  return body;
}

function brandById(id) {
  return state.brands.find((brand) => Number(brand.id) === Number(id));
}

function brandOptions(select, selectedId) {
  select.replaceChildren();
  for (const brand of state.brands) {
    const option = el("option", "", brand.name);
    option.value = brand.id;
    option.selected = Number(brand.id) === Number(selectedId);
    select.append(option);
  }
}

function updateKnowledgeCount(brandId = state.activeBrandId) {
  const brand = brandById(brandId);
  $("#kbNavCount").textContent = brand ? Number(brand.knowledge_count || 0) : 0;
}

function filteredConversations() {
  return state.conversations.filter((item) => Number(item.brand_id) === Number(state.activeBrandId));
}

function renderConversationList() {
  const list = $("#conversationList");
  list.replaceChildren();
  const conversations = filteredConversations();
  $("#conversationCount").textContent = conversations.length;
  if (!conversations.length) {
    list.append(el("div", "activity-empty", "No conversations for this brand yet."));
    return;
  }
  for (const conversation of conversations) {
    const card = el("button", `conversation-card${Number(conversation.id) === Number(state.activeConversationId) ? " active" : ""}`);
    card.type = "button";
    const avatar = el("span", "conversation-avatar", conversation.customer_name.slice(0, 1).toUpperCase());
    avatar.style.background = `${conversation.brand_color}1b`;
    avatar.style.color = conversation.brand_color;
    const main = el("span", "conversation-main");
    const top = el("span", "conversation-card-top");
    top.append(el("span", "conversation-card-name", conversation.customer_name), el("span", "conversation-time", "Open"));
    const preview = el("span", "conversation-preview", conversation.last_message || "No messages yet");
    const bottom = el("span", "conversation-card-sub");
    bottom.append(el("span", "brand-mini", conversation.order_number), el("span", "unread-dot"));
    main.append(top, preview, bottom);
    card.append(avatar, main);
    card.addEventListener("click", () => loadConversation(Number(conversation.id)));
    list.append(card);
  }
}

function prettyTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function renderOrder(conversation) {
  const summary = $("#orderSummary");
  summary.replaceChildren();
  const fields = [
    ["ORDER", `${conversation.order_number} · ${conversation.product}`],
    ["STATUS", conversation.order_status],
    ["TOTAL", conversation.order_total],
    ["DELIVERED", conversation.delivery_date],
  ];
  fields.forEach(([label, value]) => {
    const field = el("div", "order-field");
    field.append(el("span", "", label), el("strong", label === "STATUS" ? "order-status" : "", value));
    summary.append(field);
  });
}

function renderThread(messages) {
  const thread = $("#thread");
  thread.replaceChildren();
  const divider = el("div", "date-divider");
  divider.append(el("span", "", "TODAY"));
  thread.append(divider);
  for (const message of messages) {
    const isAgent = message.sender === "agent";
    const row = el("div", `message-row${isAgent ? " agent" : ""}`);
    const senderAvatar = el("span", "message-sender-avatar", isAgent ? "A" : state.conversation.customer_name.slice(0, 1).toUpperCase());
    const contentWrap = el("div", "message-content-wrap");
    const bubble = el("div", "message-bubble", message.content);
    const sourceLabel = message.source === "approved_ai" ? " · AI assisted" : "";
    const time = el("span", "message-time", `${prettyTime(message.created_at)}${sourceLabel}`);
    contentWrap.append(bubble, time);
    row.append(senderAvatar, contentWrap);
    thread.append(row);
  }
  requestAnimationFrame(() => { thread.scrollTop = thread.scrollHeight; });
}

function resetDraft() {
  state.activeRunId = null;
  $("#draftArea").classList.add("hidden");
  $("#assistantEmpty").classList.remove("hidden");
  $("#generationError").classList.add("hidden");
  $("#draftText").value = "";
  $("#contextList").replaceChildren();
  $("#agentNotice").textContent = "";
  $("#providerLine").textContent = "";
  $("#editStatus").textContent = "";
}

async function loadConversation(id) {
  state.activeConversationId = id;
  state.activeRunId = null;
  const response = await request(`/api/conversations/${id}`);
  state.conversation = response.conversation;
  $("#emptyState").classList.add("hidden");
  $("#conversationView").classList.remove("hidden");
  $("#customerName").textContent = response.conversation.customer_name;
  $("#customerMeta").textContent = `${response.conversation.customer_email} · ${response.conversation.brand_name}`;
  $("#customerAvatar").textContent = response.conversation.customer_name.slice(0, 1).toUpperCase();
  $("#customerAvatar").style.background = `${response.conversation.brand_color}1b`;
  $("#customerAvatar").style.color = response.conversation.brand_color;
  $("#threadBrand").textContent = response.conversation.brand_name;
  renderOrder(response.conversation);
  renderThread(response.messages);
  renderConversationList();
  resetDraft();
  setMode(state.mode);
}

function setMode(mode) {
  state.mode = mode;
  const isAgent = mode === "agent";
  $("#agentModeButton").classList.toggle("active", isAgent);
  $("#customerModeButton").classList.toggle("active", !isAgent);
  $("#assistantPanel").classList.toggle("hidden", !isAgent);
  $("#composerHint").textContent = isAgent ? "Replying to customer" : "Testing the customer side";
  $("#messageInput").placeholder = isAgent ? "Write a manual reply…" : "Send a new customer message…";
  $("#messageInput").setAttribute("aria-label", isAgent ? "Manual reply to send" : "Customer message to send");
  $("#sendButtonLabel").textContent = isAgent ? "Send reply" : "Send as customer";
}

async function sendManualMessage(event) {
  event.preventDefault();
  if (!state.activeConversationId) return;
  const input = $("#messageInput");
  const content = input.value.trim();
  $("#messageError").textContent = "";
  if (!content) {
    $("#messageError").textContent = "Write a message first.";
    return;
  }
  const button = $("#messageForm").querySelector("button[type=submit]");
  button.disabled = true;
  try {
    await request("/api/messages", {
      method: "POST",
      body: JSON.stringify({
        conversation_id: state.activeConversationId,
        sender: state.mode === "agent" ? "agent" : "customer",
        content,
      }),
    });
    input.value = "";
    resetDraft();
    await refreshConversationData();
    showToast(state.mode === "agent" ? "Manual reply added to the conversation." : "Customer message added.");
  } catch (error) {
    $("#messageError").textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function refreshConversationData() {
  const bootstrap = await request("/api/bootstrap");
  state.conversations = bootstrap.conversations;
  renderConversationList();
  if (state.activeConversationId) await loadConversation(state.activeConversationId);
}

function renderContext(items) {
  const list = $("#contextList");
  list.replaceChildren();
  $("#contextCount").textContent = items.length;
  if (!items.length) {
    list.append(el("div", "context-empty", "No matching policy was found for this customer message. The draft asks the customer to wait while an agent verifies the next step."));
    return;
  }
  for (const item of items) {
    const card = el("div", "context-item");
    const heading = el("div", "context-item-top");
    heading.append(el("strong", "", item.title), el("span", "context-category", item.category.replaceAll("_", " ")));
    card.append(heading, el("p", "", item.content));
    list.append(card);
  }
}

function showDraft(result) {
  state.activeRunId = result.run_id;
  $("#generationError").classList.add("hidden");
  $("#assistantEmpty").classList.add("hidden");
  $("#draftArea").classList.remove("hidden");
  $("#draftText").value = result.draft;
  const badge = $("#confidenceBadge");
  badge.className = `confidence-badge ${result.confidence || "low"}`;
  badge.textContent = `${(result.confidence || "low").toUpperCase()} MATCH`;
  $("#agentNotice").textContent = result.notice || "Review the retrieved policy and confirm the details before sending.";
  $("#providerLine").textContent = `Generated with ${result.provider || "Grounded demo mode"}`;
  renderContext(result.context || []);
  $("#editStatus").textContent = "";
}

async function generateReply() {
  if (!state.activeConversationId) return;
  const button = $("#generateButton");
  const oldContent = button.innerHTML;
  button.disabled = true;
  button.innerHTML = '<span class="sparkle">✦</span><span>Working from brand policies…</span>';
  $("#generationError").classList.add("hidden");
  try {
    const result = await request("/api/generate", {
      method: "POST",
      body: JSON.stringify({ conversation_id: state.activeConversationId }),
    });
    showDraft(result);
  } catch (error) {
    const errorBox = $("#generationError");
    if (error.payload?.suggestion) {
      setMode("agent");
      $("#messageInput").value = error.payload.suggestion;
      errorBox.textContent = `${error.message} A grounded fallback is in the manual composer; review it before sending.`;
    } else {
      errorBox.textContent = error.message;
    }
    errorBox.classList.remove("hidden");
    $("#assistantEmpty").classList.remove("hidden");
  } finally {
    button.disabled = false;
    button.innerHTML = oldContent;
  }
}

async function saveDraft() {
  if (!state.activeRunId) return;
  try {
    await request(`/api/reply-runs/${state.activeRunId}`, {
      method: "PUT",
      body: JSON.stringify({ edited_response: $("#draftText").value }),
    });
    $("#editStatus").textContent = "Your edit is saved in the activity log.";
    showToast("Edit saved.");
  } catch (error) {
    $("#editStatus").textContent = error.message;
  }
}

async function approveDraft() {
  if (!state.activeRunId) return;
  const button = $("#approveButton");
  button.disabled = true;
  try {
    await request(`/api/reply-runs/${state.activeRunId}/send`, {
      method: "POST",
      body: JSON.stringify({ final_response: $("#draftText").value }),
    });
    resetDraft();
    await refreshConversationData();
    showToast("Approved reply sent to the conversation.");
  } catch (error) {
    $("#generationError").textContent = error.message;
    $("#generationError").classList.remove("hidden");
  } finally {
    button.disabled = false;
  }
}

function setActivePage(page) {
  state.activePage = page;
  $$(".page-tab").forEach((button) => button.classList.toggle("active", button.dataset.page === page));
  $("#inboxPage").classList.toggle("hidden", page !== "inbox");
  $("#knowledgePage").classList.toggle("hidden", page !== "knowledge");
  $("#activityPage").classList.toggle("hidden", page !== "activity");
  if (page === "knowledge") loadKnowledge();
  if (page === "activity") loadActivity();
}

async function loadKnowledge() {
  if (!$("#kbBrandSelect").value) return;
  const result = await request(`/api/knowledge?brand_id=${encodeURIComponent($("#kbBrandSelect").value)}`);
  const brand = brandById($("#kbBrandSelect").value);
  if (brand) brand.knowledge_count = result.entries.length;
  renderKnowledge(result.entries);
}

function renderKnowledge(entries) {
  $("#policyList").replaceChildren();
  $("#kbPolicyCount").textContent = `${entries.length} ${entries.length === 1 ? "policy" : "policies"}`;
  if (Number($("#kbBrandSelect").value) === Number(state.activeBrandId)) {
    $("#kbNavCount").textContent = entries.length;
  }
  if (!entries.length) {
    $("#policyList").append(el("div", "activity-empty", "No saved policies for this brand. Add one to give the assistant grounded information."));
    return;
  }
  const icons = { returns: "↩", refunds: "₹", shipping: "⌁", cancellations: "×", damaged_items: "◇" };
  for (const entry of entries) {
    const card = el("article", "policy-card");
    const top = el("div", "policy-card-top");
    top.append(el("span", "policy-type-icon", icons[entry.category] || "◈"));
    const label = el("div");
    label.append(el("h3", "", entry.title), el("div", "category-label", entry.category));
    top.append(label);
    const content = el("p", "", entry.content);
    const actions = el("div", "policy-card-actions");
    const edit = el("button", "small-action", "Edit");
    edit.type = "button";
    edit.addEventListener("click", () => openPolicyEditor(entry));
    const remove = el("button", "small-action delete", "Delete");
    remove.type = "button";
    remove.addEventListener("click", () => deletePolicy(entry));
    actions.append(edit, remove);
    card.append(top, content, actions);
    $("#policyList").append(card);
  }
}

function openPolicyEditor(entry = null) {
  $("#policyEditor").classList.remove("hidden");
  $("#policyError").textContent = "";
  $("#policyId").value = entry ? entry.id : "";
  $("#policyCategory").value = entry ? entry.category : "";
  $("#policyTitle").value = entry ? entry.title : "";
  $("#policyContent").value = entry ? entry.content : "";
  $("#policyFormTitle").textContent = entry ? "Edit policy" : "New policy";
  $("#savePolicyButton").textContent = entry ? "Save changes" : "Save policy";
  $("#policyCategory").focus();
}

async function submitPolicy(event) {
  event.preventDefault();
  const id = $("#policyId").value;
  const payload = {
    brand_id: Number($("#kbBrandSelect").value),
    category: $("#policyCategory").value.trim(),
    title: $("#policyTitle").value.trim(),
    content: $("#policyContent").value.trim(),
  };
  try {
    await request(id ? `/api/knowledge/${id}` : "/api/knowledge", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    $("#policyEditor").classList.add("hidden");
    await loadKnowledge();
    showToast(id ? "Policy updated." : "Policy added.");
  } catch (error) {
    $("#policyError").textContent = error.message;
  }
}

async function deletePolicy(entry) {
  if (!window.confirm(`Delete “${entry.title}” from this brand’s knowledge base?`)) return;
  try {
    await request(`/api/knowledge/${entry.id}`, { method: "DELETE" });
    await loadKnowledge();
    showToast("Policy deleted.");
  } catch (error) {
    showToast(error.message);
  }
}

function safeParseContext(value) {
  try { return JSON.parse(value || "[]"); } catch { return []; }
}

function activityField(parent, label, value) {
  const field = el("div", "activity-field");
  field.append(el("label", "", label), el("p", "", value || "Not recorded"));
  parent.append(field);
}

async function loadActivity() {
  const query = state.activeConversationId ? `?conversation_id=${state.activeConversationId}` : "";
  const result = await request(`/api/activity${query}`);
  const list = $("#activityList");
  list.replaceChildren();
  if (!result.runs.length) {
    list.append(el("div", "activity-empty", "No AI reply runs yet. Generate a reply from the Inbox to see the retrieval and response audit trail here."));
    return;
  }
  for (const run of result.runs) {
    const card = el("article", "activity-card");
    const heading = el("div", "activity-card-heading");
    heading.append(el("strong", "", `${run.brand_name} · ${run.order_number}`), el("span", "", new Date(run.created_at).toLocaleString()));
    card.append(heading);
    card.append(el("div", "activity-meta", `${run.provider} · ${run.confidence} confidence · ${run.status}`));
    activityField(card, "CUSTOMER MESSAGE", run.customer_message);
    const contextField = el("div", "activity-field");
    contextField.append(el("label", "", "RETRIEVED CONTEXT"));
    const context = safeParseContext(run.retrieved_context);
    if (!context.length) contextField.append(el("div", "activity-context-item", "No matching brand policy."));
    context.forEach((item) => contextField.append(el("div", "activity-context-item", `${item.title}: ${item.content}`)));
    card.append(contextField);
    activityField(
      card,
      run.status === "failed" ? "SAFE FALLBACK SUGGESTION" : "GENERATED RESPONSE",
      run.generated_response || run.error,
    );
    if (run.error) activityField(card, "MODEL ERROR", run.error);
    if (run.edited_response) activityField(card, "AGENT-EDITED RESPONSE", run.edited_response);
    if (run.final_response) activityField(card, "FINAL RESPONSE SENT", run.final_response);
    list.append(card);
  }
}

async function init() {
  try {
    const bootstrap = await request("/api/bootstrap");
    state.brands = bootstrap.brands;
    state.conversations = bootstrap.conversations;
    if (!state.brands.length) throw new Error("Add at least one brand before using the app.");
    const modeLabel = $("#modeBadgeLabel");
    const liveModelEnabled = Boolean(bootstrap.llm_enabled);
    modeLabel.textContent = liveModelEnabled ? "Live model enabled" : "Demo mode";
    if (liveModelEnabled) $("#modeBadge").classList.add("live-mode-badge");
    state.activeBrandId = state.brands[0].id;
    updateKnowledgeCount();
    brandOptions($("#brandFilter"), state.activeBrandId);
    brandOptions($("#kbBrandSelect"), state.activeBrandId);
    renderConversationList();
    const initial = filteredConversations()[0];
    if (initial) await loadConversation(Number(initial.id));
    else $("#emptyState").classList.remove("hidden");
  } catch (error) {
    $("#emptyState").classList.remove("hidden");
    $("#emptyState").querySelector("h2").textContent = "Could not load the workspace";
    $("#emptyState").querySelector("p").textContent = error.message;
  }
}

$("#brandFilter").addEventListener("change", async (event) => {
  state.activeBrandId = Number(event.target.value);
  const brand = brandById(state.activeBrandId);
  $(".select-brand-dot").style.background = brand?.color || "#39734f";
  updateKnowledgeCount();
  renderConversationList();
  const first = filteredConversations()[0];
  if (first) await loadConversation(Number(first.id));
  else {
    state.activeConversationId = null;
    state.conversation = null;
    $("#conversationView").classList.add("hidden");
    $("#emptyState").classList.remove("hidden");
    resetDraft();
  }
});
$("#agentModeButton").addEventListener("click", () => setMode("agent"));
$("#customerModeButton").addEventListener("click", () => setMode("customer"));
$("#messageForm").addEventListener("submit", sendManualMessage);
$("#generateButton").addEventListener("click", generateReply);
$("#regenerateButton").addEventListener("click", generateReply);
$("#saveEditButton").addEventListener("click", saveDraft);
$("#approveButton").addEventListener("click", approveDraft);
$("#kbBrandSelect").addEventListener("change", loadKnowledge);
$("#addPolicyButton").addEventListener("click", () => openPolicyEditor());
$("#cancelPolicyButton").addEventListener("click", () => $("#policyEditor").classList.add("hidden"));
$("#policyForm").addEventListener("submit", submitPolicy);
$("#refreshActivity").addEventListener("click", loadActivity);
$$(".page-tab").forEach((button) => button.addEventListener("click", () => setActivePage(button.dataset.page)));
$("#helpButton").addEventListener("click", () => $("#aboutDialog").showModal());
$("#closeAboutButton").addEventListener("click", () => $("#aboutDialog").close());
$("#closeAboutFooter").addEventListener("click", () => $("#aboutDialog").close());
$("#newConversationHint").addEventListener("click", () => showToast("Use the Customer toggle to add a new message to a demo conversation."));

init();
