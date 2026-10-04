/* Checks the actual rendered site in Chromium/Edge using Playwright. */
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const state = JSON.parse(fs.readFileSync(path.join(root,'.cache','preview.json'),'utf8').replace(/^\uFEFF/,''));
const output = path.join(root,'.cache','browser-check');
fs.mkdirSync(output,{recursive:true});
const edge = path.join(process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)','Microsoft','Edge','Application','msedge.exe');
const checks = [];

(async () => {
  const browser = await chromium.launch({headless:true, ...(fs.existsSync(edge)?{executablePath:edge}:{})});
  try {
    const context = await browser.newContext({viewport:{width:1440,height:1000}});
    const page = await context.newPage();
    const errors=[];
    page.on('pageerror',err=>errors.push(err.message));
    for (const pageName of ['index.html','leaderboard.html']) {
      await page.goto(state.url+'/'+pageName,{waitUntil:'networkidle'});
      await page.waitForSelector('.tabulator-row');
      assert.equal(await page.locator('html').getAttribute('lang'),'en');
      assert.equal(await page.locator('.tabulator-row').count(),6);
      assert.ok((await page.locator('.tabulator-row').first().innerText()).includes('Kimi-K3'));
      const body=await page.locator('body').innerText();
      assert.ok(!/[\u4e00-\u9fff]/.test(body),'English UI has Chinese text');
      assert.ok(!/Equal contribution|TODO|PLACEHOLDER|lorem ipsum/i.test(body));
      for (const identity of ['Jiulin Li','Ping Huang','lijiulin@18trees.com','Beijing Liuyi Guanhua Technology Co., Ltd.','State Key Laboratory of General Artificial Intelligence','BIGAI']) {
        assert.ok(!body.includes(identity),'Author information is displayed: '+identity);
      }
      assert.equal(await page.locator('a[href^="mailto:"]').count(),0);
      assert.equal(await page.locator('a[href="#BibTeX"]').count(),0);
      const payload=await page.locator('#leaderboard-data').evaluate(el=>JSON.parse(el.textContent));
      assert.deepEqual(payload.rows.map(r=>r.n),Array(6).fill(2492));
      const sort=page.locator('.tabulator-col[tabulator-field="overall_acc"] .tabulator-col-title');
      await sort.click();
      await page.waitForFunction(()=>document.querySelector('.tabulator-row').innerText.includes('MiniMax-M3'));
      await sort.click();
      await page.waitForFunction(()=>document.querySelector('.tabulator-row').innerText.includes('Kimi-K3'));
      await page.getByRole('searchbox',{name:'Filter models'}).fill('deepseek');
      await page.waitForFunction(()=>document.querySelectorAll('.tabulator-row').length===2);
      await page.getByRole('searchbox',{name:'Filter models'}).fill('no-model-matches');
      await page.waitForFunction(()=>document.querySelectorAll('.tabulator-row').length===0);
      await page.getByRole('searchbox',{name:'Filter models'}).fill('');
      await page.waitForFunction(()=>document.querySelectorAll('.tabulator-row').length===6);
      const headerFilter=page.locator('.tabulator-col[tabulator-field="model"] .tabulator-header-filter input');
      await headerFilter.pressSequentially('Kimi');
      await page.waitForFunction(()=>document.querySelectorAll('.tabulator-row').length===1);
      await headerFilter.press('ControlOrMeta+A');
      await headerFilter.press('Backspace');
      await page.waitForFunction(()=>document.querySelectorAll('.tabulator-row').length===6);
      const links=await page.evaluate(()=>Array.from(document.querySelectorAll('a[href],img[src],script[src],link[href]')).map(el=>el.getAttribute('href')||el.getAttribute('src')).filter(s=>s&&!s.startsWith('#')&&!/^(https?:|mailto:)/.test(s)));
      for(const href of new Set(links)){
        const response=await context.request.get(new URL(href,page.url()).href);
        assert.equal(response.status(),200,'Missing asset: '+href);
      }
      for(const href of ['https://nerfies.github.io/','https://github.com/eliahuhorwitz/Academic-project-page-template']){
        assert.equal(await page.locator(`.footer a[href="${href}"]`).count(),1);
      }
      if(pageName==='index.html'){
        const figures=page.locator('#Gallery img');
        assert.equal(await figures.count(),4);
        for(const img of await figures.all()){
          await img.scrollIntoViewIfNeeded();
          await page.waitForFunction(src=>Array.from(document.images).find(i=>i.getAttribute('src')===src)?.naturalWidth>0,await img.getAttribute('src'));
        }
        const wide=await page.locator('.figure-wide').boundingBox();
        const gallery=await page.locator('.gallery-grid').boundingBox();
        assert.ok(wide.width/gallery.width>.95,'Figure 4 must span the gallery');
        const opened=await context.request.get(state.url+'/figures/category-profile.svg');
        assert.ok((await opened.text()).includes('<svg'));
        await page.locator('.figure-wide').screenshot({path:path.join(output,'figure4-desktop.png')});
        await page.locator('#Leaderboard').screenshot({path:path.join(output,'leaderboard-desktop.png')});
      }
      await page.evaluate(()=>window.scrollTo(0,0));
      await page.screenshot({path:path.join(output,pageName.replace('.html','')+'-desktop.png'),fullPage:true});
      await page.setViewportSize({width:375,height:900});
      await page.waitForTimeout(150);
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'Page overflows at 375px: '+pageName);
      await page.locator('#Leaderboard').scrollIntoViewIfNeeded();
      const before=await page.locator('.tabulator-row').first().locator('[tabulator-field="model"]').boundingBox();
      await page.locator('.tabulator-tableholder').evaluate(el=>el.scrollLeft=200);
      const after=await page.locator('.tabulator-row').first().locator('[tabulator-field="model"]').boundingBox();
      assert.ok(Math.abs(before.x-after.x)<2,'Frozen model column moved');
      await page.locator('#Leaderboard').screenshot({path:path.join(output,pageName.replace('.html','')+'-table-mobile.png')});
      await page.evaluate(()=>window.scrollTo(0,0));
      await page.screenshot({path:path.join(output,pageName.replace('.html','')+'-mobile.png'),fullPage:true});
      await page.setViewportSize({width:1440,height:1000});
      checks.push(pageName+': English metadata, sorting, filtering, links, figures, frozen column, mobile layout');
    }
    const pdfResponse=await context.request.get(state.url+'/pdfs/paper.pdf');
    const pdf=await pdfResponse.body();
    assert.equal(pdf.subarray(0,5).toString(),'%PDF-');
    const sha=buf=>crypto.createHash('sha256').update(buf).digest('hex');
    assert.equal(sha(pdf),sha(fs.readFileSync(path.join(root,'docs','pdfs','paper.pdf'))));
    assert.deepEqual(errors,[],'Browser JavaScript errors');
    checks.push('PDF served successfully; SHA-256 matches the revised manuscript');
    fs.writeFileSync(path.join(output,'report.json'),JSON.stringify({url:state.url,checks,errors},null,2)+'\n');
    console.log(checks.join('\n'));
  } finally {await browser.close();}
})().catch(err=>{console.error(err);process.exitCode=1;});
