import {chromium} from 'playwright';
import fs from 'node:fs';
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-webgpu','--ignore-gpu-blocklist']});
const page=await browser.newPage({viewport:{width:1440,height:1080},deviceScaleFactor:1});
await page.goto('http://127.0.0.1:4178/?debug=1');
await page.waitForFunction(()=>window.__arena||window.__arenaFailure,null,{timeout:180000});
const error=await page.evaluate(()=>window.__arenaFailure);if(error)throw new Error(error);
const views=[
 {id:'northeast',position:[240,165,-150],target:[25,10,5],fov:38},
 {id:'north',position:[130,150,-245],target:[25,10,0],fov:38},
 {id:'northwest',position:[-170,155,-230],target:[-15,10,0],fov:38}
];
for(const v of views){await page.evaluate(v=>{const w=window.__arena;w.environment.manifest.cameras[v.id]=v;w.view(v.id);},v);await page.waitForTimeout(700);await page.screenshot({path:`../renders/runtime_feedback_${v.id}.png`});}
fs.writeFileSync('feedback_views.json',JSON.stringify(views,null,2));await browser.close();
