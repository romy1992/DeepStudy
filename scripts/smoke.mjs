import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createInterface } from 'node:readline';
import { once } from 'node:events';
const dir = await mkdtemp(join(tmpdir(),'deepstudy-'));
const browser = await chromium.launch({channel:'msedge',headless:true});
async function run(profile, visit) {
 const p=spawn('.venv/Scripts/python.exe',['-m','deepstudy.server','--desktop','--data-root',dir,'--profile',profile],{env:{...process.env,PYTHONPATH:'backend'}});
 const done=once(p,'exit');
 try {
  const [line]=await once(createInterface({input:p.stdout}),'line');
  const page=await browser.newPage({viewport:{width:375,height:780}});
  try { await page.goto(JSON.parse(line).url); await page.getByRole('heading',{name:/Pronto a costruire/}).waitFor(); await visit(page); }
  finally { await page.close(); }
 } finally {p.stdin.end(); await done;}
}
try {
 const path=join(dir,'backup.zip');
 await run('source',async page=>{
  await page.getByRole('button',{name:'Impostazioni',exact:true}).click();
  await page.getByLabel('Come vuoi essere chiamato?').fill('Ada');
  await page.getByRole('button',{name:'Salva preferenze'}).click();
  await page.getByRole('status').waitFor();
  await page.getByRole('button',{name:'Backup e ripristino',exact:true}).click();
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'Scarica backup'}).click();
  await (await download).saveAs(path);
 });
 await run('restored',async page=>{
  await page.getByRole('button',{name:'Backup e ripristino',exact:true}).click();
  await page.getByLabel('Archivio DeepStudy').setInputFiles(path);
  await page.getByRole('checkbox').check();
  await page.getByRole('button',{name:'Verifica e ripristina'}).click();
  await page.getByRole('status').filter({hasText:'Ripristino completato'}).waitFor();
  await page.getByRole('button',{name:'Panoramica',exact:true}).click();
  await page.getByRole('heading',{name:'Pronto a costruire, Ada.'}).waitFor();
 });
 console.log('Edge: login, viewport mobile, preferenze, download e restore verificati');
} finally { await browser.close(); await rm(dir,{recursive:true}); }
