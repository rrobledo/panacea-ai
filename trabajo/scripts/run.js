// smoke test: stub DOM y Chart, ejecutar el script completo
const els={}; const el=()=>({innerHTML:'',hidden:false,appendChild(){},addEventListener(){},querySelectorAll(){return[]},setAttribute(){},dataset:{}});
global.document={getElementById:id=>els[id]||(els[id]=el()),createElement:()=>el(),documentElement:{}};
global.getComputedStyle=()=>({getPropertyValue:()=>'#000'});
global.matchMedia=()=>({addEventListener(){}}); global.MutationObserver=class{observe(){}};
let n=0; global.window={Chart:1}; global.Chart=class{constructor(){n++} destroy(){}}; Chart.defaults={font:{}};
require(process.argv[2]); console.log("charts",n); console.log(els.kpisMerma.innerHTML.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').slice(0,400)); console.log(els.tGranel.innerHTML.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').slice(0,500));
