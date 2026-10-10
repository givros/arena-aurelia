import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
const execute=promisify(execFile);
export async function observeHost(browser,phase){
 const result={phase,timestamp:new Date().toISOString(),scope:'Read-only GPU engine sample outside timed intervals. Other applications are neither controlled nor closed.',testProcessIds:[],engines:[]};
 try{const session=await browser.newBrowserCDPSession();const info=await session.send('SystemInfo.getProcessInfo');result.testProcessIds=info.processInfo.map(p=>Number(p.id));await session.detach();}catch(error){result.processInventoryError=error.message;}
 try{const script="$items=@(Get-Counter '\\GPU Engine(*)\\Utilization Percentage' -ErrorAction Stop | ForEach-Object {$_.CounterSamples} | Where-Object {$_.CookedValue -gt 0.1} | ForEach-Object {[pscustomobject]@{instance=$_.InstanceName;utilizationPercent=$_.CookedValue}});ConvertTo-Json -InputObject $items -Compress";const {stdout}=await execute('powershell.exe',['-NoProfile','-Command',script],{timeout:20000,windowsHide:true});result.engines=JSON.parse(stdout).map(e=>{const pid=Number(e.instance.match(/^pid_(\d+)_/)?.[1]);return {...e,pid,ownedByTest:result.testProcessIds.includes(pid)};});}catch(error){result.counterError=error.message;}
 result.background3dEngines=result.engines.filter(e=>!e.ownedByTest&&e.instance.endsWith('engtype_3d'));
 return result;
}
