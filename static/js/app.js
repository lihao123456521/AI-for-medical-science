const STORAGE_KEY = 'uscc_chat_history_v34';
const API_KEY_STORAGE = 'uscc_openai_api_key';
const API_MODEL_STORAGE = 'uscc_openai_model';
const API_PROVIDER_STORAGE = 'uscc_api_provider';
const API_BASE_URL_STORAGE = 'uscc_api_base_url';
const API_CUSTOM_MODEL_STORAGE = 'uscc_api_custom_model';

const els = {
  sidebar: document.getElementById('sidebar'),
  historyList: document.getElementById('historyList'),
  chatWindow: document.getElementById('chatWindow'),
  emptyState: document.getElementById('emptyState'),
  input: document.getElementById('messageInput'),
  sendBtn: document.getElementById('sendBtn'),
  newChatBtn: document.getElementById('newChatBtn'),
  addCurrentCaseBtn: document.getElementById('addCurrentCaseBtn'),
  fileInput: document.getElementById('fileInput'),
  uploadStatus: document.getElementById('uploadStatus'),
  kbSummary: document.getElementById('kbSummary'),
  mobileMenuBtn: document.getElementById('mobileMenuBtn'),
  apiKeyBtn: document.getElementById('apiKeyBtn'),
  apiModal: document.getElementById('apiModal'),
  closeApiModal: document.getElementById('closeApiModal'),
  apiKeyInput: document.getElementById('apiKeyInput'),
  apiProviderSelect: document.getElementById('apiProviderSelect'),
  apiBaseUrlInput: document.getElementById('apiBaseUrlInput'),
  apiModelSelect: document.getElementById('apiModelSelect'),
  apiCustomModelInput: document.getElementById('apiCustomModelInput'),
  saveApiKey: document.getElementById('saveApiKey'),
  clearApiKey: document.getElementById('clearApiKey'),
  testApiKey: document.getElementById('testApiKey'),
  apiKeyStatus: document.getElementById('apiKeyStatus'),
  fontSettingsBtn: document.getElementById('fontSettingsBtn'),
  useSavedApiConfig: document.getElementById('useSavedApiConfig'),
  savedApiConfigHint: document.getElementById('savedApiConfigHint'),
  apiHistoryModal: document.getElementById('apiHistoryModal'),
  closeApiHistoryModal: document.getElementById('closeApiHistoryModal'),
  apiHistoryList: document.getElementById('apiHistoryList'),
  apiHistoryStatus: document.getElementById('apiHistoryStatus'),
  fontModal: document.getElementById('fontModal'),
  closeFontModal: document.getElementById('closeFontModal'),
  saveFontConfig: document.getElementById('saveFontConfig'),
  fontFamilySelect: document.getElementById('fontFamilySelect'),
  fontSizeSelect: document.getElementById('fontSizeSelect'),
};

let state = { chats: [], activeId: null };
let rememberedApiConfig = null;
let rememberedApiHistory = [];
const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);
const escapeHtml = (text) => String(text ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('\"','&quot;').replaceAll("'",'&#039;');
function formatSimilarity(value, percentValue) {
  if (percentValue) return String(percentValue);
  const n = Number(value);
  if (!Number.isFinite(n)) return value ? String(value) : '未计算';
  const pct = n <= 1.5 ? n * 100 : n;
  return `${Math.max(0, Math.min(100, pct)).toFixed(0)}%`;
}
function normalizeBackendMessage(text) {
  const raw = String(text || '');
  const low = raw.trim().toLowerCase();
  if (low.startsWith('<!doctype html') || low.startsWith('<html') || low.includes('<div id="root"')) {
    return '后台返回的是网页 HTML，而不是模型回答。通常是 API 配置里的 Base URL 填成了平台首页、登录页或控制台地址。请把 Base URL 改为该平台文档提供的 OpenAI-compatible API 接口地址，例如 OpenRouter 使用 https://openrouter.ai/api/v1；4Router/其他平台需要使用其文档中的 /v1、/api/v1 或类似接口地址，然后重新“保存并测试”。';
  }
  return raw;
}

function renderAssistantText(text) {
  let html = escapeHtml(normalizeBackendMessage(text || ''));
  // 保留模型输出中的加粗语义，但不再使用红色重点标记。
  html = html.replace(/\*\*([^*]{1,120})\*\*/g, '<strong>$1</strong>');
  return html.replace(/\n/g, '<br>');
}

function currentChat() { return state.chats.find(c => c.id === state.activeId) || state.chats[0] || createChat(true); }
function createChat(activate = true) {
  const chat = { id: uid(), title: '新的病例对话', createdAt: Date.now(), updatedAt: Date.now(), patient: {}, caseConfirmed: false, attachments: [], messages: [] };
  state.chats.unshift(chat);
  if (activate) state.activeId = chat.id;
  saveChats(); renderHistory(); renderChat();
  return chat;
}
function saveChats() {
  const slim = state.chats.slice(0, 50).map(c => ({ ...c, messages: (c.messages || []).slice(-80), attachments: c.attachments || [], patient: c.patient || {} }));
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ chats: slim, activeId: state.activeId }));
}
function loadChats() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY) || localStorage.getItem('uscc_chat_history_v33') || localStorage.getItem('uscc_chat_history_v32') || localStorage.getItem('uscc_chat_history_v31') || localStorage.getItem('uscc_chat_history_v30') || localStorage.getItem('uscc_chat_history_v29') || localStorage.getItem('uscc_chat_history_v19') || localStorage.getItem('uscc_chat_history_v18') || localStorage.getItem('uscc_chat_history_v17') || localStorage.getItem('uscc_chat_history_v16') || localStorage.getItem('uscc_chat_history_v15') || localStorage.getItem('uscc_chat_history_v14') || localStorage.getItem('uscc_chat_history_v13') || localStorage.getItem('uscc_chat_history_v12') || localStorage.getItem('uscc_chat_history_v11') || localStorage.getItem('uscc_chat_history_v10') || localStorage.getItem('uscc_chat_history_v9') || localStorage.getItem('uscc_chat_history_v8') || localStorage.getItem('uscc_chat_history_v7') || localStorage.getItem('uscc_chat_history_v6') || localStorage.getItem('uscc_chat_history_v5') || localStorage.getItem('uscc_chat_history_v4') || localStorage.getItem('uscc_chat_history_v3') || localStorage.getItem('uscc_chat_history_v2');
    if (raw) {
      const parsed = JSON.parse(raw);
      state.chats = Array.isArray(parsed.chats) ? parsed.chats.map(c => ({ attachments: [], patient: {}, caseConfirmed: false, ...c })) : [];
      state.activeId = parsed.activeId || state.chats[0]?.id || null;
    }
  } catch (_) {}
  if (!state.chats.length) createChat(true);
}
function deleteChat(id) {
  const chat = state.chats.find(c => c.id === id);
  if (!chat) return;
  if (!confirm(`删除聊天记录：${chat.title || '病例对话'}？`)) return;
  state.chats = state.chats.filter(c => c.id !== id);
  if (state.activeId === id) state.activeId = state.chats[0]?.id || null;
  if (!state.chats.length) createChat(true);
  saveChats(); renderHistory(); renderChat();
}
function pickFirstMatch(text, patterns) {
  for (const pat of patterns) {
    const m = text.match(pat);
    if (m) return (m[1] || m[0] || '').trim();
  }
  return '';
}
function normalizeAge(value, text) {
  const fromPatient = String(value || '').match(/\d{1,3}/)?.[0] || '';
  const fromText = pickFirstMatch(text, [/(\d{1,3})\s*岁/, /年龄[:：]?\s*(\d{1,3})/]);
  return fromPatient || fromText;
}
function uniquePush(parts, value, maxLen = 18) {
  const v = String(value || '').replace(/\s+/g, '').replace(/[，,。；;]+$/g, '');
  if (!v) return;
  const clipped = v.length > maxLen ? v.slice(0, maxLen) + '…' : v;
  if (!parts.includes(clipped)) parts.push(clipped);
}
function inferPatientTitle(text, patient = {}) {
  const patientBlob = Object.values(patient || {}).filter(v => v !== null && v !== undefined).join(' ');
  const raw = String([text, patientBlob].filter(Boolean).join(' ')).replace(/\s+/g, ' ').trim();
  const parts = [];

  const age = normalizeAge(patient.age, raw);
  if (age) uniquePush(parts, `${age}岁`, 6);

  const sex = String(patient.sex || patient.gender || '');
  if (/男性|男/.test(raw) || /男/.test(sex)) uniquePush(parts, '男', 2);
  else if (/女性|女/.test(raw) || /女/.test(sex)) uniquePush(parts, '女', 2);

  const diagnosis = String(patient.diagnosis || patient['主要诊断'] || '');
  if (/SCC|鳞状细胞癌|鳞癌/i.test(raw + diagnosis)) uniquePush(parts, '尿道SCC', 8);
  else if (/尿道癌|尿道肿瘤/.test(raw + diagnosis)) uniquePush(parts, '尿道肿瘤', 8);

  if (/LS|硬化性苔藓|lichen sclerosus/i.test(raw)) uniquePush(parts, 'LS', 4);
  if (/尿道狭窄/.test(raw)) uniquePush(parts, '尿道狭窄', 8);
  if (/尿道肿物|肿块|占位|菜花样|溃疡/.test(raw)) uniquePush(parts, '尿道肿物', 8);

  const tnm = pickFirstMatch(raw, [/(T[0-4][a-c]?\s*N[0-3xX]?\s*M[0-1xX]?)/i, /(T[0-4][a-c]?)/i]);
  if (tnm) uniquePush(parts, tnm.toUpperCase().replace(/\s+/g, ''), 12);

  if (/淋巴结[^。；;，,]{0,12}(转移|阳性)|N[1-3]/i.test(raw)) uniquePush(parts, '淋巴结+', 8);
  else if (/淋巴结[^。；;，,]{0,12}(阴性|未见|无转移)|N0/i.test(raw)) uniquePush(parts, '淋巴结-', 8);

  const symptom = pickFirstMatch(raw, [/(排尿困难|血尿|尿痛|尿道流血|会阴疼痛|尿潴留|尿线变细|尿道分泌物)/]);
  if (symptom) uniquePush(parts, symptom, 8);

  const path = pickFirstMatch(raw, [/(高分化|中分化|低分化|原位癌|浸润性鳞癌|角化型鳞癌)/]);
  if (path) uniquePush(parts, path, 10);

  const treatment = pickFirstMatch(raw, [/(尿道切除|阴茎部分切除|阴茎全切|根治性切除|膀胱造瘘|放疗|化疗|免疫治疗|淋巴结清扫)/]);
  if (treatment) uniquePush(parts, treatment, 10);

  if (parts.length) return parts.slice(0, 8).join('｜');
  return raw ? raw.slice(0, 28) + (raw.length > 28 ? '…' : '') : '未命名病例讨论';
}
function refreshChatTitle(chat) {
  const userText = (chat.messages || []).filter(m => m.role === 'user').map(m => m.content).join(' ');
  chat.title = inferPatientTitle(userText, chat.patient || {});
}
function setActiveChat(id) { state.activeId = id; saveChats(); renderHistory(); renderChat(); els.sidebar.classList.remove('open'); }
function renderHistory() {
  els.historyList.innerHTML = '';
  for (const chat of state.chats) {
    const item = document.createElement('div');
    item.className = 'history-item-wrap' + (chat.id === state.activeId ? ' active' : '');
    const title = document.createElement('button');
    title.className = 'history-item';
    title.textContent = chat.title || '病例对话';
    title.onclick = () => setActiveChat(chat.id);
    const del = document.createElement('button');
    del.className = 'history-delete';
    del.title = '删除此聊天记录';
    del.textContent = '×';
    del.onclick = (e) => { e.stopPropagation(); deleteChat(chat.id); };
    item.appendChild(title); item.appendChild(del); els.historyList.appendChild(item);
  }
}
function renderChat() {
  const chat = currentChat();
  els.chatWindow.innerHTML = '';
  if (!chat.messages.length) {
    els.chatWindow.appendChild(els.emptyState);
    els.emptyState.style.display = 'block';
    return;
  }
  els.emptyState.style.display = 'none';
  for (const msg of chat.messages) renderMessage(msg);
  scrollToBottom();
}
function renderMessage(msg) {
  const row = document.createElement('div');
  row.className = `message-row ${msg.role === 'user' ? 'user' : 'assistant'}`;
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  const content = document.createElement('div');
  content.innerHTML = msg.role === 'assistant' ? renderAssistantText(msg.content || '') : escapeHtml(msg.content || '').replace(/\n/g, '<br>');
  bubble.appendChild(content);
  if (msg.attachments?.length) bubble.appendChild(renderAttachments(msg.attachments));
  if (msg.report?.similar_cases?.length) bubble.appendChild(renderCaseLinks(msg.report.similar_cases));
  if (msg.candidates?.length) bubble.appendChild(renderCandidateLinks(msg.candidates));
  if (msg.report?.related_articles?.length) bubble.appendChild(renderArticleLinks(msg.report.related_articles));
  row.appendChild(bubble); els.chatWindow.appendChild(row);
}
function renderAttachments(files) {
  const wrap = document.createElement('div'); wrap.className = 'attachment-list';
  for (const f of files) {
    const a = document.createElement('a'); a.className = 'attachment-chip'; a.href = f.url || '#'; a.target = '_blank';
    a.textContent = f.type === 'image' ? `图片：${f.filename}` : `文件：${f.filename}`;
    wrap.appendChild(a);
  }
  return wrap;
}
function renderCaseLinks(cases) {
  const wrap = document.createElement('div'); wrap.className = 'case-links';
  const title = document.createElement('div'); title.className = 'case-links-title'; title.textContent = '相似病例与治疗转归'; wrap.appendChild(title);
  for (const c of cases.slice(0, 4)) {
    const a = document.createElement('a');
    a.className = 'case-link-card'; a.href = `/case/${encodeURIComponent(c.case_id)}`; a.target = '_blank';
    const ev = (c.evidence_summary || []).slice(0, 2).join('；');
    a.innerHTML = `<b>${escapeHtml(c.case_id)}｜${escapeHtml(c.sheet)}｜相似度 ${escapeHtml(formatSimilarity(c.similarity, c.similarity_percent))}</b><small>${escapeHtml(c.diagnosis || '诊断未记录')}</small><small>${escapeHtml(ev || '点击查看病例详情')}</small>`;
    wrap.appendChild(a);
  }
  return wrap;
}


function renderCandidateLinks(candidates) {
  const chat = currentChat();
  const wrap = document.createElement('div'); wrap.className = 'case-links candidate-links';
  const allCandidates = (candidates || []).slice(0, 2000);
  const title = document.createElement('div'); title.className = 'case-links-title'; title.textContent = `候选患者确认（${allCandidates.length} 条）`; wrap.appendChild(title);
  for (const c of allCandidates) {
    const card = document.createElement('div');
    const selected = chat.selectedCandidateId && chat.selectedCandidateId === c.candidate_id;
    card.className = `case-link-card candidate-link-card selectable-candidate ${selected ? 'selected' : ''}`;
    const info = [c.age ? `${c.age}岁` : '', c.sex, c.diagnosis, c.tnm].filter(Boolean).join('｜');
    const desc = [c.history, c.symptoms, c.pathology, c.surgery].filter(Boolean).join('；').slice(0, 120);
    const btnText = selected ? '✓ 已选择' : '选择该患者';
    card.innerHTML = `<div class="candidate-card-main"><b>${escapeHtml(c.display_title || c.candidate_id || '候选病例')}</b><small>${escapeHtml(info || '基础信息待确认')}｜匹配度 ${escapeHtml(c.match_score || '')}</small><small>${escapeHtml(desc || '该行病例信息待医生确认')}</small></div><button type="button" class="candidate-confirm-btn">${btnText}</button>`;
    const btn = card.querySelector('.candidate-confirm-btn');
    btn.addEventListener('click', (e) => {
      e.preventDefault(); e.stopPropagation();
      selectCandidateInChat(c);
    });
    wrap.appendChild(card);
  }
  return wrap;
}

function selectCandidateInChat(c) {
  const chat = currentChat();
  chat.selectedCandidateId = c.candidate_id || '';
  const merged = { ...(chat.patient || {}) };
  for (const k of ['name','sex','age','diagnosis','ls','tnm','lymph_node','history','symptoms','tumor','imaging','pathology','surgery','other_treatment','followup','free_text']) {
    if (c[k]) merged[k] = c[k];
  }
  chat.patient = merged;
  chat.caseConfirmed = true;
  refreshChatTitle(chat);
  saveChats();
  renderHistory();
  renderChat();
  analyzeSelectedCandidate(c);
}

async function analyzeSelectedCandidate(c) {
  const chat = currentChat();
  const typing = addMessage('assistant', '已选择该患者，正在检索病例、文献并生成初步分析……');
  try {
    const res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
      question: '请基于医生已选择的患者进行总体分析，检索相似病例和可参考文献，并给出下一步讨论方向。',
      mode: 'initial_patient_analysis',
      patient: chat.patient || {},
      has_confirmed_case: true,
      history: chat.messages.slice(-18).map(m => ({ role: m.role, content: m.content })),
      attachments: chat.attachments || [],
      ...apiPayloadExtras(),
    })});
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || '后端返回错误');
    let answerText = normalizeBackendMessage(data.llm?.answer || '系统没有生成回答。');
    if (data.llm?.provider && data.llm.provider.startsWith('local_fallback')) {
      if (data.llm.error) answerText += `

（后台 AI 调用失败，已使用本地知识库回答：${data.llm.error}）`;
      else if (!(localStorage.getItem(API_KEY_STORAGE) || '').trim()) answerText += `

（当前未配置 API Key，因此使用本地知识库兜底回答；配置后会调用所选 AI 模型。）`;
    }
    replaceMessage(typing.id, { content: answerText, report: data.report, candidates: [] });
  } catch (err) {
    replaceMessage(typing.id, { content: `分析失败：${err.message}` });
  }
}

function renderArticleLinks(articles) {
  const wrap = document.createElement('div'); wrap.className = 'case-links article-links';
  const title = document.createElement('div'); title.className = 'case-links-title'; title.textContent = '可参考文献'; wrap.appendChild(title);
  for (const a of (articles || []).slice(0, 4)) {
    const link = a.article_url || (a.article_id ? `/article/${encodeURIComponent(a.article_id)}` : (a.source_url || '#'));
    const card = document.createElement('a');
    card.className = 'case-link-card article-link-card'; card.href = link; card.target = '_blank';
    const meta = [a.article_id, a.journal, a.year].filter(Boolean).join('｜');
    const hits = (a.hit_terms || []).slice(0, 6).join('、');
    const point = ((a.value_points || [])[0] || '').slice(0, 90);
    const source = a.source_url ? `<small>含原文件，可点开查看</small>` : '';
    card.innerHTML = `<b>${escapeHtml(a.title || '未命名文献')}</b>
      <small>${escapeHtml(meta || '点击查看文章详情')}</small>
      <small>${a.low_confidence ? '匹配较弱，仅作补充查看' : '可参考' + (hits ? '：' + escapeHtml(hits) : '')}</small>
      ${point ? `<small>${escapeHtml(point)}</small>` : ''}
      ${source}`;
    wrap.appendChild(card);
  }
  return wrap;
}

function addMessage(role, content, extra = {}) {
  const chat = currentChat();
  const msg = { id: uid(), role, content, ...extra };
  chat.messages.push(msg); chat.updatedAt = Date.now();
  if (role === 'user') refreshChatTitle(chat);
  if (extra.patient) { chat.patient = { ...(chat.patient || {}), ...extra.patient }; refreshChatTitle(chat); }
  saveChats(); renderHistory(); renderChat(); return msg;
}
function replaceMessage(id, patch) {
  const chat = currentChat();
  const idx = chat.messages.findIndex(m => m.id === id);
  if (idx >= 0) { chat.messages[idx] = { ...chat.messages[idx], ...patch }; saveChats(); renderChat(); }
}
function scrollToBottom() { requestAnimationFrame(() => { els.chatWindow.scrollTop = els.chatWindow.scrollHeight; }); }
function resizeInput() { els.input.style.height = 'auto'; els.input.style.height = Math.min(190, els.input.scrollHeight) + 'px'; }
function looksLikeDetailedCaseText(text) {
  const raw = String(text || '').trim();
  const markers = ['年龄','性别','诊断','病史','症状','影像','CT','MRI','病理','TNM','淋巴结','手术史'];
  const hits = markers.filter(marker => raw.toLowerCase().includes(marker.toLowerCase())).length;
  return raw.length >= 80 && hits >= 3;
}
function updatePatientFromExplicitText(text) {
  const chat = currentChat();
  const raw = String(text || '').trim();
  const explicit = raw.match(/^(?:补充病例|更新病例|病例信息)[：:]\s*([\s\S]+)/);
  const caseText = explicit ? explicit[1].trim() : (looksLikeDetailedCaseText(raw) ? raw : '');
  if (!caseText) return false;
  const old = chat.patient?.free_text || '';
  chat.patient = { ...(chat.patient || {}), free_text: [old, caseText].filter(Boolean).join('\n') };
  chat.caseConfirmed = true;
  refreshChatTitle(chat);
  return true;
}
function apiPayloadExtras() {
  const provider = localStorage.getItem(API_PROVIDER_STORAGE) || 'openai';
  const storedModel = localStorage.getItem(API_MODEL_STORAGE) || '';
  const customModel = localStorage.getItem(API_CUSTOM_MODEL_STORAGE) || '';
  return {
    api_key: localStorage.getItem(API_KEY_STORAGE) || '',
    provider,
    base_url: localStorage.getItem(API_BASE_URL_STORAGE) || '',
    model: storedModel === '__custom__' ? customModel : storedModel,
  };
}
async function sendMessage() {
  const text = els.input.value.trim(); if (!text) return;
  els.input.value = ''; resizeInput(); updatePatientFromExplicitText(text);
  const chat = currentChat();
  addMessage('user', text);
  const typing = addMessage('assistant', '正在理解问题并调用后台 AI 生成回答……');
  els.sendBtn.disabled = true;
  try {
    const res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
      question: text,
      patient: chat.patient || {},
      has_confirmed_case: Boolean(chat.caseConfirmed),
      history: chat.messages.slice(-18).map(m => ({ role: m.role, content: m.content })),
      attachments: chat.attachments || [],
      ...apiPayloadExtras(),
    })});
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || '后端返回错误');
    const hasCandidateBatch = (chat.attachments || []).some(a => a.type === 'candidate_case_batch');
    const asksMatch = /候选|匹配|哪个病人|哪位患者|查找患者|识别患者|选择患者|住院号|姓名|年龄/.test(text);
    const shouldShowCandidates = !chat.selectedCandidateId && hasCandidateBatch && asksMatch && data.report?.candidate_matches?.length;
    let answerText = normalizeBackendMessage(data.llm?.answer || '系统没有生成回答。');
    if (data.llm?.provider && data.llm.provider.startsWith('local_fallback')) {
      if (data.llm.error) answerText += `\n\n（后台 AI 调用失败，已使用本地知识库回答：${data.llm.error}）`;
      else if (!(localStorage.getItem(API_KEY_STORAGE) || '').trim()) answerText += '\n\n（当前未配置 API Key，因此使用本地知识库兜底回答；配置后会调用所选 AI 模型。）';
    }
    replaceMessage(typing.id, { content: answerText, report: data.report, candidates: shouldShowCandidates ? data.report.candidate_matches : [] });
  } catch (err) {
    replaceMessage(typing.id, { content: `请求失败：${err.message}\n请确认 Flask 后端仍在运行。` });
  } finally { els.sendBtn.disabled = false; els.input.focus(); }
}
async function uploadFile(file) {
  const chat = currentChat();
  const fd = new FormData(); fd.append('file', file);
  els.uploadStatus.textContent = `正在上传：${file.name}`;
  try {
    const res = await fetch('/api/upload', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || data.note || '上传失败');
    const attachment = { filename: data.filename, stored_as: data.stored_as, url: data.url, type: data.type, batch_id: data.batch_id, candidate_count: data.candidate_count };
    chat.attachments = [...(chat.attachments || []), attachment];
    if (data.fields && Object.keys(data.fields).length) {
      chat.patient = { ...(chat.patient || {}), ...data.fields };
      const clinicalKeys = ['age','sex','diagnosis','history','symptoms','tumor','imaging','pathology','tnm','lymph_node'];
      chat.caseConfirmed = clinicalKeys.filter(key => String(data.fields[key] || '').trim()).length >= 3;
      refreshChatTitle(chat);
    }
    saveChats();
    const fieldNames = Object.keys(data.fields || {}).join('、');
    let text = fieldNames ? `已读取病例文件：${data.filename}
自动识别字段：${fieldNames}
已纳入当前对话。` : `已上传：${data.filename}
${data.note || ''}`;
    let candidates = [];
    if (data.type === 'candidate_case_batch') {
      candidates = data.candidate_preview || [];
      text = `已读取病例数据表：${data.filename}
识别到 ${data.candidate_count || candidates.length || 0} 条候选病例。请先在下方选择当前患者；选择后系统会在本对话内生成初步分析，之后医生可继续追问。`;
    }
    addMessage('assistant', text, { attachments: [attachment], patient: data.fields || {}, candidates });
    els.uploadStatus.textContent = data.note || '上传完成。';
  } catch (err) { els.uploadStatus.textContent = `上传失败：${err.message}`; addMessage('assistant', `上传失败：${err.message}`); }
  finally { els.fileInput.value = ''; }
}
async function addCurrentCase() {
  const chat = currentChat();
  const text = (chat.messages || []).filter(m => m.role === 'user').map(m => m.content).join('\n');
  if (!text.trim() && !Object.keys(chat.patient || {}).length) { addMessage('assistant', '当前对话还没有可加入知识库的病例内容。'); return; }
  const res = await fetch('/api/add_case', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ fields: { ...(chat.patient || {}), medical_images: (chat.attachments || []).filter(a => a.type === 'image') }, source_text: text }) });
  const data = await res.json();
  if (!res.ok || !data.ok) { addMessage('assistant', `添加失败：${data.error || '未知错误'}`); return; }
  addMessage('assistant', `${data.message}\n可在左侧“病例知识库”中查看。`);
  loadSummary();
}
async function loadSummary() {
  try {
    const res = await fetch('/api/summary'); const data = await res.json();
    const groups = Object.entries(data.sheets || {}).map(([k,v]) => `${k} ${v}`).join('｜');
    els.kbSummary.innerHTML = `病例总数：${escapeHtml(data.total_cases)}｜文章 ${escapeHtml(data.articles || 0)}<br>${escapeHtml(groups || '暂无分组')}`;
  } catch (_) { els.kbSummary.textContent = '知识库读取失败'; }
}

const API_PROVIDER_CONFIG = {
  openai: {
    baseUrl: '',
    models: ['gpt-4.1-mini','gpt-4.1','gpt-4.1-nano','gpt-4o-mini','gpt-4o','o4-mini','o3','gpt-5-mini','gpt-5']
  },
  deepseek: {
    baseUrl: 'https://api.deepseek.com',
    models: ['deepseek-chat','deepseek-reasoner','deepseek-v3','deepseek-v3.1','deepseek-v4','__custom__']
  },
  dashscope: {
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: ['qwen-plus','qwen-max','qwen-turbo','qwen-long','qwen-vl-plus','qwen3-max','qwen3-plus','__custom__']
  },
  zhipu: {
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    models: ['glm-4-flash','glm-4-plus','glm-4-air','glm-4v-plus','glm-4.5','glm-4.5-flash','__custom__']
  },
  siliconflow: {
    baseUrl: 'https://api.siliconflow.cn/v1',
    models: ['deepseek-ai/DeepSeek-V3','deepseek-ai/DeepSeek-R1','Qwen/Qwen2.5-72B-Instruct','Qwen/Qwen2.5-VL-72B-Instruct','__custom__']
  },
  moonshot: {
    baseUrl: 'https://api.moonshot.cn/v1',
    models: ['moonshot-v1-8k','moonshot-v1-32k','moonshot-v1-128k','kimi-k2-0711-preview','kimi-latest','__custom__']
  },
  openrouter: {
    baseUrl: 'https://openrouter.ai/api/v1',
    models: ['openai/gpt-4o-mini','openai/gpt-4.1-mini','deepseek/deepseek-chat','deepseek/deepseek-r1','anthropic/claude-3.5-sonnet','google/gemini-2.0-flash','__custom__']
  },
  volcengine: {
    baseUrl: 'https://ark.cn-beijing.volces.com/api/v3',
    models: ['doubao-1-5-pro-32k','doubao-1-5-lite-32k','doubao-seed-1-6','doubao-seed-1-6-thinking','__custom__']
  },
  anthropic: {
    baseUrl: 'https://api.anthropic.com',
    models: ['claude-opus-4-7','claude-sonnet-4-6','claude-haiku-4-5-20251001','claude-opus-4-6','claude-sonnet-4-5','claude-3-7-sonnet-latest','claude-3-5-sonnet-latest','__custom__']
  },
  fourrouter: {
    baseUrl: '',
    models: ['__custom__']
  },
  custom: {
    baseUrl: '',
    models: ['__custom__']
  }
};
function refreshApiModelOptions(provider, selected = '') {
  const cfg = API_PROVIDER_CONFIG[provider] || API_PROVIDER_CONFIG.openai;
  if (!els.apiModelSelect) return;
  els.apiModelSelect.innerHTML = '';
  for (const m of cfg.models) {
    const opt = document.createElement('option');
    opt.value = m;
    opt.textContent = m === '__custom__' ? '自定义模型名称' : m;
    els.apiModelSelect.appendChild(opt);
  }
  els.apiModelSelect.value = selected && cfg.models.includes(selected) ? selected : cfg.models[0];
  toggleCustomModelInput();
}
function toggleCustomModelInput() {
  if (!els.apiCustomModelInput || !els.apiModelSelect) return;
  const custom = els.apiModelSelect.value === '__custom__';
  els.apiCustomModelInput.style.display = custom ? 'block' : 'none';
}
async function fetchRememberedApiConfig() {
  try {
    const res = await fetch('/api/llm/config', {cache:'no-store'});
    const data = await res.json();
    if (res.ok && data.ok) {
      rememberedApiConfig = data.config || null;
      rememberedApiHistory = Array.isArray(data.history) ? data.history : [];
      if (rememberedApiConfig?.provider) {
        localStorage.setItem(API_PROVIDER_STORAGE, rememberedApiConfig.provider || 'openai');
        localStorage.setItem(API_MODEL_STORAGE, rememberedApiConfig.model || '');
        localStorage.setItem(API_BASE_URL_STORAGE, rememberedApiConfig.base_url || '');
      }
      const hint = rememberedApiConfig?.provider ? `已记住：${rememberedApiConfig.provider} / ${rememberedApiConfig.model || '未选模型'}${rememberedApiConfig.api_key_masked ? ' / ' + rememberedApiConfig.api_key_masked : ''}` : '当前后端未记住 API 配置。';
      if (els.savedApiConfigHint) els.savedApiConfigHint.textContent = hint;
      return rememberedApiConfig;
    }
  } catch (_) {}
  if (els.savedApiConfigHint) els.savedApiConfigHint.textContent = '当前后端未记住 API 配置。';
  rememberedApiConfig = null;
  rememberedApiHistory = [];
  return null;
}

function fillApiModalFromConfig(cfg, note='') {
  if (!cfg) return;
  if (els.apiProviderSelect) els.apiProviderSelect.value = cfg.provider || 'openai';
  refreshApiModelOptions(cfg.provider || 'openai', cfg.model || '');
  if (els.apiModelSelect) {
    const opts = [...els.apiModelSelect.options].map(o => o.value);
    if (cfg.model && opts.includes(cfg.model)) {
      els.apiModelSelect.value = cfg.model;
    } else if (cfg.model) {
      els.apiModelSelect.value = '__custom__';
      if (els.apiCustomModelInput) els.apiCustomModelInput.value = cfg.model;
    }
  }
  if (els.apiBaseUrlInput) els.apiBaseUrlInput.value = cfg.base_url || '';
  if (els.apiKeyInput) els.apiKeyInput.value = '';
  if (els.apiKeyStatus) els.apiKeyStatus.textContent = note || `已调用已记住配置：${cfg.provider || ''} / ${cfg.model || ''}。API Key 已由后端记住，无需重新输入；若要更换 Key，再手动填写后保存即可。`;
}

function renderApiHistoryList() {
  if (!els.apiHistoryList) return;
  els.apiHistoryList.innerHTML = '';
  const rows = rememberedApiHistory || [];
  if (!rows.length) {
    els.apiHistoryList.innerHTML = '<div class="modal-status">暂无已成功连接的配置。未连接成功的配置已自动清理；请先保存并测试一次 API。</div>';
    return;
  }
  for (const cfg of rows) {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'api-history-item';
    const title = [cfg.provider, cfg.model].filter(Boolean).join(' / ') || '未命名配置';
    const meta = [cfg.api_key_masked, cfg.base_url, cfg.updated_at].filter(Boolean).join(' ｜ ');
    item.innerHTML = `<b>${escapeHtml(title)}</b><small>${escapeHtml(meta)}</small>`;
    item.addEventListener('click', () => useRememberedApiConfig(cfg.config_id));
    els.apiHistoryList.appendChild(item);
  }
}

async function openApiHistoryModal() {
  await fetchRememberedApiConfig();
  renderApiHistoryList();
  if (els.apiHistoryModal) {
    els.apiHistoryModal.hidden = false;
    document.body.classList.add('modal-open');
  }
}
function closeApiHistoryModal() {
  if (els.apiHistoryModal) els.apiHistoryModal.hidden = true;
  document.body.classList.remove('modal-open');
}

async function useRememberedApiConfig(configId) {
  if (!configId) {
    if (els.apiHistoryStatus) els.apiHistoryStatus.textContent = '该配置缺少编号，无法调用。';
    return;
  }
  if (els.apiHistoryStatus) els.apiHistoryStatus.textContent = '正在切换配置...';
  try {
    const res = await fetch('/api/llm/config/use', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({config_id: configId})});
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || '切换失败');
    rememberedApiConfig = data.config || null;
    fillApiModalFromConfig(rememberedApiConfig, data.message || '已切换到该 API 配置。');
    await fetchRememberedApiConfig();
    closeApiHistoryModal();
  } catch (err) {
    if (els.apiHistoryStatus) els.apiHistoryStatus.textContent = `切换失败：${err.message}`;
  }
}

function applyRememberedApiConfig() {
  if ((rememberedApiHistory || []).length > 1) {
    openApiHistoryModal();
    return;
  }
  const cfg = rememberedApiConfig || (rememberedApiHistory || [])[0];
  if (!cfg) {
    if (els.apiKeyStatus) els.apiKeyStatus.textContent = '当前没有可调用的已记住配置。';
    return;
  }
  fillApiModalFromConfig(cfg);
}

function refreshBaseUrlForProvider() {
  const provider = els.apiProviderSelect?.value || 'openai';
  const savedBase = localStorage.getItem(API_BASE_URL_STORAGE) || rememberedApiConfig?.base_url || '';
  const cfg = API_PROVIDER_CONFIG[provider] || API_PROVIDER_CONFIG.openai;
  if (els.apiBaseUrlInput) els.apiBaseUrlInput.value = provider === 'custom' ? savedBase : (savedBase || cfg.baseUrl || '');
}
async function openApiModal() {
  await fetchRememberedApiConfig();
  const provider = localStorage.getItem(API_PROVIDER_STORAGE) || rememberedApiConfig?.provider || 'openai';
  els.apiKeyInput.value = localStorage.getItem(API_KEY_STORAGE) || '';
  if (els.apiProviderSelect) els.apiProviderSelect.value = provider;
  refreshApiModelOptions(provider, localStorage.getItem(API_MODEL_STORAGE) || rememberedApiConfig?.model || '');
  refreshBaseUrlForProvider();
  if (els.apiCustomModelInput) els.apiCustomModelInput.value = localStorage.getItem(API_CUSTOM_MODEL_STORAGE) || '';
  els.apiKeyStatus.textContent = rememberedApiConfig?.provider
    ? `当前已记住：${rememberedApiConfig.provider} / ${rememberedApiConfig.model || '未选模型'}${rememberedApiConfig.api_key_masked ? ' / ' + rememberedApiConfig.api_key_masked : ''}。`
    : (localStorage.getItem(API_KEY_STORAGE) ? `当前浏览器已保存 ${provider} API Key。` : '当前未配置 API Key，系统将使用本地兜底回答。');
  els.apiModal.hidden = false;
  document.body.classList.add('modal-open');
  els.apiKeyInput.focus();
}
function closeApiModal() { els.apiModal.hidden = true; document.body.classList.remove('modal-open'); }
function collectApiConfigFromModal() {
  const provider = els.apiProviderSelect?.value || 'openai';
  const selectedModel = els.apiModelSelect?.value || '';
  const customModel = els.apiCustomModelInput?.value.trim() || '';
  return {
    api_key: els.apiKeyInput.value.trim(),
    provider,
    model: selectedModel === '__custom__' ? customModel : selectedModel,
    selected_model: selectedModel,
    custom_model: customModel,
    base_url: els.apiBaseUrlInput?.value.trim() || '',
  };
}
async function testApiConnection() {
  const cfg = collectApiConfigFromModal();
  if (!cfg.api_key) { els.apiKeyStatus.textContent = '请先填写 API Key。'; return false; }
  if (!cfg.model) { els.apiKeyStatus.textContent = '请先选择或填写模型。'; return false; }
  els.apiKeyStatus.textContent = '正在联系后台并测试供应商接口...';
  try {
    const res = await fetch('/api/llm/test', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(cfg)});
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || '连接失败');
    els.apiKeyStatus.textContent = `连接成功：${data.provider} / ${data.model}`;
    return true;
  } catch (err) {
    els.apiKeyStatus.textContent = `连接失败：${err.message}`;
    return false;
  }
}
async function saveApiConfig() {
  const cfg = collectApiConfigFromModal();
  if (cfg.api_key) localStorage.setItem(API_KEY_STORAGE, cfg.api_key);
  localStorage.setItem(API_PROVIDER_STORAGE, cfg.provider);
  localStorage.setItem(API_MODEL_STORAGE, cfg.selected_model);
  localStorage.setItem(API_BASE_URL_STORAGE, cfg.base_url);
  localStorage.setItem(API_CUSTOM_MODEL_STORAGE, cfg.custom_model);
  els.apiKeyStatus.textContent = cfg.api_key ? `正在保存到本地 Flask 后端并测试 ${cfg.provider}...` : `未填写 Key，仅保存浏览器模型配置。`;
  if (!cfg.api_key) return;
  try {
    const res = await fetch('/api/llm/config', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(cfg)});
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || '后端保存失败');
    if (data.test?.ok) els.apiKeyStatus.textContent = `后端连接成功：${data.test.provider} / ${data.test.model}，已保存到历史配置。`;
    else els.apiKeyStatus.textContent = `连接失败，未保存该配置：${data.test?.error || data.message || '未知错误'}`;
    await fetchRememberedApiConfig();
  } catch (err) {
    els.apiKeyStatus.textContent = `保存/连接失败：${err.message}`;
  }
}
async function clearApiConfig() {
  localStorage.removeItem(API_KEY_STORAGE); localStorage.removeItem(API_MODEL_STORAGE); localStorage.removeItem(API_PROVIDER_STORAGE); localStorage.removeItem(API_BASE_URL_STORAGE); localStorage.removeItem(API_CUSTOM_MODEL_STORAGE);
  els.apiKeyInput.value = ''; if (els.apiProviderSelect) els.apiProviderSelect.value = 'openai';
  refreshApiModelOptions('openai', 'gpt-4.1-mini'); refreshBaseUrlForProvider();
  if (els.apiCustomModelInput) els.apiCustomModelInput.value = '';
  els.apiKeyStatus.textContent = '正在同时清除后端 API 配置...';
  try {
    const res = await fetch('/api/llm/config', { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || '后端清除失败');
    rememberedApiConfig = null;
  rememberedApiHistory = [];
    if (els.savedApiConfigHint) els.savedApiConfigHint.textContent = '当前后端未记住 API 配置。';
    els.apiKeyStatus.textContent = '已清除浏览器与后端 API 配置。现在会使用本地知识库兜底模式。';
  } catch (err) {
    els.apiKeyStatus.textContent = `浏览器配置已清除，但后端清除失败：${err.message}`;
  }
}

async function loadMascot() {
  try {
    const res = await fetch('/api/settings/mascot', {cache:'no-store'});
    const data = await res.json();
    if (data.ok && data.url) {
      document.querySelectorAll('.mascot-img').forEach(img => { img.src = data.url; });
    }
  } catch (_) {}
}
async function uploadMascotImage(file) {
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
  els.apiKeyStatus.textContent = '正在上传吉祥物图片...';
  try {
    const res = await fetch('/api/settings/mascot', {method:'POST', body:fd});
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || '上传失败');
    document.querySelectorAll('.mascot-img').forEach(img => { img.src = data.url; });
    els.apiKeyStatus.textContent = '吉祥物图片已更新。';
  } catch (err) {
    els.apiKeyStatus.textContent = `吉祥物更新失败：${err.message}`;
  } finally {
    if (els.mascotFileInput) els.mascotFileInput.value = '';
  }
}

const FONT_FAMILY_STORAGE = 'uscc_font_family';
const FONT_SIZE_STORAGE = 'uscc_font_size_px';
function applyFontSettings() {
  const family = localStorage.getItem(FONT_FAMILY_STORAGE) || 'system';
  const size = localStorage.getItem(FONT_SIZE_STORAGE) || '16';
  document.body.classList.remove('font-system','font-yahei','font-songti','font-heiti','font-arial','font-small','font-normal','font-large','font-xlarge');
  document.body.classList.add(`font-${family}`);
  document.body.style.fontSize = `${Number(size) || 16}px`;
  if (els.fontFamilySelect) els.fontFamilySelect.value = family;
  if (els.fontSizeSelect) els.fontSizeSelect.value = String(size);
}
function openFontModal() {
  applyFontSettings();
  if (els.fontModal) {
    els.fontModal.hidden = false;
    document.body.classList.add('modal-open');
  }
}
function closeFontModal() {
  if (els.fontModal) els.fontModal.hidden = true;
  document.body.classList.remove('modal-open');
}
function saveFontSettings() {
  if (els.fontFamilySelect) localStorage.setItem(FONT_FAMILY_STORAGE, els.fontFamilySelect.value || 'system');
  if (els.fontSizeSelect) localStorage.setItem(FONT_SIZE_STORAGE, els.fontSizeSelect.value || '16');
  applyFontSettings();
  closeFontModal();
}

els.sendBtn.addEventListener('click', sendMessage);
els.input.addEventListener('input', resizeInput);
els.input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }});
els.newChatBtn.addEventListener('click', () => {
  const chat = currentChat();
  const hasContent = (chat.messages || []).length > 0 || Object.values(chat.patient || {}).some(v => String(v || '').trim()) || (chat.attachments || []).length > 0;
  if (hasContent) createChat(true);
  els.input.focus();
});
els.addCurrentCaseBtn.addEventListener('click', addCurrentCase);
els.fileInput.addEventListener('change', e => { const file = e.target.files?.[0]; if (file) uploadFile(file); });
els.mobileMenuBtn.addEventListener('click', () => els.sidebar.classList.toggle('open'));
els.apiKeyBtn.addEventListener('click', () => { openApiModal(); });
els.closeApiModal.addEventListener('click', closeApiModal);
els.apiModal.addEventListener('click', e => { if (e.target === els.apiModal) closeApiModal(); });
els.saveApiKey.addEventListener('click', saveApiConfig);
els.testApiKey?.addEventListener('click', testApiConnection);
els.clearApiKey.addEventListener('click', clearApiConfig);
els.useSavedApiConfig?.addEventListener('click', applyRememberedApiConfig);
els.closeApiHistoryModal?.addEventListener('click', closeApiHistoryModal);
els.apiHistoryModal?.addEventListener('click', e => { if (e.target === els.apiHistoryModal) closeApiHistoryModal(); });
els.apiProviderSelect?.addEventListener('change', () => { const p = els.apiProviderSelect.value; refreshApiModelOptions(p); localStorage.removeItem(API_BASE_URL_STORAGE); refreshBaseUrlForProvider(); });
els.apiModelSelect?.addEventListener('change', toggleCustomModelInput);
els.fontSettingsBtn?.addEventListener('click', openFontModal);
els.closeFontModal?.addEventListener('click', closeFontModal);
els.fontModal?.addEventListener('click', e => { if (e.target === els.fontModal) closeFontModal(); });
els.saveFontConfig?.addEventListener('click', saveFontSettings);
document.querySelectorAll('[data-prompt]').forEach(btn => btn.addEventListener('click', () => { els.input.value = btn.dataset.prompt; resizeInput(); els.input.focus(); }));

applyFontSettings(); loadMascot(); fetchRememberedApiConfig(); loadChats(); renderHistory(); renderChat(); loadSummary(); resizeInput();
