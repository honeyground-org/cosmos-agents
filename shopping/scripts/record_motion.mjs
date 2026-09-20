// Actual UI recording against the isolated fixture server; no external actions.
import {mkdir,rename} from 'node:fs/promises';
import {resolve,join} from 'node:path';
const {chromium}=await import(process.env.SHOPPING_PLAYWRIGHT_MODULE||'playwright');
const output=resolve(process.argv[2]||'/tmp/shopping-motion');await mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1100},recordVideo:{dir:output,size:{width:1440,height:1100}}});
const page=await context.newPage();
try{
 await page.goto('http://127.0.0.1:8804');const ui=page.frameLocator('#av-body iframe');
 await ui.locator('.candidate').first().waitFor();await page.waitForTimeout(900);
 await ui.locator('#query').fill('출퇴근용 헤드폰 — 화면 예시');await ui.locator('button[type=submit]').click();
 await page.waitForTimeout(850);await ui.locator('.candidate').nth(1).click();await page.waitForTimeout(950);
 await ui.locator('#hero-image').hover();await page.waitForTimeout(800);
 await ui.locator('#price-chart .bar-row').nth(2).click();await page.waitForTimeout(950);
 await ui.locator('.candidate').first().click();await page.waitForTimeout(900);
}finally{
 const video=page.video();await context.close();await rename(await video.path(),join(output,'shopping-motion.webm'));await browser.close();
}
console.log(join(output,'shopping-motion.webm'));
