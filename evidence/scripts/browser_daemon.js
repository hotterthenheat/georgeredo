// Persistent research browser: Playwright Chromium with CDP on 127.0.0.1:9222 (for REA attach)
// and a tiny local control API on 127.0.0.1:9333. Read-only observation; no secrets logged.
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const http = require('http'); const fs = require('fs'); const url = require('url');
const SP = process.env.SP; const PROFILE = SP + '/browser/profile';
(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    headless: true, viewport: { width: 1440, height: 900 },
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
    args: ['--remote-debugging-port=9222', '--password-store=basic', '--no-sandbox', '--disable-dev-shm-usage'],
  });
  let page = ctx.pages()[0] || await ctx.newPage();
  const net = []; const ws = []; const consoleLog = [];
  const attach = (p) => {
    p.on('request', r => net.push({ t: Date.now(), ev: 'req', m: r.method(), u: r.url(), type: r.resourceType() }));
    p.on('response', async r => { let ct = ''; try { ct = r.headers()['content-type'] || ''; } catch {} net.push({ t: Date.now(), ev: 'res', s: r.status(), u: r.url(), ct }); });
    p.on('websocket', w => { ws.push({ t: Date.now(), ev: 'open', u: w.url() });
      w.on('framereceived', f => ws.push({ t: Date.now(), ev: 'in', u: w.url(), n: (f.payload || '').length, head: String(f.payload || '').slice(0, 200) }));
      w.on('framesent', f => ws.push({ t: Date.now(), ev: 'out', u: w.url(), n: (f.payload || '').length, head: String(f.payload || '').slice(0, 200) }));
      w.on('close', () => ws.push({ t: Date.now(), ev: 'close', u: w.url() })); });
    p.on('console', m => consoleLog.push({ t: Date.now(), type: m.type(), text: m.text().slice(0, 300) }));
  };
  attach(page);
  const send = (res, code, obj) => { res.writeHead(code, { 'content-type': 'application/json' }); res.end(JSON.stringify(obj)); };
  http.createServer(async (req, res) => {
    const q = url.parse(req.url, true); const a = q.query; const path = q.pathname;
    try {
      if (path === '/goto') { await page.goto(a.url, { waitUntil: a.wait || 'load', timeout: 60000 }); await page.waitForTimeout(Number(a.settle || 3000)); return send(res, 200, { url: page.url(), title: await page.title() }); }
      if (path === '/wait') { await page.waitForTimeout(Number(a.ms || 2000)); return send(res, 200, { ok: true, url: page.url() }); }
      if (path === '/text') { const t = await page.evaluate(() => document.body.innerText); return send(res, 200, { url: page.url(), title: await page.title(), text: t }); }
      if (path === '/html') { return send(res, 200, { url: page.url(), html: await page.content() }); }
      if (path === '/screenshot') { const f = SP + '/evidence/screenshots/' + (a.name || 'shot') + '.png'; await page.screenshot({ path: f, fullPage: a.full === '1' }); return send(res, 200, { file: f }); }
      if (path === '/click') { await page.click(a.sel, { timeout: 10000 }); await page.waitForTimeout(Number(a.settle || 1500)); return send(res, 200, { ok: true, url: page.url() }); }
      if (path === '/clicktext') { await page.getByText(a.text, { exact: a.exact === '1' }).first().click({ timeout: 10000 }); await page.waitForTimeout(Number(a.settle || 1500)); return send(res, 200, { ok: true, url: page.url() }); }
      if (path === '/fill') { await page.fill(a.sel, a.value, { timeout: 10000 }); return send(res, 200, { ok: true }); }
      if (path === '/login') { // reads creds from env only; never logs them
        const e = process.env.GEORGEFI_EMAIL, pw = process.env.GEORGEFI_PASSWORD; if (!e || !pw) return send(res, 400, { error: 'no credentials in env' });
        await page.goto('https://georgefi.trade/login', { waitUntil: 'load' }); await page.waitForTimeout(2000);
        await page.fill('input[type=email]', e); await page.fill('input[type=password]', pw); await page.click('button[type=submit]'); await page.waitForTimeout(5000);
        return send(res, 200, { url: page.url(), title: await page.title() }); }
      if (path === '/net') { const out = net.slice(Number(a.from || 0)); return send(res, 200, { n: net.length, items: a.filter ? out.filter(x => x.u.includes(a.filter)) : out }); }
      if (path === '/ws') { return send(res, 200, { n: ws.length, items: ws.slice(Number(a.from || 0)) }); }
      if (path === '/console') { return send(res, 200, { items: consoleLog.slice(Number(a.from || 0)) }); }
      if (path === '/clear') { net.length = 0; ws.length = 0; consoleLog.length = 0; return send(res, 200, { ok: true }); }
      if (path === '/eval') { const v = await page.evaluate(a.js); return send(res, 200, { value: v }); }
      if (path === '/state') { const st = await page.evaluate(() => { try { const n = window.__NUXT__ || window.useNuxtApp?.().payload; return n ? JSON.stringify(n.state || n.data || {}).slice(0, 200000) : null; } catch (e) { return 'ERR ' + e; } }); return send(res, 200, { state: st }); }
      if (path === '/targets') { const t = await fetch('http://127.0.0.1:9222/json').then(r => r.json()); return send(res, 200, t); }
      if (path === '/newpage') { page = await ctx.newPage(); attach(page); return send(res, 200, { ok: true }); }
      if (path === '/quit') { send(res, 200, { bye: true }); await ctx.close(); process.exit(0); }
      return send(res, 404, { error: 'unknown ' + path });
    } catch (e) { return send(res, 500, { error: String(e).slice(0, 500) }); }
  }).listen(9333, '127.0.0.1', () => console.log('control on 127.0.0.1:9333; cdp on 9222'));
})().catch(e => { console.error('FATAL', e); process.exit(1); });
