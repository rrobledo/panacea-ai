const els={}; const mk=id=>({id,innerHTML:'',textContent:'',hidden:false,_l:{},addEventListener(t,f){this._l[t]=f},querySelectorAll(){return[]},setAttribute(){},dataset:{}});
global.document={getElementById:id=>els[id]||(els[id]=mk(id)),documentElement:{}};
global.getComputedStyle=()=>({getPropertyValue:()=>'#000'}); global.matchMedia=()=>({addEventListener(){}}); global.MutationObserver=class{observe(){}};
global.window={Chart:1}; global.Chart=class{destroy(){}}; Chart.defaults={font:{}}; global.navigator={};
require(process.argv[2]);
for (const z of [0,0.3,0.5,0.8,1]) { els.z._l.input({target:{value:z}}); console.log(z, els.kpis.innerHTML.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ')); }
