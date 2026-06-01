const articleList = document.getElementById('articleList');
const articleStatus = document.getElementById('articleStatus');
const articleUploadStatus = document.getElementById('articleUploadStatus');
const articleBatchStatus = document.getElementById('articleBatchStatus');
const articleStorageStatus = document.getElementById('articleStorageStatus');
const escapeHtml = (text) => String(text ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
let articleTimer = null;
let lastParsedArticleFile = null;
let currentArticleRows = [];
let autosaveTimer = null;
let autosavedArticleId = null;

const CHUNK_SIZE = 20;

const API_KEY_STORAGE = 'uscc_openai_api_key';
const API_MODEL_STORAGE = 'uscc_openai_model';
const API_PROVIDER_STORAGE = 'uscc_api_provider';
const API_BASE_URL_STORAGE = 'uscc_api_base_url';
const API_CUSTOM_MODEL_STORAGE = 'uscc_api_custom_model';
function appendApiConfigToFormData(fd) {
  const provider = localStorage.getItem(API_PROVIDER_STORAGE) || 'openai';
  const storedModel = localStorage.getItem(API_MODEL_STORAGE) || '';
  const customModel = localStorage.getItem(API_CUSTOM_MODEL_STORAGE) || '';
  fd.append('api_key', localStorage.getItem(API_KEY_STORAGE) || '');
  fd.append('provider', provider);
  fd.append('base_url', localStorage.getItem(API_BASE_URL_STORAGE) || '');
  fd.append('model', storedModel === '__custom__' ? customModel : storedModel);
}

function renderArticles(rows) {
  currentArticleRows = rows || [];
  if (!rows.length) {
    articleList.innerHTML = '<div class="empty-card">暂无匹配文章。可以先在上方投喂文章或批量导入文件夹。</div>';
    return;
  }
  articleList.innerHTML = rows.map(a => {
    const meta = [a.authors, a.journal, a.year].filter(Boolean).join('｜');
    const preview = a.abstract || a.content_preview || '';
    const href = `/article/${encodeURIComponent(a.article_id)}`;
    const fileLink = a.source_url ? `<a class="case-open-btn" href="${escapeHtml(a.source_url)}" target="_blank" onclick="event.stopPropagation()">原文件</a>` : '';
    return `<article class="article-card">
      <a class="article-card-main" href="${href}" target="_blank">
        <b>${escapeHtml(a.article_id)}｜${escapeHtml(a.title || '未命名文献')}</b>
        ${meta ? `<small>${escapeHtml(meta)}</small>` : ''}
        ${a.keywords ? `<small>关键词：${escapeHtml(a.keywords)}</small>` : ''}
        <p>${escapeHtml(preview || '暂无摘要。')}</p>
      </a>
      <div class="case-card-actions"><a class="case-open-btn" href="${href}" target="_blank">查看详情</a>${fileLink}<button class="article-delete-mini" data-article-id="${escapeHtml(a.article_id)}">删除</button></div>
    </article>`;
  }).join('');
  document.querySelectorAll('.article-delete-mini').forEach(btn => btn.addEventListener('click', deleteOneArticle));
}

async function loadStorageStatus() {
  if (!articleStorageStatus) return;
  try {
    const res = await fetch('/api/storage/status', { cache: 'no-store' });
    const data = await res.json();
    if (data.ok) {
      articleStorageStatus.textContent = `文献库：${data.articles} 篇文章，新增病例：${data.user_cases} 个。单次上传上限 ${data.max_upload_mb}MB；批量最多 ${data.max_batch_files} 个文件。`;
    }
  } catch (_) {}
}

async function loadArticles() {
  const q = document.getElementById('articleSearch').value.trim();
  articleList.innerHTML = '<div class="empty-card">正在读取文章...</div>';
  try {
    const res = await fetch(`/api/articles?q=${encodeURIComponent(q)}&limit=500`, { cache: 'no-store' });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || '读取失败');
    renderArticles(data.articles || []);
    await loadStorageStatus();
  } catch (err) {
    articleList.innerHTML = `<div class="empty-card">文章读取失败：${escapeHtml(err.message)}</div>`;
  }
}

async function parseArticleFile() {
  const files = Array.from(document.getElementById('articleFile').files || []);
  if (!files.length) { articleUploadStatus.textContent = '请选择文件。'; return; }
  try {
    if (files.length > 1) {
      articleUploadStatus.textContent = `正在批量解析文本与图片并保存 ${files.length} 个文章文件...`;
      let totalAdded = 0, totalFailed = 0, duplicateNotes = 0;
      for (let i = 0; i < files.length; i += CHUNK_SIZE) {
        const chunk = files.slice(i, i + CHUNK_SIZE);
        articleUploadStatus.textContent = `正在解析 ${i + 1}-${Math.min(i + CHUNK_SIZE, files.length)} / ${files.length}...`;
        const data = await postArticleFiles(chunk);
        totalAdded += (data.added || []).length;
        totalFailed += (data.failed || []).length;
        duplicateNotes += (data.failed || []).filter(x => String(x.error || '').includes('重复')).length;
      }
      articleUploadStatus.textContent = `批量处理完成：已加入 ${totalAdded} 篇，跳过重复 ${duplicateNotes} 篇，失败 ${Math.max(0,totalFailed-duplicateNotes)} 个。`;
      if (duplicateNotes) alert(`检测到 ${duplicateNotes} 篇重复文章，已跳过重复收录。`);
      await loadArticles();
      document.getElementById('articleFile').value = '';
      return;
    }
    const file = files[0];
    const fd = new FormData(); fd.append('file', file); appendApiConfigToFormData(fd);
    articleUploadStatus.textContent = '正在解析文本与图片...';
    const res = await fetch('/api/upload_article', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || '解析失败');
    lastParsedArticleFile = { source_file: data.filename, source_url: data.url, stored_as: data.stored_as };
    if (!document.getElementById('articleTitle').value.trim()) document.getElementById('articleTitle').value = data.filename.replace(/\.[^.]+$/, '');
    document.getElementById('articleContent').value = data.text || '';
    articleUploadStatus.textContent = data.note || '解析完成，正在保存...';
    await autoSaveArticleNow(false);
    document.getElementById('articleFile').value = '';
  } catch (err) {
    articleUploadStatus.textContent = `解析失败：${err.message}`;
  }
}

async function postArticleFiles(filesChunk) {
  const fd = new FormData();
  filesChunk.forEach(f => fd.append('files', f, f.webkitRelativePath || f.name));
  appendApiConfigToFormData(fd);
  const res = await fetch('/api/upload_articles_batch', { method: 'POST', body: fd });
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || '批量导入失败');
  return data;
}

async function batchImportArticles() {
  const files = Array.from(document.getElementById('articleFolder').files || []);
  if (!files.length) { articleBatchStatus.textContent = '请选择包含文章的文件夹。'; return; }
  // v13: 批量导入不再弹出二次询问，选择文件夹并点击后直接处理。
  let totalAdded = 0;
  let totalFailed = 0;
  let duplicateNotes = 0;
  articleBatchStatus.textContent = `准备分批解析 ${files.length} 个文件...`;
  try {
    for (let i = 0; i < files.length; i += CHUNK_SIZE) {
      const chunk = files.slice(i, i + CHUNK_SIZE);
      articleBatchStatus.textContent = `正在解析 ${i + 1}-${Math.min(i + CHUNK_SIZE, files.length)} / ${files.length}...`;
      const data = await postArticleFiles(chunk);
      totalAdded += (data.added || []).length;
      totalFailed += (data.failed || []).length;
      duplicateNotes += (data.failed || []).filter(x => String(x.error || '').includes('重复')).length;
    }
    articleBatchStatus.textContent = `批量导入完成：已加入 ${totalAdded} 篇文章，跳过重复 ${duplicateNotes} 篇，失败 ${Math.max(0,totalFailed-duplicateNotes)} 个文件。`; if (duplicateNotes) alert(`检测到 ${duplicateNotes} 篇重复文章，已跳过重复收录。`);
    await loadArticles();
  } catch (err) {
    articleBatchStatus.textContent = `批量导入中断：${err.message}。可减少单批文件或检查文件格式。`;
  } finally {
    document.getElementById('articleFolder').value = '';
  }
}

async function submitArticle() {
  await autoSaveArticleNow(true);
}

function collectArticleFields() {
  return {
    title: document.getElementById('articleTitle').value,
    authors: document.getElementById('articleAuthors').value,
    journal: document.getElementById('articleJournal').value,
    year: document.getElementById('articleYear').value,
    keywords: document.getElementById('articleKeywords').value,
    abstract: document.getElementById('articleAbstract').value,
    content: document.getElementById('articleContent').value,
    source_file: lastParsedArticleFile?.source_file || '',
    source_url: lastParsedArticleFile?.source_url || '',
    stored_as: lastParsedArticleFile?.stored_as || '',
    created_at: new Date().toISOString(),
  };
}

function hasArticleContent(fields) {
  return Boolean((fields.title || fields.abstract || fields.content || fields.keywords || '').trim());
}

async function autoSaveArticleNow(force = false) {
  const fields = collectArticleFields();
  if (!hasArticleContent(fields)) {
    if (force) articleStatus.textContent = '请先输入标题、摘要或正文。';
    return;
  }
  articleStatus.textContent = autosavedArticleId ? '正在更新文章...' : '正在保存到文献库...';
  try {
    const res = await fetch('/api/articles/autosave', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ article_id: autosavedArticleId, fields }) });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || '保存失败');
    if (data.duplicate) {
      const msg = data.message || '检测到相同文章，已跳过重复收录。';
      articleStatus.textContent = msg;
      alert(msg);
      return;
    }
    autosavedArticleId = data.article?.article_id || autosavedArticleId;
    articleStatus.textContent = autosavedArticleId ? `已保存：${autosavedArticleId}。` : '已保存。';
    if (force) {
      ['articleTitle','articleAuthors','articleJournal','articleYear','articleKeywords','articleAbstract','articleContent'].forEach(id => document.getElementById(id).value = '');
      document.getElementById('articleFile').value = '';
      lastParsedArticleFile = null;
      autosavedArticleId = null;
    }
    await loadArticles();
  } catch (err) {
    articleStatus.textContent = `自动保存失败：${err.message}`;
  }
}

function scheduleArticleAutosave() {
  clearTimeout(autosaveTimer);
  autosaveTimer = setTimeout(() => autoSaveArticleNow(false), 1200);
}

async function deleteOneArticle(event) {
  event.preventDefault();
  event.stopPropagation();
  const articleId = event.currentTarget.dataset.articleId;
  if (!articleId) return;
  if (!confirm(`确认删除文章 ${articleId}？删除后会从文献库 JSON 中移除。`)) return;
  try {
    const res = await fetch(`/api/article/${encodeURIComponent(articleId)}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || '删除失败');
    await loadArticles();
  } catch (err) { alert(`删除失败：${err.message}`); }
}

async function bulkDeleteArticles() {
  const ids = currentArticleRows.map(a => a.article_id).filter(Boolean);
  if (!ids.length) { alert('当前没有可删除的文章结果。'); return; }
  const tip = `将一键删除当前查询结果中的 ${ids.length} 篇文章。该操作会修改 data/articles.json。\n如确认删除，请在下一步输入 DELETE。`;
  if (!confirm(tip)) return;
  const confirmText = prompt('请输入 DELETE 确认一键删除中的文章：');
  if (confirmText !== 'DELETE') return;
  try {
    const res = await fetch('/api/articles/bulk', { method:'DELETE', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ article_ids: ids, confirm: 'DELETE' }) });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || '删除失败');
    articleBatchStatus.textContent = data.message || '删除完成。';
    await loadArticles();
  } catch (err) { alert(`删除失败：${err.message}`); }
}

function debounceLoadArticles() {
  clearTimeout(articleTimer);
  articleTimer = setTimeout(loadArticles, 250);
}

document.getElementById('parseArticleFile').addEventListener('click', parseArticleFile);
const parseFolderBtn = document.getElementById('parseArticleFolder');
if (parseFolderBtn) parseFolderBtn.addEventListener('click', batchImportArticles);
document.getElementById('submitArticle')?.addEventListener('click', submitArticle);
document.getElementById('queryArticles').addEventListener('click', loadArticles);
document.getElementById('articleSearch').addEventListener('input', debounceLoadArticles);
document.getElementById('articleSearch').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); loadArticles(); }});
document.getElementById('bulkDeleteArticles')?.addEventListener('click', bulkDeleteArticles);

['articleTitle','articleAuthors','articleJournal','articleYear','articleKeywords','articleAbstract','articleContent'].forEach(id => {
  const el = document.getElementById(id);
  if (el) el.addEventListener('input', scheduleArticleAutosave);
});
loadArticles();


async function loadMascot() {
  try {
    const res = await fetch('/api/settings/mascot', {cache:'no-store'});
    const data = await res.json();
    if (data.ok && data.url) document.querySelectorAll('.mascot-img').forEach(img => { img.src = data.url; });
  } catch (_) {}
}
loadMascot();
