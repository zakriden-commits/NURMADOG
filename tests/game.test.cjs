const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');
const {createMatch,vote} = require('../rules.cjs');
test('starts at zero; invalid fighter ignored',()=> { const s=createMatch(); assert.deepEqual(s,{benoit:0,khabib:0,winner:null});assert.equal(vote(s,'bad'),s); });
for(const id of ['benoit','khabib']) test(id+' wins exactly at 100; match then locked',()=> {
 let s=createMatch(); for(let i=0;i<99;i++) s=vote(s,id); assert.equal(s.winner,null);
 s=vote(s,id); assert.equal(s.winner,id);assert.equal(s[id],100);assert.equal(vote(s,id),s);assert.equal(vote(s,id==='benoit'?'khabib':'benoit'),s);
});
function setup() {
 const dom=new JSDOM(fs.readFileSync('index.html','utf8'),{runScripts:'outside-only',url:'http://localhost/'}); const w=dom.window;
 w.matchMedia=()=>({matches:true});w.confirm=()=>true;w.requestAnimationFrame=()=>0;w.cancelAnimationFrame=()=>{};
 w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};
 w.eval(fs.readFileSync('rules.cjs','utf8'));w.eval(fs.readFileSync('game.js','utf8'));return dom;
}
for(const [id,loser] of [['benoit','khabib'],['khabib','benoit']]) test('UI: '+id+' wins, correct loser photo, rematch resets',async()=>{
 const dom=setup(),w=dom.window,d=w.document;
 try {
 for(let i=0;i<100;i++)d.getElementById(id).click();
 await new Promise(resolve=>setTimeout(resolve,20));
 assert.equal(d.getElementById(id+'-score').textContent,'100');assert.equal(d.getElementById('result').open,true);
 assert.ok(d.getElementById('loser-image').src.endsWith('/assets/'+loser+'-lost.jpg'));
 assert.ok(d.getElementById('winner-image').src.endsWith('/assets/'+id+(id==='khabib'?'.jpeg':'.jpg')));
 assert.equal(d.getElementById(id).disabled,true);
 d.getElementById('rematch').click();assert.equal(d.getElementById('result').open,false);
 assert.equal(d.getElementById(id+'-score').textContent,'0');assert.equal(d.getElementById(loser+'-score').textContent,'0');assert.equal(d.getElementById(id).disabled,false);
 d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowLeft'}));assert.equal(d.getElementById('benoit-score').textContent,'1');
 d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowRight',repeat:true}));assert.equal(d.getElementById('khabib-score').textContent,'0');
 }finally{w.close();}
});
