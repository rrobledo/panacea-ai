const els={}; const mk=id=>({id,innerHTML:'',textContent:'',hidden:false,addEventListener(){},querySelectorAll(){return[]},setAttribute(){},dataset:{}});
global.document={getElementById:id=>els[id]||(els[id]=mk(id)),documentElement:{}};
global.getComputedStyle=()=>({getPropertyValue:()=>'#000'}); global.matchMedia=()=>({addEventListener(){}}); global.MutationObserver=class{observe(){}};
global.window={Chart:1}; global.Chart=class{destroy(){}}; Chart.defaults={font:{}}; global.navigator={};
require(process.argv[2]);
const strip=h=>h.replace(/<\/t[dh]>/g,' | ').replace(/<\/tr>/g,'\n').replace(/<[^>]+>/g,'').replace(/[ \t]+/g,' ');
console.log(strip(els.kpis.innerHTML)); console.log(strip(els.tSem.innerHTML).split('\n').slice(0,40).join('\n')); console.log("VGB\n"+strip(els.tVgb.innerHTML));
