import {mkdir,rename} from 'node:fs/promises';
import {resolve,join} from 'node:path';
const {chromium}=await import(process.env.FLIGHTS_PLAYWRIGHT_MODULE||'playwright');
const output=resolve(process.argv[2]||'/tmp/flights-motion');await mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1250},recordVideo:{dir:output,size:{width:1440,height:1250}}});
const page=await context.newPage();
try{
 await page.goto('http://127.0.0.1:8805');const ui=page.frameLocator('#av-body iframe');
 await ui.locator('.flight').first().waitFor();await page.waitForTimeout(1100);
 await ui.locator('.flight').nth(1).click();await page.waitForTimeout(1000);
 await ui.locator('.bar-row').nth(2).click();await page.waitForTimeout(1000);
 await ui.locator('.bar-row').first().click();await page.waitForTimeout(1000);
 await ui.locator('#check-dates').click();await ui.locator('.day').first().waitFor();
 await ui.locator('#nearby').scrollIntoViewIfNeeded();await page.waitForTimeout(1000);
 await ui.locator('.day').first().click();await page.waitForTimeout(1300);
 await ui.locator('#route-name').scrollIntoViewIfNeeded();await page.waitForTimeout(1100);
}finally{const video=page.video();await context.close();await rename(await video.path(),join(output,'flights-motion.webm'));await browser.close()}
console.log(join(output,'flights-motion.webm'));
