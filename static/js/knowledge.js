const caseList = document.getElementById('caseList');
const sheetFilter = document.getElementById('sheetFilter');
const caseSearch = document.getElementById('caseSearch');
let currentCases = [];
const escapeHtml = (text) => String(text ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
let searchTimer = null;

async function loadGroups() {
  try {
    const res = await fetch('/api/summary', { cache: 'no-store' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || '分组读取失败');
    const current = sheetFilter.value;
    sheetFilter.innerHTML = '<option value="">全部分组</option>';
    for (const [sheet, count] of Object.entries(data.sheets || {})) {
      const opt = document.createElement('option');
      opt.value = sheet;
      opt.textContent = `${sheet}（${count}）`;
      sheetFilter.appendChild(opt);
    }
    if ([...sheetFilter.options].some(o => o.value === current)) sheetFilter.value = current;
  } catch (err) {
    sheetFilter.innerHTML = '<option value="">全部分组</option>';
  }
}

function safeAge(age) {
  if (age === null || age === undefined || age === '' || Number.isNaN(Number(age))) return '';
  return String(Number(age)).replace(/\.0$/, '') + '岁';
}

function renderCases(cases) {
  currentCases = Array.isArray(cases) ? cases : [];
  if (!cases.length) {
    caseList.innerHTML = '<div class="empty-card">未找到病例。可换用“鳞癌 / SCC / LS / 尿道狭窄 / 病理 / 手术”等关键词，或切换分组。</div>';
    return;
  }
  caseList.innerHTML = cases.map(c => {
    const info = [safeAge(c.age), c.sex, c.ls, c.tnm, c.lymph_node].filter(Boolean).join('｜');
    const summary = [c.symptoms, c.tumor, c.pathology, c.imaging].filter(Boolean).join('｜').slice(0, 220);
    const treatment = [
      c.surgery ? '手术：' + c.surgery : '',
      c.other_treatment ? '其他治疗：' + c.other_treatment : '',
      c.followup ? '随访：' + c.followup : ''
    ].filter(Boolean).join('\n');
    const editableLabel = String(c.case_id || '').startsWith('USER-');
    return `
      <article class="knowledge-case-card">
        <a href="/case/${encodeURIComponent(c.case_id)}">
          <b>${escapeHtml(c.case_id)}｜<span class="case-group-label">${escapeHtml(c.sheet)}</span></b>
          <span>${escapeHtml(c.diagnosis || '诊断未记录')}</span>
          <small>${escapeHtml(info || '基础信息未记录')}</small>
          <small>${escapeHtml(summary || '点击查看病例详情')}</small>
          ${treatment ? `<div class="treatment-block">${escapeHtml(treatment).replace(/\n/g, '<br>')}</div>` : ''}
        </a>
        <div class="case-card-actions">
          <a class="case-open-btn" href="/case/${encodeURIComponent(c.case_id)}">查看详情</a>
          ${editableLabel ? `<button class="case-label-btn" data-case-id="${escapeHtml(c.case_id)}" data-label="${escapeHtml(c.sheet || '')}">编辑标签</button>` : ''}
          <button class="case-delete-btn" data-case-id="${escapeHtml(c.case_id)}">删除病例</button>
        </div>
      </article>`;
  }).join('');
  document.querySelectorAll('.case-delete-btn').forEach(btn => btn.addEventListener('click', deleteCase));
  document.querySelectorAll('.case-label-btn').forEach(btn => btn.addEventListener('click', editCaseLabel));
}

async function loadCases() {
  caseList.innerHTML = '<div class="empty-card">正在读取病例...</div>';
  const q = caseSearch.value.trim();
  const sheet = sheetFilter.value;
  const url = `/api/cases?limit=500&q=${encodeURIComponent(q)}&sheet=${encodeURIComponent(sheet)}`;
  try {
    const res = await fetch(url, { cache: 'no-store' });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || '读取失败');
    renderCases(data.cases || []);
  } catch (err) {
    caseList.innerHTML = `<div class="empty-card">病例读取失败：${escapeHtml(err.message)}<br>请确认 Flask 后端正在运行，并尝试刷新页面。</div>`;
  }
}



async function editCaseLabel(event) {
  event.preventDefault(); event.stopPropagation();
  const caseId = event.currentTarget.dataset.caseId;
  const oldLabel = event.currentTarget.dataset.label || '用户新增';
  const input = prompt(`编辑病例 ${caseId} 的自定义标签：`, oldLabel);
  if (input === null) return;
  const label = input.trim();
  if (!label) { alert('标签不能为空。'); return; }
  try {
    const res = await fetch(`/api/case/${encodeURIComponent(caseId)}/label`, { method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ label }) });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || '标签保存失败');
    await loadGroups();
    await loadCases();
  } catch (err) {
    alert(`标签保存失败：${err.message}`);
  }
}

async function deleteCase(event) {
  event.preventDefault(); event.stopPropagation();
  const caseId = event.currentTarget.dataset.caseId;
  if (!caseId) return;
  if (!confirm(`删除病例 ${caseId}？\n删除后将从当前知识库检索结果中移除。`)) return;
  const res = await fetch(`/api/case/${encodeURIComponent(caseId)}`, { method:'DELETE' });
  const data = await res.json();
  if (!res.ok || !data.ok) { alert(data.error || '删除失败'); return; }
  await loadGroups();
  await loadCases();
}


async function bulkDeleteCurrentCases() {
  const ids = (currentCases || []).map(c => c.case_id).filter(Boolean);
  if (!ids.length) { alert('当前没有可删除的病例结果。'); return; }
  const q = caseSearch.value.trim();
  const scopeText = q ? `当前查询结果中的 ${ids.length} 个病例` : `当前列表中的 ${ids.length} 个病例`;
  if (!confirm(`准备删除${scopeText}。\n删除后这些病例不会再参与知识库检索。是否继续？`)) return;
  const typed = prompt('为避免误删，请输入 DELETE 确认删除：');
  if (typed !== 'DELETE') { alert('已取消删除。'); return; }
  try {
    const res = await fetch('/api/cases/bulk', { method:'DELETE', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ case_ids: ids, confirm: 'DELETE' }) });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || '删除失败');
    alert(data.message || `已删除 ${ids.length} 个病例。`);
    await loadGroups();
    await loadCases();
  } catch (err) {
    alert(`删除失败：${err.message}`);
  }
}

function debounceLoadCases() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadCases, 250);
}

document.getElementById('reloadCases').onclick = loadCases;
document.getElementById('bulkDeleteCases').onclick = bulkDeleteCurrentCases;
caseSearch.addEventListener('input', debounceLoadCases);
caseSearch.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); loadCases(); }});
sheetFilter.addEventListener('change', loadCases);
(async function init(){ await loadGroups(); await loadCases(); })();


async function loadMascot() {
  try {
    const res = await fetch('/api/settings/mascot', {cache:'no-store'});
    const data = await res.json();
    if (data.ok && data.url) document.querySelectorAll('.mascot-img').forEach(img => { img.src = data.url; });
  } catch (_) {}
}
loadMascot();
