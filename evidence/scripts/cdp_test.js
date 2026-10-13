const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => {
  const SP = process.env.SP;
  const browser = await chromium.launch({
    headless: true,
    args: ['--remote-debugging-port=9222', '--password-store=basic', '--no-sandbox', '--disable-dev-shm-usage'],
  });
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36' });
  const page = await ctx.newPage();
  const reqs = [];
  page.on('request', r => reqs.push(r.method() + ' ' + r.url()));
  await page.goto('https://georgefi.trade/', { waitUntil: 'networkidle', timeout: 60000 });
  await page.screenshot({ path: SP + '/evidence/screenshots/home_public.png', fullPage: false });
  console.log('title:', await page.title());
  const ver = await fetch('http://127.0.0.1:9222/json/version').then(r => r.json()).catch(e => ({ err: String(e) }));
  console.log('cdp version:', JSON.stringify(ver).slice(0, 300));
  const targets = await fetch('http://127.0.0.1:9222/json').then(r => r.json()).catch(e => ({ err: String(e) }));
  console.log('cdp targets:', JSON.stringify(targets).slice(0, 500));
  console.log('requests:', reqs.length);
  console.log(reqs.filter(u => !u.includes('/_nuxt/') && !u.includes('fonts.g')).slice(0, 60).join('\n'));
  await browser.close();
})().catch(e => { console.error('ERR', e); process.exit(1); });
